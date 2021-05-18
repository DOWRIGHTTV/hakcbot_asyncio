#!/usr/bin/python3

import os
import asyncio
from socket import socket

from config import * # pylint: disable=unused-wildcard-import
from hakcbot_utilities import get_local_time, load_from_file, Log as L


class Initialize:
    def __init__(self):
        self._connected = False

        self._connect_process = [
            f'PASS {PASS}', # pylint: disable=undefined-variable
            f'NICK {IDENT}', # pylint: disable=undefined-variable
            f'JOIN #{CHANNEL}', # pylint: disable=undefined-variable
            'CAP REQ :twitch.tv/tags'
        ]

    @classmethod
    def setup(cls, Hakcbot):
        cls._Hakcbot = Hakcbot

    @classmethod
    async def start(cls):
        self = cls()
        await self._start()

    async def _start(self):
        self._load_json_data()

        while not self._connected:
            try:
                await self._join_room()

            except OSError:
                L.l0(f'{get_local_time()}: connection failure.')

            else:
                await self._wait_for_eol()

    async def _join_room(self):
        loop = asyncio.get_running_loop()

        self._Hakcbot._sock.setblocking(0)

        await loop.sock_connect(self._Hakcbot._sock, (self._host, self._port))
        for step in self._connect_process:
            await loop.sock_sendall(self._Hakcbot._sock, f'{step}\r\n'.encode('utf-8'))

        self._connected = True

    async def _wait_for_eol(self):
        loop = asyncio.get_running_loop()
        while True:
            data = await loop.sock_recv(self._Hakcbot._sock, 1024)
            data = data.decode('utf-8', 'ignore').strip()
            if ('authentication failed' in data):
                L.l0('Authentication failure!')
                os._exit(1)

            if ('End of /NAMES list' in data):
                L.l1('hakcbot: NOW CONNECTED TO INTERWEBS. PREPARE FOR CYBER WARFARE.')
                break

    def _load_json_data(self):
        stored_data = load_from_file('config')

        self._host = stored_data['twitch']['host']
        self._port = stored_data['twitch']['port']
