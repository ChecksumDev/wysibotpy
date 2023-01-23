import asyncio
import contextlib
import json
import sys
from configparser import ConfigParser

from websockets.client import connect
from aiohttp.client import ClientSession
from loguru import logger
from tweepy.asynchronous import AsyncClient as TwitterClient
from tweepy.models import User
from twitchAPI import Twitch
from twitchAPI.chat import Chat, ChatEvent, EventData
from twitchAPI.helper import first
from twitchAPI.oauth import AuthScope

from modules.analytics import Analytics
from modules.discord import send_webhook
from utilities.tools import dysi, extract_socials, get_username


class Client:
    def __init__(self, config: ConfigParser):
        self.config = config
        self.scopes = list(AuthScope)

        self.analytics = Analytics()
        self.twitch: Twitch

    async def start(self):
        self.client = ClientSession()

        self.twitter = TwitterClient(
            bearer_token=self.config.get("twitter", "bearer_token"),
            consumer_key=self.config.get("twitter", "app_key"),
            consumer_secret=self.config.get("twitter", "app_secret"),
            access_token=self.config.get("twitter", "access_token"),
            access_token_secret=self.config.get("twitter", "access_secret"),
        )

        twitter_username = await self.twitter.get_me()
        logger.success(
            f"Successfully connected to Twitter as {twitter_username.data.username}")

        # Initialize the Twitch API and Chatbot
        self.twitch = await Twitch(
            self.config.get("twitch", "client_id"),
            self.config.get("twitch", "client_secret"),
        )

        await self.twitch.set_user_authentication(
            token="REFRESH_ME",
            refresh_token=self.config.get("twitch", "refresh_token"),
            validate=False,
            scope=self.scopes,
        )

        # create chat instance
        self.chat = await Chat(self.twitch)
        self.chat.register_event(ChatEvent.READY, self.on_ready)
        self.chat.start()

        current_ws = None
        async for websocket in connect("wss://api.beatleader.xyz/scores", compression=None):
            logger.success("Connected to the BeatLeader websocket!")

            try:
                current_ws = websocket

                while current_ws is not None:
                    message = await current_ws.recv()
                    await asyncio.ensure_future(self.on_score(message))

            except Exception as e:
                current_ws = None  # Close the websocket connection

                webhook = self.config.get("discord", "exception_webhook")
                async with ClientSession() as session:
                    async with session.post(webhook, json={"content": f"```{e}```"}) as resp:
                        pass

                logger.error(
                    "An exception occured on the websocket connection:")
                logger.error(e)

    async def on_ready(self, event: EventData):
        logger.success(
            f"Successfully connected to Twitch as {event.chat.username}")

    async def on_score(self, message: str):
        score: dict = json.loads(message)
        player: dict = score.get("player")
        leaderboard: dict = score.get("leaderboard")
        song: dict = leaderboard.get("song")

        accuracy = str(round(score.get("accuracy") * 100, 2))

        # await self.analytics.send(score)
        
        if not dysi(accuracy):
            # logger.debug(
            #     f"{player['name']} just got a {accuracy} on {song['name']} by {song['author']}")
            return

        async with self.client.get(f'https://api.beatleader.xyz/player/{player.get("id")}', headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }) as resp:
            player = await resp.json()

        twitter_link, twitch_link, youtube_link, beatsaver_link = extract_socials(
            player["socials"])

        clip_link = None
        rclip_link = None
        replay_url = f'https://replay.beatleader.xyz/?scoreId={score["id"]}'

        if twitch_link is not None:
            user = await first(self.twitch.get_users(logins=get_username(twitch_link)))

            if user is not None:
                await self.chat.join_room(user.login)

                await asyncio.sleep(20)
                clip_link = await self.create_clip(user)

                await self.chat.send_message(user.login, f"! WYSI @{user.login} just got a {accuracy}% on {song['name']} by {song['author']} | {clip_link or '(no clip, not live / no perms)'}")

                if clip_link is not None:  # Reaction Clip
                    await asyncio.sleep(25)
                    rclip_link = await self.create_clip(user.id)

                await self.chat.leave_room(user.login)

        display_name = await self.get_displayname(player, twitter_link)

        await self.twitter.create_tweet(text=f"#WYSI! {display_name} just got a {accuracy}% on {song['name']} ({leaderboard['difficulty']['difficultyName']}) by {song['author']}! {replay_url} {clip_link or twitch_link or ''}")

        logger.success(
            f"{display_name} just got a {accuracy}% on {song['name']} ({leaderboard.get('difficulty').get('difficultyName')}) by {song['author']}! {replay_url} {clip_link or twitch_link or ''}")

        await send_webhook(self.config, player.get("name"), accuracy, song.get("name"), song.get("author"), leaderboard.get('difficulty').get('difficultyName'), replay_url, twitter_link, twitch_link, clip_link, rclip_link, song.get("coverImage"), player.get("avatar"))

    async def get_displayname(self, player, twitter_link):
        display_name = player["name"]

        if twitter_link is not None:
            twitter_user = await self.twitter.get_user(
                username=get_username(twitter_link))

            display_name = f"@{twitter_user.data.username}"
        return display_name

    async def create_clip(self, user):
        stream = await first(self.twitch.get_streams(user_id=user.id))

        if stream is None:
            return None

        try:
            clip_resp = await self.twitch.create_clip(user.id, has_delay=True)
        except Exception as e:
            logger.warning(
                f"Tried to create a clip for {user.display_name} but was unable too.")
            logger.warning(e)

            return None

        clip_link = f"https://clips.twitch.tv/{clip_resp.id}"
        return clip_link
