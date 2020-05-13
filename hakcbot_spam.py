#!/usr/bin/python3

import re
import time
import traceback
import asyncio

from config import CHANNEL, BROADCASTER # pylint: disable=no-name-in-module
from hakcbot_regex import * # pylint: disable=unused-wildcard-import
from hakcbot_utilities import load_from_file, write_to_file, Log as L


class Spam:
    permit_list = {}

    _Hakcbot = None

    __slots__ = (
        '_line', '_user', '_message'
    )

    def __init__(self, data):
        self._data = data

    @classmethod
    def setup(cls, Hakcbot):
        cls._Hakcbot = Hakcbot

    # main spam logic, creating a wrapper/ logic around other functional methods
    async def pre_process(self):
        '''primary processing logic for spam module. will return a user namedtuple and a list
        containing all words in message.'''

        # if there is a return an exception was raise // returning
        user, message = self._format_data()
        if (not user):
            return None, None

        # calling admin hook for real time code modifications
        self._custom_filter_hook()

        block_message = self._message_filter()
        if (not block_message):
            L.l2(f'{self._user.name}: {self._message}')

            # updating some bot tracking vars if message passes spam filter
            self._Hakcbot.linecount += 1
            self._Hakcbot.last_message = fast_time()

            return self._user, self._message.split()

        await self.Hakcbot.send_message(*block_message)

    # hook for implemented custom, real time filters to prevent bots, spam, etc.
    def _custom_filter_hook(self):
        pass

    # running messages through filter to detect links or banned words.
    def _message_filter(self):
        blacklisted_words = self._blacklisted_word
        if (blacklisted_words):
            message  = f'/timeout {self._user.name} 10 {blacklisted_words}'
            response = f'{self._user.name}, you are a bad boi and used a blacklisted word.'

            L.l1(f'BLOCKED || {self._user} : {blacklisted_words}') # want to see user tuple here

            return message, response

        url_match = re.findall(URL, self._message)
        if (not self._user.permit and url_match):
            matches = self._is_link(url_match)
            if (not matches): return None

            message  = f'/timeout {self._user.name} 5 {matches}'
            response = f'{self._user.name}, ask for permission to post links. timeout is only 5 seconds.'

            L.l1(f'BLOCKED || {self._user} : {matches}') # want to see user tuple here

            return message, response

    @property
    def _blacklisted_word(self):
        return list(self.Hakcbot.word_filter.intersection(self._message))

    # advanced checks for urls to limit programming language in chat from triggering url/link filter
    def _is_link(self, urlmatch):
        matches = []
        for match in urlmatch:
            match = match.strip('/')
            tld = match.split('.')[-1]
            if (match not in self.Hakcbot.url_whitelist and tld in self.Hakcbot.domain_tlds):
                matches.append(match)

        return ', '.join(matches)

    def _format_line(self):
        try:
            tags = re.findall(USER_TAGS, self._data)[0]
            msg = re.findall(MESSAGE, self._data)[0].split(':', 2)

            # converting to lower to make it easier to string match
            username = msg[1].split('!')[0].lower()
            message = msg[2].lower()
        except Exception as E:
            L.l0(f'Parse Error: {msg} | {E}')
            return None, None

        timestamp = int(fast_time())
        bcast = username == BROADCASTER
        mod = bool(int(re.findall(MOD, tags)[0]))
        sub = bool(int(re.findall(SUB, tags)[0]))
        vip = bool(re.search(VIP, tags))

        # any special user role is auto permitted
        permit = any([bcast, mod, sub, vip])
        if (not permit):
            usr_permit = self.permit_list.pop(username, 0)

            # marking user to be permitted for a link head of time
            if (fast_time() < usr_permit):
                permit = True

        return USER_TUPLE(username, bcast, mod, sub, vip, permit, timestamp), message
