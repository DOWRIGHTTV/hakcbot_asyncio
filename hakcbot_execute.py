#!/usr/bin/python3


import re
import threading
import asyncio
import time
import requests
import json
import traceback

from config import * # pylint: disable=unused-wildcard-import
from hakcbot_regex import * # pylint: disable=unused-wildcard-import
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
        self._special_command = False # NOTE: this can be done better prob.
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

    def adjust_whitelist(self, url, action):
        current_whitelist = self.Hakcbot.url_whitelist
        if (action is AK.ADD):
            if (url in current_whitelist):
                return f'{url} already actively whitelisted.'

            current_whitelist.add(url)
            L.l1(f'added {url} to whitelist')

        elif (action is AK.DEL):
            try:
                current_whitelist.remove(url)
            except KeyError:
                return f'{url} does not have an active whitelist.'

            L.l1(f'removed {url} from whitelist')
        self.Hakcbot.Threads.add_file_task('url_whitelist')

    # NOTE: currently unused
    def adjust_blacklist(self, url=None, action=None):
        config = load_from_file('config.json')
        self.blacklist = set(config['blacklist'])

    def adjust_titles(self, name, title, tier, action):
        if (action is AK.DEL):
            user_data = self.Hakcbot.titles.pop(name, None)
            old_title = user_data['title']

            L.l1(f'removed title for {name}, the {title}.')

            message = f'{name} is no longer known as the {old_title}'

        else:
            if (action is AK.ADD):
                # default to one if not specified. did not want to make kwarg default 1 though
                # to not conflict with updates.
                if (not tier):
                    tier = 1

                self.Hakcbot.titles[name] = {
                    'tier': tier,
                    'title': title
                }
                L.l1(f'added title for {name}, the {title}.')

                message = f'{name} is now known as the {title}'

            elif (action is AK.MOD):
                old_title = self.Hakcbot.titles.get(name)
                # if tier is not defined, we will grab current user tier.
                if (not tier):
                    tier = self.Hakcbot.titles[name]['tier']

                if (not title or len(title) < 5):
                    title = self.Hakcbot.titles[name]['title']

                self.Hakcbot.titles[name] = {
                    'tier': tier,
                    'title': title
                }
                L.l1(f'updated tier {tier} title for {name}, the {title} formerly the {old_title}.')

                message = f'{name} (tier {tier}) is now known as the {title}, formerly the {old_title}'

        self.Hakcbot.Threads.add_file_task('titles')

        return message

    def _special_check(self, usr, msg):
        L.l4('special command parse started.')
        if (not usr.bcast and not usr.mod): return msg

        L.l4('bcaster or mod identified. checking for command match.')
        join_msg = ' '.join(msg)
        if not re.fullmatch(VALID_CMD, join_msg): return msg

        L.l4('valid command match. cross referencing special commands list.')
        cmd = re.findall(CMD, join_msg)[0]
        if cmd not in self.Hakcbot.Commands._SPECIAL: return msg

        L.l3(f'returning special command {join_msg}')

        self._special_command = True
        return [join_msg]

    def _get_title(self, arg):
        title = re.match(TITLE, arg)
        return title[0] if title else None

    def _apply_cooldown(self, cmd, cd_len):
        L.l1(f'Putting {cmd} on cooldown.')
        self.Hakcbot.Commands._COMMANDS[cmd] = fast_time() + cd_len

    def _get_command(self, word):
        if not re.fullmatch(VALID_CMD, word): return NULL

        cmd = re.findall(CMD, word)[0]
        if (cmd not in self.Hakcbot.Commands._COMMANDS): return NULL

        args = re.findall(ARG, word)[0]
        if (args.startswith(',') or args.endswith(',')): return NULL
        args = args.split(',')
        L.l3(f'pre args filter | {args}')
        for arg in args:
            arg = arg.strip()
            title = self._get_title(arg)
            if (title): continue
            for l in arg:
                # allow special commands to have urls. required for url whitelist.
                if ('.' in l and self._special_command): continue
                # ensuring users cannot abuse commands to bypass secuirty control. underscores are fine because they pose
                # no (known) threat and are commonly used in usernames.
                if (not l.isalnum() and l != '_'):
                    L.l3(f'"{l}" is not a valid command string.')
                    return NULL

        return cmd, tuple(a.strip() for a in args if a)
