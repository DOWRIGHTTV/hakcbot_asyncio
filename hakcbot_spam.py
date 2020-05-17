#!/usr/bin/python3

import re
import time
import traceback
import asyncio

from functools import cached_property

from config import CHANNEL, BROADCASTER # pylint: disable=no-name-in-module
from hakcbot_regex import * # pylint: disable=unused-wildcard-import
from hakcbot_utilities import load_tlds, load_from_file, write_to_file, Log as L


class Spam:
    permit_list = {}

    _url_whitelist = set()
    _word_filter   = set()
    _domain_tlds   = set()

    _Hakcbot = None

    __slots__ = (
        '_data', '_message'
    )

    def __init__(self, data):
        self._data = data

        self._message = None

    @classmethod
    def setup(cls, Hakcbot):
        cls._Hakcbot = Hakcbot

        cls._load_filters()

    # main spam logic, creating a wrapper/ logic around other functional methods
    async def pre_process(self):
        '''primary processing logic for spam module. will return a user namedtuple and a list
        containing all words in message.'''

        # if there is a return an exception was raise // returning
        user, self._message = self._format_data()
        if (not user):
            return None, None

        # calling admin hook for real time code modifications
        self._custom_filter_hook()

        block_message = self._message_filter(user)
        if (block_message):
            return None, block_message

        if (not block_message):
            L.l2(f'{user.name}: {self._message}')

            # NOTE: consider moving this back to main bot class.
            # updating some bot tracking vars if message passes spam filter
            self._Hakcbot.linecount += 1
            self._Hakcbot.last_message = fast_time()

            return user, self._message.split()

    # hook for implemented custom, real time filters to prevent bots, spam, etc.
    def _custom_filter_hook(self):
        pass

    # running messages through filter to detect links or banned words.
    def _message_filter(self, user):
        if (self._blacklisted_word):
            message  = f'/timeout {user.name} 10 {self._blacklisted_word}'
            response = f'{user.name}, you are a bad boi and used a blacklisted word.'

            L.l1(f'BLOCKED || {user} : {self._blacklisted_word}') # want to see user tuple here

            return message, response

        if (not user.permit and self._is_link):
            message  = f'/timeout {user.name} 1 {self._is_link}'
            response = f'{user.name}, ask for permission to post links.'

            L.l1(f'BLOCKED || {user} : {self._is_link}') # want to see user tuple here

            return message, response

    @cached_property
    def _blacklisted_word(self):
        return list(self._word_filter.intersection(self._message))

    @cached_property
    # advanced checks for urls to limit programming language in chat from triggering url/link filter
    def _is_link(self):
        url_match = re.findall(URL, self._message)
        if not url_match: return None

        matches = []
        for match in url_match:
            match = match.strip('/')
            tld = match.split('.')[-1]
            if (match not in self._url_whitelist and tld in self._domain_tlds):
                matches.append(match)

        return ', '.join(matches)

    def _format_data(self):
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

    @classmethod
    def _load_filters(cls):
        stored_data = load_from_file('config')

        cls._url_whitelist = set(stored_data['url_whitelist']) # easier to deal with a set
        cls._word_filter   = set(stored_data['word_filter'])
        cls._domain_tlds   = load_tlds()
