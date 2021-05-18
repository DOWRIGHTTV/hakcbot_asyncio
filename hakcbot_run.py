#!/usr/bin/python3

import threading
import uvloop, asyncio
import requests
import time
import traceback

from random import randint
from socket import socket

from config import * # pylint: disable=unused-wildcard-import
from hakcbot_init import Initialize
from hakcbot_spam import Spam
from hakcbot_commands import Commands
from hakcbot_accountage import AccountAge

from hakcbot_regex import fast_time, USER_TUPLE, ONE_MIN, FIVE_MIN, ANNOUNCEMENT_INTERVAL
from hakcbot_utilities import dynamic_looper, queue
from hakcbot_utilities import load_from_file, write_to_file, Log as L


# TODO: make account age checks persistent/ stored in a json file or sqlite db
# TODO: consider converting the broadcaster stored items in a sqlite DB eg quotes, titles, etc
# TODO: make a persistent log of accounts that are bots, this could just be a called function after
    # and AA timeout or user hook code catches a bot.


class Hakcbot:
    online = False
    linecount = 0
    last_message = 0
    uptime_message = 'hakcbot is still initializing! try again in a bit.'

    quotes = {}
    titles = {}
    announced_titles = {}
    _sock = socket()

    @classmethod
    def start(cls):
        cls._load_json_data()
        cls.Commands = Commands(cls)

        # applying callback reference to access main bot objects
        Initialize.setup(cls)
        Spam.setup(cls)

        Threads.start(cls)
        AccountAge.start(cls, Threads)

        uvloop.install()

        self = cls()
        asyncio.run(self.main())

    async def main(self):
        await Initialize.start()

        self._task_handler = self.Commands.task_handler
        self._titles_get = self.titles.get
        self._announced_titles_get = self.announced_titles.get

        await asyncio.gather(self.hakc_general(), Automate.start())

    async def hakc_general(self):
        L.l1('[+] Starting main bot process.')
        sock, asock_recv = self._sock, asyncio.get_running_loop().sock_recv
        while True:
            try:
                data = await asock_recv(sock, 1024)
            except OSError as E:
                L.l3(f'MAIN SOCKET ERROR | {E}')
                break
            else:
                if (not data):
                    L.l3('SOCKET CLOSED BY REMOTE SERVER')
                    break

                await self._message_handler(data.decode('utf-8', 'ignore').strip())

        # closing socket | TODO: figure out how we can reconnect properly
        self._sock.close()

    # TODO: break this out into multiple functions. its starting to get out of hand.
    async def _message_handler(self, data):
        # NOTE: probably dont need user definition
        user = None
        if (data == 'PING :tmi.twitch.tv'):
            await self.send_message(pong=True)

        elif ('PRIVMSG' in data):
            spam_filter = Spam(data)
            user, message = await spam_filter.pre_process()

            if (not user and not message): return

            elif (not user):
                await self.send_message(message)

            # TODO: temporary until better location is found.
            elif any([word.startswith('!') and len(word) > 2 for word in message]):
                await self.send_message(['invalid command syntax. try: command() instead of !command.'])

            else:
                # function will check if already in progress before sending to the queue
                AccountAge.add_to_queue(user)

                response = self._task_handler(user, message)
                if (response):
                    await self.send_message(response)

                await self._handle_titles(user.name)
                self._update_trackers()

        # placeholder for when i want to track joins/ see if a user joins
        elif ('JOIN' in data):
            L.l3(data)

        # probably a bunk ass message, not sure????? should protect higher tier titles for now.
        else:
            L.l3(f'else: {data}')
            return

    # T2 TITLES
    async def _handle_titles(self, username):
        titled_user = self._titles_get(username)
        if (not titled_user): return

        prior_announcement = self._announced_titles_get(username, None)
        if (not prior_announcement) or (titled_user['tier'] == 2 and not self.recently_announced(prior_announcement)):

            # already announced users - type > dict()
            self.announced_titles[username] = fast_time()

            # announcing the user to chat
            if (self.online):
                await self.announce_title(username, titled_user['title'])

    async def announce_title(self, user, title):
        # message needs to be iterable for compatibility with commands.
        message = [f'attention! {user}, the {title}, has spoken.']

        await self.send_message(message)

    def recently_announced(self, prior_announcement):
        if (fast_time() - prior_announcement > ANNOUNCEMENT_INTERVAL):
            return False

        return True

    @classmethod
    async def send_message(cls, msgs=None, pong=False):
        loop = asyncio.get_running_loop()
        if (pong):
            await loop.sock_sendall(cls._sock, b'PONG :tmi.twitch.tv\r\n')

            return

        for msg in msgs:

            # ensuring empty returns to do not get sent over irc
            if (not msg): continue

            L.l2(msg)
            await loop.sock_sendall(
                cls._sock, f'PRIVMSG #{CHANNEL} :{msg}\r\n'.encode('utf-8')
            )

    @classmethod
    def _update_trackers(cls):
        # updating some bot tracking vars if message passes spam filter
        cls.linecount += 1
        cls.last_message = fast_time()

    @classmethod
    def _load_json_data(cls):
        stored_data = load_from_file('config')

        cls.titles = stored_data['titles']
        cls.quotes = stored_data['quotes']


class Automate:

    _Hakcbot = Hakcbot

    def __init__(self):
        # direct reference for perf
        self._send_message = self._Hakcbot.send_message
        self._Commands = self._Hakcbot.Commands

        self.hakcusr = USER_TUPLE(
            'hakcbot', False, False, False,
            False, True, fast_time()
        )

    @classmethod
    async def start(cls):
        L.l1('[+] Starting automated command process.')

        self = cls()

        await asyncio.gather(
            self.reset_line_count(),
            *[self.timers(k, v) for k,v in Commands.AUTOMATE.items()])

    @dynamic_looper(func_type='async')
    async def reset_line_count(self):
        if (fast_time() - self._Hakcbot.last_message > FIVE_MIN):
            self._Hakcbot.linecount = 0

        return FIVE_MIN

    @dynamic_looper(func_type='async')
    async def timers(self, cmd, timer):
        if (self._Hakcbot.linecount >= randint(3,7)):
            try:
                response = getattr(self._Commands, cmd)(usr=self.hakcusr)
            except Exception as E:
                L.l0(E)
            else:
                await self._send_message(response)

        return (ONE_MIN * timer) + randint(100,250)


class Threads:
    def __init__(self, Hakcbot):
        self._Hakcbot = Hakcbot

        self._last_status = None

        # direct reference for perf
        self._send_message = self._Hakcbot.send_message

    @classmethod
    def start(cls, Hakcbot):
        L.l1('[+] Starting bot threads.')

        self = cls(Hakcbot)
        threading.Thread(target=self._uptime).start()
        threading.Thread(target=self.timeout).start()
        threading.Thread(target=self.file_task).start()

    @queue(name='timeout', func_type='thread')
    def timeout(self, username):
        message = f'/timeout {username} 3600 account age less than one day.'

        response = (
            f'{username}, you have been timed out for having an account age less that '
            'one day old. this is to prevent bot spam. if you are a human (i can tell '
            'from first message), i will remove the timeout when i see it, sorry!'
        )

        self._send_message((message, response))

    @queue(name='file_task', func_type='thread')
    def file_task(self, obj_name):
        config = load_from_file('config')
        if (obj_name not in config): return None

        updated_attribute = getattr(self._Hakcbot, obj_name)
        if isinstance(updated_attribute, set):
            updated_attribute = list(updated_attribute)

        config[obj_name] = updated_attribute

        write_to_file(config, 'config')

    @dynamic_looper(func_type='thread')
    def _uptime(self):
        try:
            uptime = requests.get(f'https://decapi.me/twitch/uptime?channel={CHANNEL}')
        except Exception:
            self._Hakcbot.uptime_message = 'Hakcbot is currently being a dumb dumb. :/'
        else:
            uptime = uptime.text.strip('\n')
            if (uptime == 'dowright is offline'):
                self._Hakcbot.online = False
                self._Hakcbot.uptime_message = 'DOWRIGHT is OFFLINE'

            else:
                self._Hakcbot.online = True
                self._Hakcbot.uptime_message = f'DOWRIGHT has been live for {uptime}'

        if (self._last_status != self._Hakcbot.online):
            self._last_status = self._Hakcbot.online

            # resetting tricho count and title announcements every stream
            if (self._Hakcbot.online):
                self._Hakcbot.Commands.tricho_count = []

                self._Hakcbot.announced_titles.clear()

        return ONE_MIN

def main():
    Hakcbot.start()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nExiting Hakcbot :(')
