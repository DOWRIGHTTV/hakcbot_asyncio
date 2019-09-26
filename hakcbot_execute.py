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

    async def Main(self, line):
        try:
            user, msg, subscriber, badge = await self.Parse(line)
            await self.ParseMessage(user, msg)

        except Exception:
            traceback.print_exc()

    async def ParseMessage(self, user, msg):
        now = time.time()
        ## Checking each word in message for a command. if a command is found will switch go to be true
        ## which will prevent any further checks. this makes it so only the first command gets ran.
        for word in msg:
            word = word.lower().strip('\r')
            command = word.strip('()')
            if (command in self.Hakcbot.Commands.commands and word.endswith('()')):
                cd_expire = getattr(self.Hakcbot.Commands, f'hakc{command}')
                if (now > cd_expire or user in self.Hakcbot.mod_list):
                    command, CD = await self.Hakcbot.Commands.HandleCommand(user, msg, command)

                    await self.Cooldown(command, CD)

                    break

    async def Parse(self, line):
        tags = re.findall(USER_TAGS, line)[0]
        tags = tags.split(';')
        badges = tags[1]
        subscriber = tags[9]

        msg = re.findall(MESSAGE, line)[0]
        msg = msg.split(':', 2)
        message = msg[2]

        user = msg[1].split('!')
        user = user[0]

        print(f'{user}: {message}')

        return user, msg, subscriber, badges

    async def Cooldown(self, command, CD):
        cd_expire = time.time() + CD

        print(f'Putting {command} on cooldown.')
        setattr(self.Hakcbot.Commands, f'hakc{command}', cd_expire)

