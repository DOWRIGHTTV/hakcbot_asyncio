#!/usr/bin/env pythonTHREE_MIN

import re
import json
import asyncio
import requests

from time import strftime, localtime

from config import BROADCASTER
from hakcbot_regex import fast_time, NULL, AK, ONE_MIN, THREE_MIN
from hakcbot_spam import Spam
from hakcbot_accountage import AccountAge
from hakcbot_execute import * # pylint: disable=unused-wildcard-import
from hakcbot_utilities import Log as L, CommandStructure as cs


class Commands(cs):

    tricho_count = []

    def __init__(self, Hakcbot):
        self._Hakcbot = Hakcbot

# ====================
#   STANDARD COMMANDS
# ====================
    # TODO: make sure this filters out commands that arent available for standard users.
    @cs.cmd('commands', THREE_MIN)
    def commands(self):
        commands = [f'{c}()' for c, public in self.COMMANDS.items() if public]

        return ' | '.join(commands)

    @cs.cmd('sub', THREE_MIN, auto=31)
    def sub(self):
        return 'Consider a sub to DOWRIGHT --> https://www.twitch.tv/subs/dowright'

    @cs.cmd('discord', THREE_MIN, auto=42)
    def discord(self):
        return 'Join the Discord --> https://Discord.gg/KSCHNfa'

    @cs.cmd('youtube', THREE_MIN)
    def youtube(self):
        return "DOWRIGHT's YouTube --> https://www.youtube.com/channel/UCKAiTcsiD50oZvf9h0xbvCg"

    @cs.cmd('playlist', THREE_MIN)
    def playlist(self):
        return "DOWRIGHT's YouTube --> https://www.youtube.com/playlist?list=PLwZJPKdsVZZW9l2EJlGZb7jFQwuPj4XHo"

    @cs.cmd('github', THREE_MIN)
    def github(self):
        return "DOWRIGHT's GitHub --> https://github.com/DOWRIGHTTV"

    @cs.cmd('parrot', THREE_MIN)
    def parrot(self):
        return 'I prefer Parrot OS because it comes with all Airgeddon options, its preloaded with \
            OpenVAS setup scripts(Vuln Scan), and the general user experience is great. \
            https://www.parrotsec.org/'

    @cs.cmd('dnx', THREE_MIN)
    def dnx(self):
        return 'DNX is a NextGen Firewall for the consumer and small business market. \
            Open source --> https://github.com/DOWRIGHTTV/dnxfirewall'

    @cs.cmd('demo', THREE_MIN)
    def demo(self):
        return 'Technical demo of dnxfirewall (VERY OLD) --> https://youtu.be/6NvRXlNjpOc'

    @cs.cmd('brave', THREE_MIN)
    def brave(self):
        return 'i dont like mozilla (cuz DOH) and google is wack so i use brave. \
            creator code --> https://brave.com/dow336'

    @cs.cmd('doh', THREE_MIN)
    def doh(self):
        return 'WATCH THIS. its about DNS over HTTPS. https://youtube.com/watch?v=8SJorQ9Ufm8'

    @cs.cmd('ide', THREE_MIN)
    def ide(self):
        return 'vscodium with monokai theme --> https://vscodium.com/'

    @cs.cmd('uptime', THREE_MIN)
    def uptime(self):
        return self._Hakcbot.uptime_message

    @cs.cmd('time', THREE_MIN)
    def time(self):
        ltime = strftime('%H:%M:%S', localtime())

        return f"{BROADCASTER}'s time is {ltime}"

    @cs.cmd('hw', THREE_MIN)
    def hw(self):
        return 'The current target hardware is Espressobin: --> http://espressobin.net'

    @cs.cmd('laptop', THREE_MIN)
    def laptop(self):
        return 'i use this laptop --> dell e7250 12.5in, i5-5300U 2.3ghz, 8g ram, 256 ssd'

    @cs.cmd('iobound', THREE_MIN)
    def iobound(self):
        diatribe = ("First, Python is not slow.  Python is faster than the I/O "
                    "we're waiting for.  C and all other languages must wait "
                    "just as long as Python for packets to arrive.  Packet "
                    "inspection and filtering is an I/O bound task.")

        return diatribe




# ========================
#   NON STANDARD COMMANDS
# ========================

    @cs.cmd('tricho', ONE_MIN)
    def tricho(self, count=None):
        if (not count):
            return f'trichotillomania stream count: {len(self.tricho_count)}'

        self.tricho_count.append(1)
        return f'trichotillomania incremented, current: {len(self.tricho_count)}'

    # TODO: make "self" argument return title of user that called
    @cs.cmd('title', ONE_MIN)
    def title(self, usr=None):
        if (not usr):
            return 'T1 - call title("user") to query the user title. T2 - when user first speaks in chat \
                their title will be announced in chat. T3 - when user joins chat, their title will be \
                announced in chat. Title will be selected by me and can be purchased with hacker points. \
                T2/T3 is not currently active.'

        try:
            title = self._Hakcbot.titles[usr]['title']
        except KeyError:
            return f'{usr} is not named in the hakcerdom.'

        return f'{usr}, the {title}.'

    @cs.cmd('quote', THREE_MIN)
    def quote(self, num):
        quote, year = self._Hakcbot.quotes.get(num, NULL)
        if not quote: return None

        return f'{quote} - {BROADCASTER} {year}'

    @cs.cmd('yourmom', THREE_MIN)
    def yourmom(self, usr):
        return f"{usr}'s mom goes to college."

    @cs.cmd('yourmum', THREE_MIN)
    def yourmum(self, usr):
        return f"{usr}'s mum goes to college."

    @cs.cmd('praise', THREE_MIN)
    def praise(self, usr):
        if (usr == 'thesun'):
            msg = '\\ [T] / (thesun)'
        else:
            msg = f'\\ [T] / ({usr})'

        return msg

    @cs.cmd('congrats', THREE_MIN)
    def congrats(self, usr):
        return f"Yo {usr}! Welcome to the team. Grab a beer and take a seat."

# ===============
#   MOD COMMANDS
# ===============
    # NOTE: these are now broken!
    @cs.mod('permit')
    def permit(self, usr):
        Spam.permit_list[usr] = fast_time() + THREE_MIN
        message  = f'/untimeout {usr}'
        response = f'{usr}, you can now post 1 link.'

        return message, response

    @cs.mod('acctwl')
    def acctwl(self, usr):
        AccountAge.whitelist.add(usr)
        message  = f'/untimeout {usr}'
        response = f'{usr}, your account age block has been lifted. chat away!'

        return message, response

    @cs.mod('urlwl', spc=True)
    def urlwl(self, url, action=1):
        try:
            action = AK(int(action))
        except:
            message = f'action={action} is not a valid argument.'
        else:
            url = url.lower()
            error = adjust_whitelist(self, url, action=action)
            if (error):
                message = error

            elif (action is AK.ADD):
                message = f'{url} added to the url whitelist.'

            elif (action is AK.DEL):
                message = f'{url} removed from the url whitelist.'

        return message, None

# =======================
#   BROADCASTER COMMANDS
# =======================

    @cs.brc('loglevel')
    def loglevel(self, lvl=None):
        if (not lvl):
            return f'current log level:{L.LEVEL}', None

        vl = L.valid_levels
        if (lvl in vl):
            L.LEVEL = int(lvl)

        else:
            return f'Log level must be a digit between {vl[0]}-{vl[-1]}.', None

        return f'Log level changed to {lvl}.', None

    @cs.brc('modifytitle', spc=True)
    def modifytitle(self, name, title, tier, action='1'):
        '''will create a title in memory for the sent in user. modifytitle(viewer, 'best viewer n/a', tier, action)'''
        if (not action.isdigit() or int(action) not in [0,1,2]): return NULL
        if (not tier.isdigit() or int(action) not in [0,1,2]): return NULL
        if (not title and action != '0'): return 'title required for this action.', None

        action, tier, title = AK(int(action)), int(tier), title.strip('"').strip("'")
        ALREADY_EXISTS = self._Hakcbot.titles.get(name, None)

        if (action is AK.ADD):
            if (ALREADY_EXISTS):
                return f'{name} is already known as the {ALREADY_EXISTS}. modify action required.', None

            elif (not title):
                return 'title is required for add call.', None

        elif (not ALREADY_EXISTS):
            if (action is AK.MOD):
                return f'{name} has no title to modify.', None

            if (action is AK.DEL):
                return f'{name} has no title to remove.', None

        message = adjust_titles(
            self, name, title, tier, action
        )

        return message, None
