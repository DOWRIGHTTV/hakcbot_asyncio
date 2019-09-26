#!/usr/bin/python3

import threading, asyncio
import re, json
import requests
import time
import traceback

from config import *
from collections import deque

from hakcbot_init import Hakcbot
from hakcbot_threads import Threads
from hakcbot_execute import Execute
from hakcbot_spam import Spam
from hakcbot_commands import Commands

class Run:
    def __init__(self):
        self.Hakcbot = Hakcbot()

        self.Threads = Threads(self)
        self.Automate = Automate(self)
        self.Execute = Execute(self)
        self.Spam = Spam(self)
        self.Commands = Commands(self)

        self.linecount = 0

        self.online = False
        self.uptime_message = 'DOWRIGHT is OFFLINE.'

        with open('roles.json', 'r') as roles:
            role = json.load(roles)
        self.mod_list = role['user_roles']['mods']

    def Start(self):
        self.Threads.Start()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        asyncio.run(self.Main())

    async def Main(self):
        await self.Hakcbot.Connect()

        await self.Spam.TLDSetCreate()
        await self.Spam.BlacklistAdjust()
        await self.Spam.WhitelistAdjust()

        await asyncio.gather(self.Hakc(), self.Hakc2())

    async def Hakc(self):
        loop = asyncio.get_running_loop()
        recv_buffer =  ''
        try:
            while True:
                recv_buffer = await loop.sock_recv(self.Hakcbot.sock, 1024)
                recv_buffer = recv_buffer.decode('utf-8', 'ignore')
                chat = recv_buffer.split('\n')
                recv_buffer = chat.pop()

                for line in chat:
                    if ('PING :tmi.twitch.tv\r' == line):
                        print(line)
                        self.linecount = 0
                        await loop.sock_sendall(self.Hakcbot.sock, 'PONG :tmi.twitch.tv\r\n'.encode('utf-8'))

                    elif ('PRIVMSG' in line):
                        spam = await self.Spam.Main(line)
                        if (not spam):
                            await self.Execute.Main(line)
                            self.linecount += 1

                    elif ('JOIN' in line):
                        pass
                        # placeholder for when i want to track joins/ see if a user joins
        except Exception as E:
            traceback.print_exc()
            print(f'Main Process Error: {E}')

    async def Hakc2(self):
        cmds = []
        timers = []

        for t_count, cmd in enumerate(self.Commands.automated, 1):
            cmds.append(cmd)
            timers.append(self.Commands.automated[cmd]['timer'])

        try:
            await asyncio.gather(*[self.Automate.Timers(cmds[t], timers[t]) for t in range(t_count)])
        except Exception as E:
            print(f'AsyncIO General Error | {E}')

    async def SendMessage(self, message, response=None):
        loop = asyncio.get_running_loop()
        print(f'hakcbot: {message}')
        message = f'PRIVMSG #{CHANNEL} :{message}'

        await loop.sock_sendall(self.Hakcbot.sock, f'{message}\r\n'.encode('utf-8'))
        if (response):
            response = f'PRIVMSG #{CHANNEL} :{response}'
            await loop.sock_sendall(self.Hakcbot.sock, f'{response}\r\n'.encode("utf-8"))

class Automate:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        self.flag_for_timeout = deque()

    async def Timers(self, cmd, timer):
        try:
            message = self.Hakcbot.Commands.commands[cmd]['message']
            while True:
                await asyncio.sleep(60 * timer)
                print(f'Line Count: {self.Hakcbot.linecount}')
                cooldown = getattr(self.Hakcbot.Commands, f'hakc{cmd}')
                if (not cooldown and self.Hakcbot.linecount >= 3):
                    await self.Hakcbot.SendMessage(message)
                elif (cooldown):
                    print(f'hakcbot: {cmd} command on cooldown')
        except Exception as E:
            print(f'AsyncIO Timer Error: {E}')

    async def AutomateTimeout(self):
        while True:
            if (not self.flag_for_timeout):
                await asyncio.sleep(1)
                continue

            while self.flag_for_timeout:
                user = self.flag_for_timeout.popleft()
                message = f'/timeout {user} 3600 account age less than one day.'
#            response = f'sorry {user}, accounts must be older than 1 day to talk in chat.'

                await self.Hakcbot.SendMessage(message)

def Main():
    Hakcbot = Run()
    Hakcbot.Start()

if __name__ == '__main__':
    try:
        Main()
    except KeyboardInterrupt:
        print('Exiting Hakcbot :(')
