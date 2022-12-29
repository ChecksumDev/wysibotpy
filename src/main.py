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
        task = loop.create_task(main())
        task.add_done_callback(lambda _: asyncio.run(client.shutdown()))
        loop.run_until_complete(task)
    except (KeyboardInterrupt):
        asyncio.run(client.shutdown())
