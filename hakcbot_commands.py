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

        with open('commands.json', 'r') as cmds:
            commands = json.load(cmds)
        self.commands = commands['standard']
        self.automated = commands['automated']

        with open('quotes.json', 'r') as quotes:
            quote = json.load(quotes)
        self.quotes = quote['quotes']

        for cmd in self.commands:
            setattr(self, f'hakc{cmd}', 0)

    async def HandleCommand(self, user, message, command):
        cmd, CD = await self.StandardCommand(command)

        return cmd, CD

    async def StandardCommand(self, command):
        name = self.commands[command]['cd_name']
        message = self.commands[command]['message']
        CD = self.commands[command]['cd_time']

        if (command == 'uptime'):
            message = self.Hakcbot.uptime_message

        if (command == 'time'):
            current_time = time.localtime()
            ltime = time.strftime('%H:%M:%S', current_time)
            message = f'{message} {ltime}'

        await self.Hakcbot.SendMessage(message)

        return name, CD
