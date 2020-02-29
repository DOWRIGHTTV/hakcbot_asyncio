#!/usr/bin/python3

import asyncio
from socket import socket

# pylint: disable=unused-wildcard-import
from config import *
from hakcbot_utilities import load_from_file


class Init:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot
        self.Hakcbot.sock.setblocking(0)

    async def initialize(self):
        self._load_json_data()

        await self._join_room()
        await self._wait_for_eol()

    async def _join_room(self):
        loop = asyncio.get_running_loop()

        await loop.sock_connect(self.Hakcbot.sock, (HOST, PORT))
        await loop.sock_sendall(self.Hakcbot.sock, f'PASS {PASS}\r\n'.encode('utf-8'))
        await loop.sock_sendall(self.Hakcbot.sock, f'NICK {IDENT}\r\n'.encode('utf-8'))
        await loop.sock_sendall(self.Hakcbot.sock, f'JOIN #{CHANNEL}\r\n'.encode('utf-8'))
        await loop.sock_sendall(self.Hakcbot.sock, 'CAP REQ :twitch.tv/tags\r\n'.encode('utf-8'))

    async def _wait_for_eol(self):
        loop = asyncio.get_running_loop()
        while True:
            data = await loop.sock_recv(self.Hakcbot.sock, 1024)
            data = data.decode('utf-8', 'ignore').strip()
            if ('End of /NAMES list' in data):
                print('HAKCBOT NOW CONNECTED TO INTERWEBS. PREPARE FOR CYBER WARFARE.')
                break

    def _load_json_data(self):
        stored_data = load_from_file('config.json')

        self.Hakcbot.titles = stored_data['titles']
        self.Hakcbot.quotes = stored_data['quotes']
        self.Hakcbot.whitelist = stored_data['whitelist']
        self.Hakcbot.blacklist = stored_data['blacklist']