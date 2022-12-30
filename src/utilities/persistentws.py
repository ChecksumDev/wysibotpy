import typing
import asyncio
import websockets
from loguru import logger


class PersistentWebSocket:
    """Async websockets implementation to hold a single socket connection open forever, regardless of errors."""

    def __init__(self, url: str, on_message: typing.Callable[[str], None], max_backoff=60):
        self.url = url
        self.on_message = on_message
        self.socket = None
        self.stop = False
        self.max_backoff = max_backoff

    async def connect(self, backoff=2):
        self.backoff_delay = 1
        while not self.stop:
            try:
                self.socket = await websockets.connect(self.url)
                logger.info("Connected to websocket server at {}", self.url)
                return
            except Exception as e:
                logger.exception(
                    "Failed to connect to websocket server at {}: {}", self.url, e)
                self.backoff_delay = min(
                    self.backoff_delay * backoff, self.max_backoff)
                await asyncio.sleep(self.backoff_delay)

    async def listen(self):
        """Listen for messages from the websocket server"""
        while not self.stop:
            try:
                message = await asyncio.ensure_future(self.socket.recv())
                # logger.debug("Received message: {}", message)
                await self.on_message(message)
            except Exception as e:
                logger.exception("Error while receiving message: {}", e)

    async def run(self):
        """Connect to the websocket server and listen for messages forever"""
        await self.connect()
        await self.listen()
