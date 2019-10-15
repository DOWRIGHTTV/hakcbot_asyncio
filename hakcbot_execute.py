#!/usr/bin/python3


import re
import threading
import asyncio
import time
import requests
import json
import traceback

from config import *
from regex import *
from datetime import datetime

class Execute:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

    async def parse_message(self, user, message):
        now = time.time()
        ## Checking each word in message for a command. if a command is found will switch go to be true
        ## which will prevent any further checks. this makes it so only the first command gets ran.
        for word in message:
            word = word.lower().strip('\r')
            command = None
            if ('(' in word and word.endswith(')')):
                command = word.split('(')[0]
                command_arg = word.split('(')[1].strip(')')

            if (command in self.Hakcbot.Commands.standard_commands
                    or command in self.Hakcbot.Commands.non_standard_commands):
                print(command, command_arg)
                cd_expire = getattr(self.Hakcbot.Commands, f'hakc{command}')
                if (now > cd_expire or user in self.Hakcbot.mod_list):
                    if (not command_arg):
                        command, CD = await self.Hakcbot.Commands.get_standard_command(command)
                    else:
                        command, CD = await self.Hakcbot.Commands.get_non_standard_command(command, command_arg)
                    await self.command_cooldown(command, CD)

                    break

            command = word.split('(')

    async def command_cooldown(self, command, CD):
        cd_expire = time.time() + CD

        print(f'Putting {command} on cooldown.')
        setattr(self.Hakcbot.Commands, f'hakc{command}', cd_expire)
