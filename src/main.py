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
        asyncio.run(main())
    except (KeyboardInterrupt):
        asyncio.run(client.shutdown())
