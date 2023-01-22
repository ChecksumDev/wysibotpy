import asyncio

from loguru import logger

from modules.bot import Client
from utilities.config import get_config


config = get_config()
client = Client(config)


@logger.catch
async def main():
    await client.start()

if __name__ == "__main__":
    asyncio.run(main())
