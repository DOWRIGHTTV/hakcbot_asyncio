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
from hakcbot_utilities import Log as L
from string import ascii_letters, digits


class Execute:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

    ## checking each word in message for a command.
    async def task_handler(self, user, message):
        # if user is broadcaster and the join of words matches a valid command, the return will be the join.
        # otherwise the original message will be returned
        message = self._special_check(user, message)
        for word in message:
            cmd, args = self._get_command(word)
            if (not cmd): continue

            try:
                cd_len, response = getattr(self.Hakcbot.Commands, cmd)(*args, usr=user) # pylint: disable=not-an-iterable
            except Exception as E:
                L.l0(E)
                continue

            if (cd_len):
                self._apply_cooldown(cmd, cd_len)
            if (response):
                await self.Hakcbot.send_message(*response)

    def adjust_whitelist(self, url, action=AK.ADD):
        if (action is AK.ADD):
            self.Hakcbot.url_whitelist.append(url.lower())
            L.l1(f'added {url} to whitelist')

        elif (action is AK.DEL):
            self.Hakcbot.url_whitelist.pop(url.lower(), None)
            L.l1(f'removed {url} from whitelist')

        self.Hakcbot.Threads.add_file_task('url_whitelist')

    # NOTE: currently unused
    def adjust_blacklist(self, url=None, action=None):
        config = load_from_file('config.json')
        self.blacklist = set(config['blacklist'])

    def adjust_titles(self, name, title, *, action=AK.ADD):
        if (action is AK.ADD):
            self.Hakcbot.titles[name] = title
            L.l1(f'added title for {name}, the {title}.')

        elif (action is AK.MOD):
            old_title = self.Hakcbot.titles.get(name)
            self.Hakcbot.titles[name] = title
            L.l1(f'updated title for {name}, the {title} formerly the {old_title}.')

        elif (action is AK.DEL):
            self.Hakcbot.titles.pop(name, None)
            L.l1(f'removed title for {name}, the {title}.')

        self.Hakcbot.Threads.add_file_task('titles')

    def _special_check(self, usr, msg):
        if (not usr.bcast): return msg

        join_msg = ' '.join(msg)
        if not re.fullmatch(VALID_CMD, join_msg): return msg

        cmd = re.findall(CMD, join_msg)[0]
        if cmd not in self.Hakcbot.Commands._SPECIAL: return msg

        L.l3(f'returning special command {join_msg}')
        return [join_msg]

    def _get_title(self, arg):
        title = re.match(TITLE, arg)
        return title[0] if title else None

    def _apply_cooldown(self, cmd, cd_len):
        L.l1(f'Putting {cmd} on cooldown.')
        self.Hakcbot.Commands._COMMANDS[cmd] = time.time() + (cd_len*60)

    def _get_command(self, word):
        if not re.fullmatch(VALID_CMD, word): return NULL

        cmd = re.findall(CMD, word)[0]
        if (cmd not in self.Hakcbot.Commands._COMMANDS): return NULL

        args = re.findall(ARG, word)[0]
        for l in cmd:
            if (not l.isalnum()): return NULL

        if (args.startswith(',') or args.endswith(',')): return NULL
        args = args.split(',')
        L.l3(f'pre args filter | {args}')
        for arg in args:
            arg = arg.strip()
            title = self._get_title(arg)
            if (title): continue
            for l in arg:
                if (not l.isalnum() and l != '_'):
                    L.l3(f'{l} is not a valid command string.')
                    return NULL

        return cmd, tuple(a.strip() for a in args if a)
