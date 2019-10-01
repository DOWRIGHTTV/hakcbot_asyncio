#!/usr/bin/python3

import re
import time
import json
import requests
import traceback
import asyncio

from config import CHANNEL
from regex import *
from collections import namedtuple


class Spam:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot
        self.tlds = set()
        self.permit_list = {}
        self.whitelist = {}

        self.account_age_check_inprogress = set()
        self.account_age_whitelist = set()

        self.user_tuple = namedtuple('user', 'name mod sub vip permit')

    # Main method, creating a wrapper/ logic around other functional methods
    async def Main(self, line):
        try:
            user, message = await self.FormatLine(line)
            await self.HakcbotModComms(user, message)

#            print(f'AA WL: {self.account_age_whitelist}')
            if (user not in self.account_age_whitelist
                    and user not in self.account_age_check_inprogress):
                self.account_age_check_inprogress.add(user)
                await self.AddtoAccountAgeQueue(user)

            spam = await self.URLFilter(user, message)

            return(spam)
        except Exception:
            traceback.print_exc()

    async def AddtoAccountAgeQueue(self, user):
        self.Hakcbot.Threads.account_age_queue.append(user)

    # checkin message for url regex match, then checking whitelisted users and whitelisted urls,
    # if not whitelisted then checking urls for more specific url qualities like known TLDs
    # then timeing out user and notifying chat.
    async def URLFilter(self, user, message):
        block_url = False
        url_match = re.findall(URL, message)
        blacklisted_word = await self.CheckBlacklist(message)
        print(user)
        if (not blacklisted_word and url_match and not user.mod
                and not user.sub and not user.permit):
            block_url, url_match = await self.URLCheck(url_match)

        print(f'URL: {url_match} | BLOCK?: {block_url} | USER: {user}')
        if (blacklisted_word):
            message = f'/timeout {user.name} {10} {blacklisted_word}'
            response = f'{user.name}, you are a bad boi and used a blacklisted word.'

            print(f'BLOCKED || {user} : {blacklisted_word}') # want to see user tuple here
        elif (block_url):
            message = f'/timeout {user.name} {10} {url_match}'
            response = f'{user.name}, ask for permission to post links.'

            print(f'BLOCKED || {user} : {url_match}') # want to see user tuple here

        if (blacklisted_word or block_url):
            await self.Hakcbot.SendMessage(message, response)

            return True

    async def CheckBlacklist(self, message):
        for blacklisted_word in self.blacklist:
            if blacklisted_word in message:
                return blacklisted_word

        return None

    # method to permit users to post urls for 3 minutes, untimeing out just in case they
    # where arlready timed out, only allowing chat mods to do the command
    async def HakcbotModComms(self, user, message):
        if (user.mod):
            if ('permit(' in message):
                valid_message = await self.ValidateCommand(message)
                if (valid_message):
                    username = re.findall(PERMIT_USER, message)[0]
                    await self.HakcbotPermitThread(username, length=3)

                    message = f'/untimeout {username}'
                    response = f'{username} can post links for 3 minutes.'

                    await self.Hakcbot.SendMessage(message, response)

            elif ('addwl(' in message):
                action = True
                url = re.findall(ADD_WL, message)[0]

                await self.WhitelistAdjust(url, action)
            elif('delwl(' in message):
                action = False
                url = re.findall(DEL_WL, message)[0]

                await self.WhitelistAdjust(url, action)

    # Thread to add user to whitelist set, then remove after 3 minutes.
    async def HakcbotPermitThread(self, username, length=3):
        permit_duration = length * 60
        self.permit_list[username] = time.time() + permit_duration
        print(f'ADDED permit user: {username} | length: {length}')

    # More advanced checks for urls and ip addresses, to limit programming language in chat from
    # triggering url/link filter
    async def URLCheck(self, urlmatch):
        ## Checking all urls in urlmatch, if a match is found and it is not whitelisted or
        ## doesnt meet the other filter requirements then it will return True to mark the message
        ## to be blocked as well as the offending url. If no match, then will return False.
        numbers = ['-', '0', '1','2','3','4','5','6','7','8','9']
        for match in urlmatch:
            tld = match.split('.')[-1].strip('/')
            if (match not in self.whitelist):
                for number in numbers:
                    if number in match:
                        return True, match
                if tld in self.tlds:
                    return True, match
        else:
            return False, None

    ## Method to adjust URL whitelist on mod command, will call itself if list is updated
    ## to update running set white bot is running
    async def WhitelistAdjust(self, url=None, action=None):
        write = False
        with open('whitelist.json', 'r') as whitelists:
            whitelist = json.load(whitelists)

        self.whitelist = whitelist['Whitelist']['URLS']
        if (action is True):
            self.whitelist.update({url: '1'})
            print(f'hakcbot: added {url} to whitelist')
            write = True
        elif action is False:
            self.whitelist.pop(url, None)
            print(f'hakcbot: removed {url} from whitelist')
            write = True

        if (write):
            with open('whitelist.json', 'w') as whitelists:
                json.dump(whitelist, whitelists, indent=4)
            await self.WhitelistAdjust()

    async def BlacklistAdjust(self, url=None, action=None):
        with open('blacklist.json', 'r') as blacklists:
            blacklist = json.load(blacklists)
        self.blacklist = blacklist['Blacklist']['Words']

    # Formatting/Parsing messages to be looked at for generally filter policies.
    async def FormatLine(self, line):
        mod = False
        sub = False
        vip = False
        permit = False
        try:
            tags = re.findall(USER_TAGS, line)[0]
            msg = re.findall(MESSAGE, line)[0]
            msg = msg.split(':', 2)
            tags = tags.split(';')
            user = msg[1].split('!')

            message = msg[2]

            username = user[0]
            subscriber = tags[9]
            badges = tags[1]

            if (username in self.Hakcbot.mod_list):
                mod = True
            if (subscriber == 'subscriber=1'):
                sub = True
            if ('vip/1' in badges):
                vip = True

            now = time.time()
            permit = self.permit_list.get(username, None)
            if (permit):
                # marking user to be permitted for a link head of time
                if (permit > now):
                    permit = True
                # if expiration detected, will remove user from dict. temporary until better cleaning solution is implemented
                else:
                    self.permit_list.pop(username)

            user = self.user_tuple(username, mod, sub, vip, permit)

            return user, message
        except Exception:
            raise Exception('Spam Format Line Error')

    # Initializing TLD set to reference for advanced url match || 0(1), so not performance hit
    # to check 1200+ entries
    async def TLDSetCreate(self):
        with open('TLDs') as TLDs:
            for tld in TLDs:
                if len(tld) <= 6:
                    self.tlds.add(tld.strip('\n').lower())

    async def ValidateCommand(self, message):
        if ('!' in message or '/' in message or '.' in message or ' ' in message):
            return False
        else:
            return True
