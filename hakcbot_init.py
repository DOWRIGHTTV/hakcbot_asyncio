#!/usr/bin/python3

import asyncio
from socket import socket

# pylint: disable=unused-wildcard-import
from config import *


class Hakcbot:
    def __init__(self):
        self.sock = socket()
        self.sock.setblocking(0)

    async def connect(self):
        await self.join_room()
        await self.validate_connection()

    # pylint: disable=undefined-variable
    async def join_room(self):
        loop = asyncio.get_running_loop()

        await loop.sock_connect(self.sock, (HOST, PORT))

        await loop.sock_sendall(self.sock, f'PASS {PASS}\r\n'.encode('utf-8'))
        await loop.sock_sendall(self.sock, f'NICK {IDENT}\r\n'.encode('utf-8'))
        await loop.sock_sendall(self.sock, f'JOIN #{CHANNEL}\r\n'.encode('utf-8'))
        await loop.sock_sendall(self.sock, f'CAP REQ :twitch.tv/tags\r\n'.encode('utf-8'))

    async def validate_connection(self):
        loop = asyncio.get_running_loop()
        recv_buffer = ''
        Loading = True
        while Loading:
            recv_buffer = await loop.sock_recv(self.sock, 1024)
            recv_buffer = recv_buffer.decode('utf-8', 'ignore')
            join = recv_buffer.split('\n')
            recv_buffer = join.pop()

            for line in join:
                print(line)
                if ('End of /NAMES list' in line):
                    Loading = False
