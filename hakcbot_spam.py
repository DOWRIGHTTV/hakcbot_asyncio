#!/usr/bin/python3

import re
import time
import traceback
import asyncio

from collections import namedtuple

# pylint: disable=no-name-in-module, unused-wildcard-import
from config import CHANNEL, BROADCASTER
from hakcbot_regex import *
from hakcbot_utilities import load_from_file, write_to_file

USER_TUPLE = namedtuple('user', 'name mod sub vip permit timestamp')


class Spam:
    def __init__(self, Hakcbot):
        self.Hakcbot       = Hakcbot
        self.permit_list   = {}
        self.url_whitelist = {}
        self.aa_whitelist  = set()
        self.domain_tlds   = set()

    # Main method, creating a wrapper/ logic around other functional methods
    async def main(self, line):
        processed_data = await self.format_line(line)
        # if error bot will process next message and print error to prevent bot from crashing.
        if (not processed_data):
            return None

        user, message = processed_data
        if not await self._is_valid_message(user, message):
            return None

        print(f'{user.name}: {message}')
        return user, [w.lower() for w in message.split()]

    # running messages through filter to detect links or banned words. NOTE: this can probably
    # be refactored much better!
    async def _is_valid_message(self, user, message):
        url_match = re.findall(URL, message)
        banned_word = await self._blacklisted_word(message)
        if (banned_word):
            message  = f'/timeout {user.name} {10} {banned_word}'
            response = f'{user.name}, you are a bad boi and used a blacklisted word.'

            print(f'BLOCKED || {user} : {banned_word}') # want to see user tuple here
        elif (user.permit):
            return True
        elif (url_match):
            matches = await self._is_link(url_match)
            if (not matches): return True

            message  = f'/timeout {user.name} {10} {matches}'
            response = f'{user.name}, ask for permission to post links.'

            print(f'BLOCKED || {user} : {matches}') # want to see user tuple here
        else:
            return True

        await self.Hakcbot.send_message(message, response)

    async def _blacklisted_word(self, message):
        for word in message:
            if (word in self.blacklist):
                return word

        return None

    # add user to whitelist set
    async def permit_link(self, username, length=3):
        self.permit_list[username.lower()] = time.time() + (length * 60)
        print(f'ADDED permit for user: {username} | length: {length}')

    async def add_to_aa_whitelist(self, username):
        self.aa_whitelist.add(username.lower())
        print(f'ADDED AA WL for user: {username}')

    # More advanced checks for urls and ip addresses, to limit programming language in chat from
    # triggering url/link filter
    async def _is_link(self, urlmatch):
        matches = []
        for match in urlmatch:
            match = match.strip('/')
            tld = match.split('.')[-1]
            if (match not in self.url_whitelist and tld in self.domain_tlds):
                matches.append(match)

        return ', '.join(matches)

    ## adjust URL whitelist on mod command, will call itself if list is updated
    ## to update running set white bot is running
    async def adjust_whitelist(self, url=None, action=None):
        config = load_from_file('config.json')
        self.url_whitelist = config['whitelist']
        if (not url or not action):
            return

        if (action is True):
            self.url_whitelist.append(url.lower())
            print(f'hakcbot: added {url} to whitelist')

        elif (action is False):
            self.url_whitelist.pop(url.lower(), None)
            print(f'hakcbot: removed {url} from whitelist')

        await asyncio.get_running_loop().run_in_executor(None,
            write_to_file, config, 'config.json')
        await self.adjust_whitelist()

    async def adjust_blacklist(self, url=None, action=None):
        config = load_from_file('config.json')
        self.blacklist = set(config['blacklist'])

    # Formatting/Parsing messages to be looked at for generally filter policies.
    async def format_line(self, line):
        try:
            tags = re.findall(USER_TAGS, line)[0]
            msg  = re.findall(MESSAGE, line)[0].split(':', 2)
            username = msg[1].split('!')[0]
            message  = msg[2]
        except Exception as E:
            print(f'Parse Error: {E}')
            return None

        timestamp = round(time.time())
        vip = bool(re.search(VIP, tags))
        sub = bool(int(re.findall(SUB, tags)[0]))
        mod = bool(int(re.findall(MOD, tags)[0]))
        # permitting the following roles to post links.
        permit = bool(sub or vip or mod)

        usr_permit = self.permit_list.get(username, None)
        if (not permit and usr_permit):
            # marking user to be permitted for a link head of time
            if (time.time() < usr_permit):
                permit = True
            # if expiration detected, will remove user from dict. temporary until better cleaning solution is implemented
            else:
                self.permit_list.pop(username)

        return USER_TUPLE(username, sub, vip, mod, permit, timestamp), message

    # Initializing TLD set to reference for advanced url match || 0(1), so not performance hit
    # to check 1200+ entries
    async def create_tld_set(self):
        with open('TLDs') as TLDs:
            for tld in TLDs:
                if (len(tld) <= 6 and not tld.startswith('#')):
                    self.domain_tlds.add(tld.strip('\n').lower())
