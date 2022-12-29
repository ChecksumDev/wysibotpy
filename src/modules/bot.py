import asyncio
import json
from configparser import ConfigParser

from aiohttp.client import ClientSession
from loguru import logger
from tweepy.asynchronous import AsyncClient as TwitterClient
from tweepy.models import User
from twitchAPI import Twitch
from twitchAPI.chat import Chat, ChatEvent, EventData
from twitchAPI.helper import first
from twitchAPI.oauth import AuthScope

from modules.discord import send_webhook
from utilities.persistentws import PersistentWebsocket
from utilities.tools import dysi, extract_socials, get_username


class Client:
    def __init__(self, config: ConfigParser):
        self.config = config
        self.scopes = [scope for scope in AuthScope]
        self.client = ClientSession()
        self.ws = PersistentWebsocket(
            "wss://api.beatleader.xyz/scores", on_message=self.on_score)

        self.twitch: Twitch

    async def start(self):
        self.twitter = TwitterClient(
            bearer_token=self.config.get("twitter", "bearer_token"),
            consumer_key=self.config.get("twitter", "app_key"),
            consumer_secret=self.config.get("twitter", "app_secret"),
            access_token=self.config.get("twitter", "access_token"),
            access_token_secret=self.config.get("twitter", "access_secret"),
        )

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
        await self.ws.connect()

    async def shutdown(self):
        logger.info("Shutting down.")
        await self.ws.close()
        await self.client.close()
        self.chat.stop()

    async def on_ready(self, event: EventData):
        logger.success("Successfully connected to Twitch")

    @logger.catch
    async def on_score(self, message: str):
        score: dict = json.loads(message)
        player: dict = score.get("player")
        leaderboard: dict = score.get("leaderboard")
        song: dict = leaderboard.get("song")

        accuracy = str(round(score.get("accuracy") * 100, 2))

        if not dysi(accuracy):
            return

        async with self.client.get(f'https://api.beatleader.xyz/player/{player.get("id")}', headers={
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }) as resp:
            player = await resp.json()

        twitter_link, twitch_link, youtube_link, beatsaver_link = extract_socials(
            player["socials"])

        clip_link = None
        reaction_clip = None
        replay_url = f'https://replay.beatleader.xyz/?scoreId={score["id"]}'

        if twitch_link is not None:
            user = await first(self.twitch.get_users(logins=get_username(twitch_link)))

            if user is not None:
                await self.chat.join_room(user.login)

                stream = await first(self.twitch.get_streams(user_id=user.id))
                if stream is not None:
                    await asyncio.sleep(20)

                    try:
                        clip_resp = await self.twitch.create_clip(user.id)
                        clip_link = f"https://clips.twitch.tv/{clip_resp.id}"
                    except:
                        logger.warning(
                            f"Tried to create a clip for {user.display_name} but was unable too.")

                await self.chat.send_message(user.login, f"! WYSI @{user.login} just got a {accuracy}% on {song['name']} by {song['author']} | {clip_link or '(no clip, not live / no perms)'}")

                await self.chat.leave_room(user.login)

        display_name = player["name"]
        if twitter_link is not None:
            twitter_user = await self.twitter.get_user(
                username=get_username(twitter_link))

            display_name = f"@{twitter_user.data.username}"

        await self.twitter.create_tweet(text=f"{display_name} just got a {accuracy}% on {song['name']} ({leaderboard['difficulty']['difficultyName']}) by {song['author']}! {replay_url} {clip_link or twitch_link or ''}")

        logger.success(
            f"{display_name} just got a {accuracy}% on {song['name']} ({leaderboard.get('difficulty').get('difficultyName')}) by {song['author']}! {replay_url} {clip_link or twitch_link or ''}")

        if clip_link is not None:
            # First clip worked, second one will also likely work.
            await asyncio.sleep(25)
            reaction_clip = await self.twitch.create_clip(user.id)

        await send_webhook(self.config, player.get("name"), accuracy, song.get("name"), song.get("author"), leaderboard.get('difficulty').get('difficultyName'), replay_url, twitter_link, twitch_link, clip_link, reaction_clip, song.get("coverImage"), player.get("avatar"))
