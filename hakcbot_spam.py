#!/usr/bin/python3

import re
import time
import json
import threading
import asyncio

from config import CHANNEL

class Spam:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot
        self.tlds = set([])
        self.permitlist = set([])

        self.addwl = re.compile(r'addwl\((.*?)\)')
        self.delwl = re.compile(r'delwl\((.*?)\)')
#        self.whitelist = {'pastebin.com', 'twitch.tv', 'github.com', 'automatetheboringstuff.com'} # PEP 8 IS BULLSHIT......FAIL

        self.permituser = re.compile(r'permit\((.*?)\)')
        self.urlregex = re.compile(
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z]{2,}\.?)|' # Domain
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # IP Address
        r'(?::\d+)?' # Optional Port eg :8080
        r'(?:/?|[/?]\S+)', re.IGNORECASE) # Sepcific pages in url eg /homepage

        self.tagsreg = re.compile(r'@badge-info=(.*?)user-type=')
        self.msgreg = re.compile(r'user-type=(.*)')

#        self.WhitelistAdjust()

        self.whitelist = {}

    # Main method, creating a wrapper/ logic around other functional methods
    async def Main(self, line):
        self.line = line
        try:
            await self.FormatLine()
            await self.HakcbotModComms()
            spam = await self.urlFilter()
            return(spam)
        except Exception as E:
            print(E)

    # checkin message for url regex match, then checking whitelisted users and whitelisted urls,
    # if not whitelisted then checking urls for more specific url qualities like known TLDs
    # then timeing out user and notifying chat.
    async def urlFilter(self):
        message_block = False
        blacklist = False
        urlmatch = re.findall(self.urlregex, self.msg)
        for blacklist_word in self.blacklist:
            if blacklist_word in self.msg:
                message_block = True
                blacklist = True
                break
        if (urlmatch):
            if ('vip/1' in self.badges or self.subscriber == 'subscriber=1' \
            or self.user in self.permitlist):
                pass
            else:
                message_block, urlmatch = self.URLCheck(urlmatch)
        if (message_block):
            print(f'BLOCKED || {self.user} : {urlmatch}')
            if (blacklist):
                message = f'/timeout {self.user} {10} {blacklist_word}'
                response = f'{self.user}, you are a bad boi and used a blacklisted word.'
            else:
                message = f'/timeout {self.user} {10} {urlmatch}'
                response = f'{self.user}, ask for permission to post links.'
            await self.SendMessage(message, response)
            return True

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

    # method to permit users to post urls for 3 minutes, untimeing out just in case they
    # where arlready timed out, only allowing chat mods to do the command
    async def HakcbotModComms(self):
        if (self.user in self.Hakcbot.mod_list):
            if ('permit(' in self.msg):
                if ('!' in self.msg or '/' in self.msg or '.' in self.msg or ' ' in self.msg):
                    pass
                else:
                    user = re.findall(self.permituser, self.msg)[0]
                    threading.Thread(target=self.HakcbotPermitThread, args=(user,)).start()
                    message = f'/untimeout {self.user}'
                    response = f'{user} can post links for 3 minutes.'
                    await self.SendMessage(message, response)

            elif ('addwl(' in self.msg):
                action = True
                url = re.findall(self.addwl, self.msg)[0]
                self.WhitelistAdjust(url, action)
            elif('delwl(' in self.msg):
                action = False
                url = re.findall(self.delwl, self.msg)[0]
                self.WhitelistAdjust(url, action)

    # Thread to add user to whitelist set, then remove after 3 minutes.
    async def HakcbotPermitThread(self, user):
        self.permitlist.add(user.lower())
        await asyncio.sleep(60 * 3)
        self.permitlist.remove(user.lower())

    # More advanced checks for urls and ip addresses, to limit programming language in chat from
    # triggering url/link filter
    async def URLCheck(self, urlmatch):
        ## Checking all urls in urlmatch, if a match is found and it is not whitelisted or
        ## doesnt meet the other filter requirements then it will return True to mark the message
        ## to be blocked as well as the offending url. If no match, then will return False.
        numbers = {'-', '0', '1','2','3','4','5','6','7','8','9'}
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

    # Initializing TLD set to reference for advanced url match || 0(1), so not performance hit
    # to check 1200+ entries
    async def TLDSetCreate(self):
        with open('TLDs') as TLDs:
            for tld in TLDs:
                if len(tld) <= 6:
                    self.tlds.add(tld.strip('\n').lower())

    # Formatting/Parsing messages to be looked at for generally filter policies.
    async def FormatLine(self):
        try:
            tags = re.findall(self.tagsreg, self.line)[0]
            msg = re.findall(self.msgreg, self.line)[0]
            msg = msg.split(':', 2)
            tags = tags.split(';')
            user = msg[1].split('!')
            self.user = user[0]
            self.msg = msg[2]
            self.subscriber = tags[9]
            self.badges = tags[1]
        except Exception:
            raise Exception('Spam Format Line Error')

    # Method to send message, refering to socket which is initialized from outside the spam module
    async def SendMessage(self, message, response=None):
        loop = asyncio.get_running_loop()
        mT = f'PRIVMSG #{CHANNEL} :{message}'
        await loop.sock_sendall(self.Hakcbot.sock.send, f'{mT}\r\n'.encode("utf-8"))
        if (not response):
            pass
        else:
            rT = f'PRIVMSG #{CHANNEL} :{response}'
            await loop.sock_sendall(self.Hakcbot.sock.send, f'{rT}\r\n'.encode("utf-8"))
