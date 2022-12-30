import asyncio

from loguru import logger

from modules.bot import Client
from utilities.config import get_config


@logger.catch
async def main():
    await client.start()

if __name__ == "__main__":
    config = get_config()
    client = Client(config)

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except (KeyboardInterrupt):
        loop.run_until_complete(client.shutdown())
