#!/usr/bin/python3

import os
import asyncio
from socket import socket

from config import * # pylint: disable=unused-wildcard-import
from hakcbot_utilities import load_from_file, Log as L


class Initialize:
    def __init__(self):
        self._connect_process = [
            f'PASS {PASS}',
            f'NICK {IDENT}',
            f'JOIN #{CHANNEL}',
            'CAP REQ :twitch.tv/tags'
        ]

    @classmethod
    def setup(cls, Hakcbot):
        cls._Hakcbot = Hakcbot

    @classmethod
    async def start(cls):
        self = cls()
        self._start()

    async def _start(self):
        self._load_json_data()

        await self._join_room()
        await self._wait_for_eol()

    async def _join_room(self):
        loop = asyncio.get_running_loop()

        self._Hakcbot._sock.setblocking(0)

        await loop.sock_connect(self._Hakcbot._sock, (self._host, self._port))
        for step in self._connect_process:
            await loop.sock_sendall(self._Hakcbot._sock, f'{step}\r\n'.encode('utf-8'))

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

    # TODO: remove this from init class. this should be a function of the main bot class and init should only
    # be used for initial connection to the server.
    def _load_json_data(self):
        stored_data = load_from_file('config')

        self._Hakcbot.titles = stored_data['titles']
        self._Hakcbot.quotes = stored_data['quotes']

        self._host = stored_data['twitch']['host']
        self._port = stored_data['twitch']['port']
