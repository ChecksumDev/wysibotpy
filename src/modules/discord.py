from configparser import ConfigParser

from aiohttp import ClientSession
from loguru import logger


async def send_webhook(config: ConfigParser, player_name: str, accuracy: float, song_name: str, song_author: str, diff: str, replay_url: str, twitter_url: str, twitch_url: str, twitch_clip: str, twitch_reaction_clip: str, song_cover: str, player_avatar: str) -> None:
    embed = {
        "title": "WHEN YOU SEE IT!",
        "color": 16719223,
        "fields": [
            {
                "name": "Information",
                "value": f"**Player**: {player_name}\n**Accuracy**: {accuracy}%\n\n**Map**: {song_name} by {song_author} ({diff})\n**Replay**: {replay_url}"
            },
            {
                "name": "Links",
                "value": f"**Twitter**: {twitter_url or 'N/A'}\n**Twitch**: {twitch_url or 'N/A'}\n**Twitch Clip**: {twitch_clip or 'N/A'}\n**Twitch R. Clip**: {twitch_reaction_clip or 'N/A'}"
            }
        ],
        "image": {
            "url": song_cover
        },
        "thumbnail": {
            "url": player_avatar
        }
    }

    async with ClientSession() as session:
        async with session.post(config.get("discord", "webhook"), json={"embeds": [embed]}) as resp:
            pass
