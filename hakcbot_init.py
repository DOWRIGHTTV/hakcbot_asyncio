#!/usr/bin/python3

import os
import asyncio
from socket import socket

from config import * # pylint: disable=unused-wildcard-import
from hakcbot_utilities import load_from_file, Log as L


class Init:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot
        self.Hakcbot.sock.setblocking(0)

        self.connect_process = [
            f'PASS {PASS}',
            f'NICK {IDENT}',
            f'JOIN #{CHANNEL}',
            'CAP REQ :twitch.tv/tags'
        ]

    async def initialize(self):
        self._load_json_data()
        self._create_tld_set()

        await self._join_room()
        await self._wait_for_eol()

    async def _join_room(self):
        loop = asyncio.get_running_loop()

        await loop.sock_connect(self.Hakcbot.sock, (HOST, PORT))
        for step in self.connect_process:
            await loop.sock_sendall(self.Hakcbot.sock, f'{step}\r\n'.encode('utf-8'))

    async def _wait_for_eol(self):
        loop = asyncio.get_running_loop()
        while True:
            data = await loop.sock_recv(self.Hakcbot.sock, 1024)
            data = data.decode('utf-8', 'ignore').strip()
            if ('authentication failed' in data):
                L.l0('Authentication failure!')
                os._exit(1)
            if ('End of /NAMES list' in data):
                L.l1('hakcbot: NOW CONNECTED TO INTERWEBS. PREPARE FOR CYBER WARFARE.')
                break

    def _load_json_data(self):
        stored_data = load_from_file('config.json')

        self.Hakcbot.titles = stored_data['titles']
        self.Hakcbot.quotes = stored_data['quotes']
        self.Hakcbot.url_whitelist = set(stored_data['url_whitelist']) # NOTE: easier to deal with a set
        self.Hakcbot.word_filter   = stored_data['word_filter']

    def _create_tld_set(self):
        with open('TLDs') as TLDs:
            tlds = TLDs.read().splitlines()

        self.Hakcbot.domain_tlds = set(t.lower() for t in tlds if len(t) <= 6 and not t.startswith('#'))