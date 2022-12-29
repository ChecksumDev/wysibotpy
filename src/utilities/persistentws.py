import asyncio
from asyncio.exceptions import CancelledError

import websockets
from loguru import logger
from websockets.exceptions import WebSocketException


class PersistentWebsocket:
    """
    A class for keeping a web socket connection open indefinitely using asyncio.
    Copyright (c) 2023 Checksum.
    """

    def __init__(self, url, on_open=None, on_message=None, on_close=None):
        """
        Initializes a new WebSocketClient instance.

        Args:
            url (str): The URL of the web socket to connect to.
            on_open (callable, optional): A callback to be called when the web socket connection is opened.
            on_message (callable, optional): A callback to be called when a message is received over the web socket.
            on_close (callable, optional): A callback to be called when the web socket connection is closed.
        """
        self.url = url
        self.on_open = on_open
        self.on_message = on_message
        self.on_close = on_close

        self.websocket = None
        self.should_connect = asyncio.Event()
        self.should_connect.set()
        self.lock = asyncio.Lock()

    async def connect(self):
        """
        Connects to the web socket and listens for incoming messages.
        If the connection is closed or fails, the method will attempt to reconnect after a brief delay.
        """
        while self.should_connect.is_set():
            try:
                self.websocket = await websockets.connect(self.url)
                logger.success(
                    "Connected to web socket at {}", self.url)
                if self.on_open:
                    await self.on_open()
                await self.listen()
            except WebSocketException as e:
                logger.error("Error while connecting to web socket: {}", e)
                if self.on_close:
                    await self.on_close(e)
                self.websocket = None
                await asyncio.sleep(5)

    async def listen(self):
        """
        Listens for incoming messages over the web socket.
        If the connection is closed or fails, the method will exit.
        """
        while self.websocket and self.should_connect.is_set():
            try:
                message = await self.websocket.recv()
                if self.on_message:
                    await self.on_message(message)

            except CancelledError:
                # The program is likely shutting down.
                await self.close()

            except Exception as e:
                logger.error(
                    "Error while listening for incoming messages: {}", e)
                if self.on_close:
                    await self.on_close(e)
                self.websocket = None
                await asyncio.sleep(5)

    async def close(self):
        """
        Closes the web socket connection.
        """
        async with self.lock:
            self.should_connect.clear()
        if self.websocket:
            logger.warning("Closing web socket connection")
            await self.websocket.close()
            self.websocket = None
