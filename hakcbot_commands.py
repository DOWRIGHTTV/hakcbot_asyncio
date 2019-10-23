#!/usr/bin/env python3

import re
import json
import time
import asyncio
import requests

from regex import *
from hakcbot_utilities import load_from_file


class Commands:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        commands = load_from_file('commands.json')
        self.standard_commands = commands['standard']
        self.non_standard_commands = commands['non_standard']
        self.automated = commands['automated']

        quotes = load_from_file('quotes.json')
        self.quotes = quotes['quotes']

        for cmd in self.standard_commands:
            setattr(self, f'hakc{cmd}', 0)

        for cmd in self.non_standard_commands:
            setattr(self, f'hakc{cmd}', 0)

    # async def HandleCommand(self, user, message, command, standard):
    #     if (standard):
    #         cmd, CD = await self.StandardCommand(command)
    #     elif (not standard):
    #         cmd, CD = await self.NonStandardCommand(command)

    #     return cmd, CD

    async def get_standard_command(self, command):
        name = self.standard_commands[command]['cd_name']
        message = self.standard_commands[command]['message']
        CD = self.standard_commands[command]['cd_time']

        if (command == 'uptime'):
            message = self.Hakcbot.uptime_message

        if (command == 'time'):
            current_time = time.localtime()
            ltime = time.strftime('%H:%M:%S', current_time)
            message = f'{message} {ltime}'

        await self.Hakcbot.send_message(message)

        return name, CD

    async def get_non_standard_command(self, command, arg):
        return None, None