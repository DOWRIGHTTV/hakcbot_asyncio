#!/usr/bin/python3


import re
import threading
import asyncio
import time
import requests
import json
import traceback

from config import *
from hakcbot_regex import *
from datetime import datetime

class Execute:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        self.invalid_chars = ['!', '/', '.', ' ']

    async def parse_message(self, user, message):
        ## Checking each word in message for a command. if a command is found will switch go to be true
        ## which will prevent any further checks. this makes it so only the first command gets ran.
        for word in message:
            word = word.lower().strip('\r')
            if ('(' not in word or not word.endswith(')')):
                continue

            command     = re.findall(COMMAND, word)
            command_arg = re.findall(COMMAND_ARG, word)
            if (not self.valid_command(command)):
                continue

            cd_expire = getattr(self.Hakcbot.Commands, f'hakc{command}')
            print(f'TIMESTAMP: {user.timestamp} | CD EXPIRE: {cd_expire}')
            if (user.timestamp < cd_expire or not user.mod or user.name != BROADCASTER):
                continue

            if (not command_arg):
                command, CD = await self.Hakcbot.Commands.get_standard_command(command)
            else:
                command, CD = await self.Hakcbot.Commands.get_non_standard_command(command, command_arg, user.name)

            if (CD):
                await self.command_cooldown(command, CD)

            break

    async def command_cooldown(self, command, CD):
        cd_expire = time.time() + CD

        print(f'Putting {command} on cooldown.')
        setattr(self.Hakcbot.Commands, f'hakc{command}', cd_expire)

    async def valid_command(self, command):
        if (not command in self.Hakcbot.Commands.standard_commands
                or not command in self.Hakcbot.Commands.non_standard_commands):
            return False

        for bad in self.invalid_chars:
            if bad not in command: continue

            return False

        return True
