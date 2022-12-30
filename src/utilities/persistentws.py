import asyncio
import websockets
from loguru import logger
from typing import Callable, Optional


class PersistentWebSocket:
    _websocket = None
    _stop = False

    def __init__(self, url: str, on_open: Optional[Callable[[], None]], on_message: Optional[Callable[[str], None]], on_close: Optional[Callable[[], None]]):
        self.url = url
        self.on_open = on_open
        self.on_message = on_message
        self.on_close = on_close
        self.reconnect_delay = 1

    async def _connect(self):
        """Connect to the WebSocket server and set the _websocket variable."""
        try:
            self._websocket = await websockets.connect(self.url)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed by server")
            self._websocket = None
        except asyncio.TimeoutError:
            logger.warning("Timed out while connecting to WebSocket")
            self._websocket = None
        except OSError as e:
            if e.errno == 101:
                logger.warning(
                    "Connection refused while connecting to WebSocket")
            else:
                logger.warning(f"Error while connecting to WebSocket: {e}")
            self._websocket = None
        except Exception as e:
            logger.exception(e)
            self._websocket = None

        if self._websocket and self.on_open:
            try:
                await self.on_open()
            except Exception as e:
                logger.exception(e)
                await self._close()

    async def _receive(self):
        """Receive messages from the WebSocket server and pass them to the on_message callback."""
        while not self._stop:
            try:
                message = await self._websocket.recv()
            except (websockets.exceptions.ConnectionClosed, asyncio.TimeoutError):
                # If the connection is closed or a timeout occurs, stop receiving messages.
                break
            except Exception as e:
                logger.exception(e)
                continue
            if self.on_message:
                try:
                    await self.on_message(message)
                except Exception as e:
                    logger.exception(e)

    async def _close(self):
        """Close the WebSocket connection and set the _websocket variable to None."""
        try:
            await self._websocket.close()
        except Exception as e:
            logger.exception(e)
        self._websocket = None
        if self.on_close:
            try:
                await self.on_close()
            except Exception as e:
                logger.exception(e)

    async def run(self):
        """Run the WebSocket connection, reconnecting on failure."""
        while not self._stop:
            if not self._websocket:
                # Connect to the WebSocket server and start receiving messages.
                await self._connect()
                if not self._websocket:
                    self.reconnect_delay = min(self.reconnect_delay * 2, 60)
                    await asyncio.sleep(self.reconnect_delay)
                    continue
                self.reconnect_delay = 1
            try:
                await self._receive()
            except Exception as e:
                # If an exception is raised, close the WebSocket connection and wait
                # before trying to reconnect.
                logger.exception(e)
                await self._close()
                self.reconnect_delay = 1
                await asyncio.sleep(self.reconnect_delay)
            else:
                # If the connection is closed normally, set the _websocket variable to None
                # and wait before trying to reconnect.
                self._websocket = None
                self.reconnect_delay = 1
                await asyncio.sleep(self.reconnect_delay)

    async def shutdown(self):
        """Shut down the WebSocket connection and stop all reconnection attempts."""
        self._stop = True
        if self._websocket:
            await self._close()
