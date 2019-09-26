#!/usr/bin/python3

import threading, asyncio
import re, json
import requests
import time
import traceback

from config import *

from hakcbot_init import Hakcbot
from hakcbot_execute import Execute
from hakcbot_spam import Spam
from hakcbot_commands import Commands

class Run:
    def __init__(self):
        self.Hakcbot = Hakcbot()

        self.Automate = Automate(self)
        self.Execute = Execute(self)
        self.Spam = Spam(self)
        self.Commands = Commands(self)

        self.linecount = 0

        self.online = False

        with open('roles.json', 'r') as roles:
            role = json.load(roles)
        self.mod_list = role['user_roles']['mods']

    def Start(self):

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        asyncio.run(self.Main())

    async def Main(self):
        await self.Hakcbot.Connect()

        await self.Spam.TLDSetCreate()
        await self.Spam.BlacklistAdjust()
        await self.Spam.WhitelistAdjust()

        await asyncio.gather(self.Hakc(), self.Hakc2(), self.CheckOnline())

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

    async def SendMessage(self, message):
        loop = asyncio.get_running_loop()
        mT = f'PRIVMSG #{CHANNEL} :{message}'
        await loop.sock_sendall(self.Hakcbot.sock, f'{mT}\r\n'.encode('utf-8'))
        print(f'hakcbot: {message}')

    async def CheckOnline(self):
        loop = asyncio.get_running_loop()
        ## start thread to contuously check if online
        await loop.run_in_executor(None, self.Automate.CheckOnline)

class Automate:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        with open('commands.json', 'r') as cmds:
            commands = json.load(cmds)

        self.commands = commands['standard']

    async def Timers(self, cmd, timer):
        try:
            message = self.commands[cmd]['message']
            while True:
                await asyncio.sleep(60 * timer)
                print(f'Line Count: {self.Hakcbot.linecount}')
                if (self.Hakcbot.linecount >= 3 and getattr(self.Hakcbot.Commands, f'hakc{cmd.lower()}')):
                    self.Hakcbot.SendMessage(message)
                elif (not getattr(self.Hakcbot.Commands, f'hakc{cmd.lower()}')):
                    print(f'hakcbot: {cmd} command on cooldown')
        except Exception as E:
            print(f'AsyncIO Timer Error: {E}')

    def CheckOnline(self):
        while True:
            uptime = requests.get("https://decapi.me/twitch/uptime?channel=dowright")
            uptime = uptime.text.strip('\n')
            if (uptime != 'dowright is offline'):
                self.Hakcbot.online = True
            else:
                self.Hakcbot.online = False

            time.sleep(60 * 10)

def Main():
    Hakcbot = Run()
    Hakcbot.Start()

if __name__ == '__main__':
    try:
        Main()
    except KeyboardInterrupt:
        print('Exiting Hakcbot :(')
