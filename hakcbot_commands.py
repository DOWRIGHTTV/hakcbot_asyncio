#!/usr/bin/env python3

import re
import json
import time
import asyncio
import requests

from hakcbot_regex import NULL, AK

from config import BROADCASTER
from hakcbot_utilities import CommandStructure as cs


class Commands(cs):

    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

# ====================
#   STANDARD COMMANDS
# ====================
    # TODO: make sure this filters out commands that arent available for standard users.
    @cs.cmd('commands', 3)
    def commands(self):
        commands = [f'{c}()' for c in self._COMMANDS]

        return ' | '.join(commands)

    @cs.cmd('sub', 3, auto=31)
    def sub(self):
        return 'Consider a sub to DOWRIGHT --> https://www.twitch.tv/subs/dowright'

    @cs.cmd('discord', 3, auto=42)
    def discord(self):
        return 'Join the Discord --> https://Discord.gg/KSCHNfa'

    @cs.cmd('youtube', 3)
    def youtube(self):
        return "DOWRIGHT's YouTube --> https://www.youtube.com/channel/UCKAiTcsiD50oZvf9h0xbvCg"

    @cs.cmd('github', 3)
    def github(self):
        return "DOWRIGHT's GitHub --> https://github.com/DOWRIGHTTV"

    @cs.cmd('parrot', 3)
    def parrot(self):
        return 'I prefer Parrot OS because it comes with all Airgeddon options, its preloaded with \
            OpenVAS setup scripts(Vuln Scan), and the general user experience is great. \
            https://www.parrotsec.org/'

    @cs.cmd('dnx', 3)
    def dnx(self):
        return 'DNX is a NextGen Firewall for the consumer and small business market. \
            Open source --> https://github.com/DOWRIGHTTV/DNX-FWALL-CMD'

    @cs.cmd('demo', 3)
    def demo(self):
        return 'Technical demo of DNX --> https://youtu.be/6NvRXlNjpOc'

    @cs.cmd('brave', 3)
    def brave(self):
        return 'i dont like mozilla (cuz DOH) and google is wack so i use brave. \
            creator code --> https://brave.com/dow336'

    @cs.cmd('doh', 3)
    def doh(self):
        return 'WATCH THIS. its about DNS over HTTPS. https://youtube.com/watch?v=8SJorQ9Ufm8'

    @cs.cmd('ide', 3)
    def ide(self):
        return 'vscodium with monokai theme --> https://vscodium.com/'

    @cs.cmd('uptime', 3)
    def uptime(self):
        return self.Hakcbot.uptime_message

    @cs.cmd('time', 3)
    def time(self):
        ltime = time.strftime('%H:%M:%S', time.localtime())
        return f"{BROADCASTER}'s time is {ltime}"

# ========================
#   NON STANDARD COMMANDS
# ========================

    @cs.cmd('title', 3)
    def title(self, usr):
        title = self.Hakcbot.titles.get(usr, None)
        if (not title): return None

        return f'{usr}, {title}.'

    @cs.cmd('quote', 3)
    def quote(self, num):
        quote, year = self.Hakcbot.quotes.get(num, NULL)
        if not quote: return None

        return f'{quote} - {BROADCASTER} {year}'

    @cs.cmd('yourmom', 3)
    def yourmom(self, usr):
        return f"{usr}'s mom goes to college."

    @cs.cmd('yourmum', 3)
    def yourmum(self, usr):
        return f"{usr}'s mum goes to college."

    @cs.cmd('praise', 3)
    def praise(self, usr):
        if (usr == 'thesun'):
            msg = '\\ [T] / (thesun)'
        else:
            msg = f'\\ [T] / ({usr})'

        return msg

# ===============
#   MOD COMMANDS
# ===============

    @cs.mod('permit')
    def permit(self, usr):
        self.Hakcbot.Spam.permit_list[usr.lower()] = time.time() + (3 * 60)
        message  = f'/untimeout {usr}'
        response = f'{usr}, you can now post links for 3 minutes.'
        return message, response

    @cs.mod('acctwl')
    def acctwl(self, usr):
        self.Hakcbot.AccountAge.whitelist.add(usr.lower())
        message  = f'/untimeout {usr}'
        response = f'{usr}, your account age block has been lifted. chat away!'
        return message, response

    @cs.mod('urlwl')
    def urlwl(self, url, action):
        if (not action.isdigit()): return NULL

        action = AK(int(action))
        self.Hakcbot.Execute.adjust_whitelist(url, action=action)
        if (action is AK.ADD):
            message = f'{url} added to the url whitelist.'
        elif (action is AK.DEL):
            message = f'{url} removed from the url whitelist.'

        return message, None

# =======================
#   BROADCASTER COMMANDS
# =======================

    @cs.brc('modifytitle', spc=True)
    def modifytitle(self, name, title, action='1'):
        '''will create a title in memory for the sent in user. addtitle(viewer, 'best viewer n/a')'''
        if (not action.isdigit() or int(action) not in [0,1,2]): return NULL
        if (not title and action != '2'): return 'title required for this action.', None

        action = AK(int(action))
        ALREADY_EXISTS = self.Hakcbot.titles.get(name, None)
        if (action is AK.MOD):
            if (not ALREADY_EXISTS): return f'{name} has no title to modify.', None
            message = f'{name} has be given the new title of the {title}'

        elif (action is AK.DEL):
            if (not ALREADY_EXISTS): return f'{name} has no title to remove.', None
            message = f'{name} is no longer known as the {title}'

        elif (ALREADY_EXISTS):
            message = f'{name} is already know as the {ALREADY_EXISTS}. modify action required.'

        elif (action is AK.ADD):
            message = f'{name} is now known as the {title}'

        self.Hakcbot.Execute.adjust_titles(
            name, title.strip('"').strip("'"), action=action)

        return message, None
