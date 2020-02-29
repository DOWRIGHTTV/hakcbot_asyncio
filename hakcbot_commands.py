#!/usr/bin/env python3

import re
import json
import time
import asyncio
import requests

import hakcbot_regex as regex

from config import BROADCASTER
from hakcbot_utilities import CommandStructure as cs

THREE_MIN = 180


class Commands:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

# ====================
#   STANDARD COMMANDS
# ====================

    @cs.command('uptime', THREE_MIN)
    async def uptime(self):
        return self.Hakcbot.uptime_message

    @cs.command('time', THREE_MIN)
    async def time(self):
        ltime = time.strftime('%H:%M:%S', time.localtime())
        return f"{BROADCASTER}'s time is {ltime}"

# ========================
#   NON STANDARD COMMANDS
# ========================

    @cs.command('title', THREE_MIN)
    async def title(self, usr):
        title = self.Hakcbot.titles.get(usr, None)
        if (not title): return None

        return f'{usr}, {title}.'

    @cs.command('quote', THREE_MIN)
    async def quote(self, num):
        quote, year = self.Hakcbot.quotes.get(num, (None, None))
        if not quote: return None

        return f'{quote} - {BROADCASTER} {year}'

    @cs.command('yourmom', THREE_MIN)
    async def yourmom(self, usr):
        return f"{usr}'s mom goes to college."

    @cs.command('yourmum', THREE_MIN)
    async def yourmum(self, usr):
        return f"{usr}'s mum goes to college."

    @cs.command('praise', THREE_MIN)
    async def praise(self, usr):
        if (usr == 'thesun'):
            msg = '\\ [T] / (thesun)'
        else:
            msg = f'\\ [T] / ({usr})'

        return msg

# ===============
#   MOD COMMANDS
# ===============
    @cs.mod('permit')
    async def permit(self, usr):
        await self.Hakcbot.Spam.permit_link(usr, length=3)
        message  = f'/untimeout {usr}'
        response = f'{usr} can post links for 3 minutes.'
        return message, response

    @cs.mod('aa_wl')
    async def aa_wl(self, usr):
        await self.Hakcbot.Spam.add_to_aa_whitelist(usr)
        message  = f'/untimeout {usr}'
        response = f'adding {usr} to the account age whitelist.'
        return message, response

    @cs.mod('add_wl')
    async def add_wl(self, url):
        await self.Hakcbot.Spam.adjust_whitelist(url, action=True)
        message = f'adding {url} to the whitelist.'

        return message, None

    @cs.mod('del_wl')
    async def del_wl(self, url):
        await self.Hakcbot.Spam.adjust_whitelist(url, action=False)
        message = f'adding {url} to the whitelist.'

        return message, None
