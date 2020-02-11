#!/usr/bin/env python3

import re
import json
import time
import asyncio
import requests

# pylint: disable=no-name-in-module, unused-wildcard-import
from hakcbot_regex import *
from config import CHANNEL
from hakcbot_utilities import load_from_file


class Commands:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        config = load_from_file('config.json')
        self.standard_commands     = config['commands']['standard']
        self.non_standard_commands = config['commands']['non_standard']
        self.automated             = config['commands']['automated']
        self.quotes                = config['quotes']

        for cmd in self.standard_commands:
            setattr(self, f'hakc{cmd}', 0)

        for cmd in self.non_standard_commands:
            setattr(self, f'hakc{cmd}', 0)

    async def get_standard_command(self, command):
        try:
            message = self.standard_commands[command]['message']
            cd_name = self.standard_commands[command]['cd_name']
            cd_time = self.standard_commands[command]['cd_time']
        except KeyError:
            return None, None

        if (command == 'uptime'):
            message = self.Hakcbot.uptime_message

        if (command == 'time'):
            current_time = time.localtime()
            ltime = time.strftime('%H:%M:%S', current_time)
            message = f'{message} {ltime}'

        await self.Hakcbot.send_message(message)

        return cd_name, cd_time

    async def get_non_standard_command(self, command, arg, username):
        try:
            message = self.non_standard_commands[command]['message']
            cd_name = self.non_standard_commands[command]['cd_name']
            cd_time = self.non_standard_commands[command]['cd_time']
        except KeyError:
            return None, None

        if (command == 'quote'):
            if (arg not in self.quotes):
                return None, None

            message = self.quotes[arg]
            message = f'{message[0]} - {CHANNEL} {message[1]}'
            await self.Hakcbot.send_message(message)

        elif (command in ['yourmom', 'yourmum']):
            message = f"{username}'s {message}"
            await self.Hakcbot.send_message(message)

        elif (command == 'praise'):
            if (arg == 'thesun'):
                message += ' (thesun)'
            else:
                message += f' ({username})'

        return cd_name, cd_time
