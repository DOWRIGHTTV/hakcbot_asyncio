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
from hakcbot_utilities import load_from_file, write_to_file
from datetime import datetime
from hakcbot_commands import Commands
from hakcbot_utilities import CommandStructure as cs


class Execute:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        self.invalid_chars = ['!', '/', '.', ' ']

    ## checking each word in message for a command.
    async def parse_message(self, user, message):
        for word in message:
            cmd, args = await self._get_command(word)
            if (not cmd): continue

            try:
                cd_len, response = await getattr(self.Hakcbot.Commands, cmd)(*args, usr=user)
            except TypeError:
                continue

            if (cd_len):
                await self._apply_cooldown(cmd, cd_len)
            if (response):
                await self.Hakcbot.send_message(*response)

    ## adjust URL whitelist on mod command, will call itself if list is updated
    ## to update running set while bot is running.
    async def adjust_titles(self, user=None, title=None, action=None):
        loop   = asyncio.get_running_loop()
        config = load_from_file('config.json')

        self.titles = config['titles']
        if (not user):
            return

        if (action is True):
            self.titles[user.lower()] = title
            print(f'hakcbot: added title: {title} for {user}')

        elif (action is False):
            self.titles.pop(user.lower(), None)
            print(f'hakcbot: removed title: {title} for {user}')

        await loop.run_in_executor(None, write_to_file, config, 'config.json')
        await self.adjust_titles()

    async def _apply_cooldown(self, cmd, cd_len):
        print(f'Putting {cmd} on cooldown.')
        print(cmd, cd_len)
        cs.COMMANDS[cmd] = time.time() + (cd_len*60)

    async def _get_command(self, word):
        if not re.fullmatch(VALID_CMD, word):
            return NULL

        cmd = re.findall(CMD, word)[0]
        if (cmd not in cs.COMMANDS):
            return NULL

        args = re.findall(ARG, word)[0]
        for bad in self.invalid_chars:
            if (bad in cmd or bad in args): return NULL

        return cmd, tuple(a for a in args.split(',') if a)
