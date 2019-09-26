#!/usr/bin/env python3

import re
import json
import time
import asyncio
import requests

from regex import *


class Commands:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        self.cmds = set()
        self.uList = set()

        with open('commands.json', 'r') as cmds:
            commands = json.load(cmds)
        self.commands = commands['standard']
        self.automated = commands['automated']

        with open('quotes.json', 'r') as quotes:
            quote = json.load(quotes)
        self.quotes = quote['quotes']

        for cmd in self.commands:
            cmd = cmd.lower()
            setattr(self, f'{cmd}_cooldown', False)

        self.hakcpraise = False
        self.hakcyourmom = False
        self.hakcyourmum = False

    async def HandleCommand(self, user, message, command):
        cmd, CD = await self.Praiser(message)
        if (not cmd):
             cmd, CD = await self.StandardCommand(command)

        return cmd, CD

    async def StandardCommand(self, command):
        loop = asyncio.get_running_loop()
        name = self.commands[command]['cd_name']
        message = self.commands[command]['message']
        CD = self.commands[command]['cd_time']

        if (command == 'uptime'):
            uptime = [loop.run_in_executor(None, self.Uptime, command)]
            completed, _ = await asyncio.wait(uptime)
            await self.HandleUptime(completed)

            return

        if (command == 'time'):
            current_time = time.localtime()
            ltime = time.strftime('%H:%M:%S', current_time)
            message = f'{message} {ltime}'

        await self.Hakcbot.SendMessage(message)

        return name, CD

    def Uptime(self, cmd):
        uptime = requests.get("https://decapi.me/twitch/uptime?channel=dowright")
        uptime = uptime.text.strip('\n')
        if (uptime == 'dowright is offline'):
            message = 'DOWRIGHT is offline'
        else:
            message = self.commands[cmd]['message']
            message = f'{message} {uptime}'

        return message

    async def HandleUptime(self, completed):
        for message in completed:
            message = message.result()
            await self.Hakcbot.SendMessage(message)

    async def Praiser(self, message):
        if ('!' in message or '/' in message or '.' in message or ' ' in message):
            pass
        else:
            hakcpraise = re.findall(PRAISE, message)
            cooldown = self.hakcpraise
            if (hakcpraise and not cooldown):
                target = hakcpraise[0]
                response = f'Praise the ({target}) \ [T] /'
                if (target == 'thesun'):
                    response = "\ [T] /"

                await self.Hakcbot.SendMessage(response)

                return 'hakcpraise', 120

        return None, None
