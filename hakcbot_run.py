#!/usr/bin/python3

import threading
import uvloop, asyncio
import requests
import time
import traceback

from socket import socket

from config import * # pylint: disable=unused-wildcard-import
from hakcbot_init import Initialize
from hakcbot_spam import Spam
from hakcbot_execute import Execute
from hakcbot_commands import Commands
from hakcbot_accountage import AccountAge

from hakcbot_regex import fast_time, USER_TUPLE, ONE_MIN, FIVE_MIN, ANNOUNCEMENT_INTERVAL
from hakcbot_utilities import dynamic_looper, queue
from hakcbot_utilities import load_from_file, write_to_file, Log as L


class Hakcbot:
    online = False
    linecount = 0
    last_message = 0
    uptime_message = 'hakbot is still initializing! try again in a bit.'

    announced_titles = {}
    _sock = socket()

    def __init__(self):
        self.Execute  = Execute(self)
        self.Commands = Commands(self)

    @classmethod
    def start(cls):
        Initialize.setup(cls)

        Automate.setup(cls)
        Threads.start(cls)
        AccountAge.start(cls, Automate)
        Spam.setup(cls)

        uvloop.install()

        self = cls()
        asyncio.run(self.main())

    async def main(self):
        await Initialize.start()

        await asyncio.gather(self.hakc_general(), self.hakc_automation())

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

    async def _message_handler(self, data):
        # NOTE: probably dont need user definition
        loop, user = asyncio.get_running_loop(), None
        if (data == 'PING :tmi.twitch.tv'):
            await loop.sock_sendall(self._sock, 'PONG :tmi.twitch.tv\r\n'.encode('utf-8'))

        elif ('PRIVMSG' in data):
            spam_filter = Spam(data)
            user, message = await spam_filter.pre_process()

            if (not user and not message): return

            elif (not user):
                self.send_message(message)

            else:
                # function will check if already in progress before sending to the queue
                AccountAge.add_to_queue(user)

                await self.Execute.task_handler(user, message)

        # placeholder for when i want to track joins/ see if a user joins
        elif ('JOIN' in data):
            L.l3(data)

        # probably a bunk ass message, not sure????? should protect higher tier titles for now.
        else:
            L.l3(f'else: {data}')
            return

        # T2 TITLES
        if (not user): return
        try:
            titled_user = self.titles[user.name] # pylint: disable=no-member
        except KeyError:
            pass
        else:
            prior_announcement = self.announced_titles.get(user.name, None)
            if titled_user['tier'] == 2 and not self.recently_announced(prior_announcement):

                # already announced users - type > set()
                self.announced_titles[user.name] = fast_time()

                # announcing the user to chat
                if (self.online):
                    await self.announce_title(user.name, titled_user['title'])

    async def announce_title(self, user, title):
        # message needs to be iterable for compatibility with commands.
        message = [f'attention! {user}, the {title}, has spoken.']

        await self.send_message(*message)

    def recently_announced(self, prior_announcement):
        if (not prior_announcement): return False

        current_time = fast_time()
        if (current_time - prior_announcement > ANNOUNCEMENT_INTERVAL):
            return False

        return True

    async def send_message(self, *msgs):
        loop = asyncio.get_running_loop()
        for msg in msgs:

            # ensuring empty returns to do not get sent over irc
            if (not msg): continue

            L.l2(msg)
            await loop.sock_sendall(
                self._sock, f'PRIVMSG #{CHANNEL} :{msg}\r\n'.encode('utf-8')
            )

    # NOTE: we can probably clean this up and make the Automate class alittle more native like
    async def hakc_automation(self):
        L.l1('[+] Starting automated command process.')

        self.Automate = Automate()
        await asyncio.gather(
            self.Automate.reset_line_count(),
            self.Automate.timeout(), # pylint: disable=no-value-for-parameter
            *[self.Automate.timers(k, v) for k,v in self.Commands._AUTOMATE.items()])

class Automate:

    def __init__(self):
        self.hakcusr = USER_TUPLE(
            'hakcbot', False, False, False,
            False, True, fast_time()
        )

    @classmethod
    def setup(cls, Hakcbot):
        cls._Hackbot = Hakcbot

    @dynamic_looper(func_type='async')
    async def reset_line_count(self):
        if (fast_time() - self._Hakcbot.last_message > FIVE_MIN):
            self._Hakcbot.linecount = 0

        return FIVE_MIN

    @dynamic_looper(func_type='async')
    # NOTE: this is no longer working!!!
    async def timers(self, cmd, timer):
        if (self._Hakcbot.linecount >= 3):
            # getattr(self.Hakcbot.Commands, cmd)(usr=self.hakcusr)
            pass

        return ONE_MIN * timer

    @queue(name='timeout', func_type='async')
    async def timeout(self, username):
        message = f'/timeout {username} 3600 account age less than one day.'

        response = f'{username}, you have been timed out for having an account age \
            less that one day old. this is to prevent bot spam. if you are a human \
            (i can tell from first message), i will remove the timeout when i see it, \
            sorry!'

        await self._Hakcbot.send_message(message, response)


class Threads:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        self._last_status = None

    @classmethod
    def start(cls, Hakcbot):
        L.l1('[+] Starting bot threads.')

        self = cls(Hakcbot)
        threading.Thread(target=self._uptime).start()
        threading.Thread(target=self.file_task).start()

    # temp until we switch reference to queue object add function itself.
    def add_file_task(self, obj_name):
        self.file_task.add(obj_name) # pylint: disable=no-member

    @queue(name='file_task', func_type='thread')
    def file_task(self, obj_name):
        config = load_from_file('config')
        if (obj_name not in config): return None

        updated_attribute = getattr(self.Hakcbot, obj_name)
        if isinstance(updated_attribute, set):
            updated_attribute = list(updated_attribute)

        config[obj_name] = updated_attribute

        write_to_file(config, 'config')

    @dynamic_looper(func_type='thread')
    def _uptime(self):
        try:
            uptime = requests.get(f'https://decapi.me/twitch/uptime?channel={CHANNEL}')
        except Exception:
            self.Hakcbot.uptime_message = 'Hakcbot is currently being a dumb dumb. :/'
        else:
            uptime = uptime.text.strip('\n')
            if (uptime == 'dowright is offline'):
                self.Hakcbot.online = False
                self.Hakcbot.uptime_message = 'DOWRIGHT is OFFLINE'

            else:
                self.Hakcbot.online = True
                self.Hakcbot.uptime_message = f'DOWRIGHT has been live for {uptime}'

        if (self._last_status != self.Hakcbot.online):
            self._last_status = self.Hakcbot.online

            # resetting tricho count and title announcements every stream
            if (self.Hakcbot.online):
                self.Hakcbot.Commands.tricho_count = 0

                self.Hakcbot.announced_titles.clear()

        return 90

def main():
    Hb = Hakcbot()
    Hb.start()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nExiting Hakcbot :(')
