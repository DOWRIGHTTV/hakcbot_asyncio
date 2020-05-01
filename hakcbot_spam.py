#!/usr/bin/python3

import re
import time
import traceback
import asyncio

from config import CHANNEL, BROADCASTER # pylint: disable=no-name-in-module
from hakcbot_regex import * # pylint: disable=unused-wildcard-import
from hakcbot_utilities import load_from_file, write_to_file, Log as L


class Spam:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot
        self.permit_list = {}
        self.aa_whitelist = {}

    # main spam logic, creating a wrapper/ logic around other functional methods
    async def pre_process(self, line):
        '''primary processing logic for spam module. will return a user namedtuple and a list
        containing all words in message.'''
        self._line = line

        error = self._format_line()
        if (error): return None

        block_message = self._message_filter()
        if (block_message):
            await self.Hakcbot.send_message(*block_message)
            return None

        L.l2(f'{self._user.name}: {self._message}')
        return self._user, [w.lower() for w in self._message.split()]

    # running messages through filter to detect links or banned words.
    def _message_filter(self):
        banned_word = self._blacklisted_word
        if (banned_word):
            message  = f'/timeout {self._user.name} {10} {banned_word}'
            response = f'{self._user.name}, you are a bad boi and used a blacklisted word.'

            L.l1(f'BLOCKED || {self._user} : {banned_word}') # want to see user tuple here
            return message, response

        url_match = re.findall(URL, self._message)
        if (not self._user.permit and url_match):
            matches = self._is_link(url_match)
            if (not matches): return None

            message  = f'/timeout {self._user.name} {10} {matches}'
            response = f'{self._user.name}, ask for permission to post links.'

            L.l1(f'BLOCKED || {self._user} : {matches}') # want to see user tuple here
            return message, response

    @property
    def _blacklisted_word(self):
        for word in self._message:
            if (word in self.Hakcbot.word_filter):
                return word

    # advanced checks for urls to limit programming language in chat from triggering url/link filter
    def _is_link(self, urlmatch):
        matches = []
        for match in urlmatch:
            match = match.strip('/')
            tld = match.split('.')[-1]
            if (match not in self.Hakcbot.url_whitelist
                    and tld in self.Hakcbot.domain_tlds):
                matches.append(match)

        return ', '.join(matches)

    def _check_broadcaster(self, usr):
        if (usr == BROADCASTER): return True

        return False

    def _format_line(self):
        self._user, self._message = None, None
        try:
            tags = re.findall(USER_TAGS, self._line)[0]
            msg  = re.findall(MESSAGE, self._line)[0].split(':', 2)
            username = msg[1].split('!')[0].lower()
            message  = msg[2].lower() # converting to lower to prevent issues with string matching
        except Exception as E:
            L.l0(f'Parse Error: {E}')
            return E

        timestamp = round(time.time())
        bcast = self._check_broadcaster(username)
        mod = bool(int(re.findall(MOD, tags)[0]))
        sub = bool(int(re.findall(SUB, tags)[0]))
        vip = bool(re.search(VIP, tags))

        # permitting the following roles to post links.
        permit = bool(bcast or mod or sub or vip)

        usr_permit = self.permit_list.get(username, None)
        if (not permit and usr_permit):
            # marking user to be permitted for a link head of time
            if (time.time() < usr_permit):
                permit = True
            # if expiration detected, will remove user from dict. temporary until better cleaning solution is implemented
            else:
                self.permit_list.pop(username)

        self._user = USER_TUPLE(username, bcast, mod, sub, vip, permit, timestamp)
        self._message = message
