#!/usr/bin/python3

import re
import time
import json
import requests
import traceback
import asyncio

from ipaddress import IPv4Address
from collections import namedtuple

# pylint: disable=no-name-in-module, unused-wildcard-import
from config import CHANNEL
from hakcbot_regex import *
from hakcbot_utilities import load_from_file, write_to_file

BROADCASTER = 'dowright'


class Spam:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot
        self.domain_tlds = set()
        self.permit_list = {}
        self.url_whitelist = {}

        self.user_tuple = namedtuple('user', 'name mod sub vip permit')

    # Main method, creating a wrapper/ logic around other functional methods
    async def main(self, line):
        try:
            user, message = await self.format_line(line)
            await self.get_mod_command(user, message)

            # function will check if already in progress before sending to the queue
            await self.Hakcbot.AccountAge.add_to_queue(user)

            blocked_message = await self.url_filter(user, message)

            return blocked_message, user, message
        except Exception:
            traceback.print_exc()

    # checkin message for url regex match, then checking whitelisted users and whitelisted urls,
    # if not whitelisted then checking urls for more specific url qualities like known TLDs
    # then timeing out user and notifying chat.
    async def url_filter(self, user, message):
        block_link = False
        url_match = re.findall(URL, message)
        blacklisted_word = await self.check_blacklist(message)
        if (not blacklisted_word and url_match and not user.permit):
            block_link, blocked_url = await self.check_for_link(url_match)

#        print(f'URL: {url_match} | BLOCK?: {block_url} | USER: {user}')
        if (blacklisted_word):
            message = f'/timeout {user.name} {10} {blacklisted_word}'
            response = f'{user.name}, you are a bad boi and used a blacklisted word.'

            print(f'BLOCKED || {user} : {blacklisted_word}') # want to see user tuple here
        elif (block_link):
            message = f'/timeout {user.name} {10} {blocked_url}'
            response = f'{user.name}, ask for permission to post links.'

            print(f'BLOCKED || {user} : {blocked_url}') # want to see user tuple here

        if (blacklisted_word or block_link):
            await self.Hakcbot.send_message(message, response)

            return True

    # maybe flip this around or use regex to improve performance on large blacklists
    async def check_blacklist(self, message):
        for blacklisted_word in self.blacklist:
            if (blacklisted_word in message):
                return blacklisted_word

        return None

    # method to permit users to post urls for 3 minutes, untimeing out just in case they
    # where arlready timed out, only allowing chat mods to do the command
    async def get_mod_command(self, user, message):
        if (not user.mod and user.name != BROADCASTER):
            return
        valid_message = await self.validate_command(message)
        if (not valid_message):
            return

        if ('permit(' in message):
            username = re.findall(PERMIT_USER, message)[0]
            await self.permit_link(username.lower(), length=3)

            message = f'/untimeout {username}'
            response = f'{username} can post links for 3 minutes.'

        elif ('addwl(' in message):
            action = True
            url = re.findall(ADD_WL, message)[0]
            message = f'adding {url} to the whitelist.'
            await self.adjust_whitelist(url, action)

        elif('delwl(' in message):
            action = False
            url = re.findall(DEL_WL, message)[0]
            message = f'removing {url} from the whitelist.'
            await self.adjust_whitelist(url, action)
        else:
            return

        await self.Hakcbot.send_message(message, response)

    # add user to whitelist set
    async def permit_link(self, username, length=3):
        self.permit_list[username] = time.time() + (length * 60)
        print(f'ADDED permit user: {username} | length: {length}')

    # More advanced checks for urls and ip addresses, to limit programming language in chat from
    # triggering url/link filter
    async def check_for_link(self, urlmatch):
        for match in urlmatch:
            match = match.strip('/')
            tld = match.split('.')[-1]
            if (match not in self.url_whitelist and tld in self.domain_tlds):
                match = ', '.join(urlmatch)
                return True, match

        return False, None

    ## Method to adjust URL whitelist on mod command, will call itself if list is updated
    ## to update running set white bot is running
    async def adjust_whitelist(self, url=None, action=None):
        config = load_from_file('config.json')

        self.url_whitelist = config['whitelist']
        if (not url or not action):
            return

        if (action is True):
            self.url_whitelist.update({url: '1'})
            print(f'hakcbot: added {url} to whitelist')

        elif action is False:
            self.url_whitelist.pop(url, None)
            print(f'hakcbot: removed {url} from whitelist')

        write_to_file(config, 'config.json')
        await self.adjust_whitelist()

    async def adjust_blacklist(self, url=None, action=None):
        config = load_from_file('config.json')
        self.blacklist = config['blacklist']

    # Formatting/Parsing messages to be looked at for generally filter policies.
    async def format_line(self, line):
        mod, sub, vip, permit = False, False, False, False
        try:
            tags = re.findall(USER_TAGS, line)[0]
            msg = re.findall(MESSAGE, line)[0]
            msg = msg.split(':', 2)
            tags = tags.split(';')
            user = msg[1].split('!')

            username = user[0]
            message = msg[2]
            subscriber = tags[9]
            moderator = int(tags[7].split('=')[1])
            badges = tags[1]
        except Exception:
            raise Exception('Spam Format Line Error')

        if (moderator):
            mod = True
        if (subscriber == 'subscriber=1'):
            sub = True
        if ('vip/1' in badges):
            vip = True

        # permitting the following roles to post links.
        if (mod or vip or sub):
            permit = True
        else:
            permit_link_expire = self.permit_list.get(username, None)
            if (permit_link_expire):
                # marking user to be permitted for a link head of time
                if (time.time() < permit_link_expire):
                    permit = True
                # if expiration detected, will remove user from dict. temporary until better cleaning solution is implemented
                else:
                    self.permit_list.pop(username)

        user = self.user_tuple(username, mod, sub, vip, permit)

        return user, message

    # Initializing TLD set to reference for advanced url match || 0(1), so not performance hit
    # to check 1200+ entries
    async def create_tld_set(self):
        with open('TLDs') as TLDs:
            for tld in TLDs:
                if (len(tld) <= 6 and not tld.startswith('#')):
                    self.domain_tlds.add(tld.strip('\n').lower())

    async def validate_command(self, message):
        if ('!' in message or '/' in message or '.' in message or ' ' in message):
            return False
        else:
            return True
