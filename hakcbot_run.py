#!/usr/bin/python3

import threading, asyncio
import requests
import time
import traceback

from config import * # pylint: disable=unused-wildcard-import
from socket import socket
from collections import deque, namedtuple

from hakcbot_init import Init
from hakcbot_spam import Spam
from hakcbot_execute import Execute
from hakcbot_commands import Commands
from hakcbot_accountage import AccountAge

from hakcbot_regex import fast_time, USER_TUPLE, ONE_MIN, FIVE_MIN, ANNOUNCEMENT_INTERVAL
from hakcbot_utilities import dynamic_looper, queue
from hakcbot_utilities import load_from_file, write_to_file, Log as L


class Hakcbot:
    def __init__(self):
        self.sock = socket()
        self.Init = Init(self)

        self.Automate = Automate(self)
        self.Threads  = Threads(self)
        self.Spam     = Spam(self)
        self.Execute  = Execute(self)
        self.Commands = Commands(self)
        self.AccountAge = AccountAge(self)

        self.online = False
        self.linecount = 0
        self.last_message = 0
        self.uptime_message = 'hakbot is still initializing! try again in a bit.'

        self.announced_titles = {}

    def start(self):
        self.Threads.start()
        self.AccountAge.start()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        asyncio.run(self.main())

    async def main(self):
        await self.Init.initialize()

        await asyncio.gather(self.hakc_general(), self.hakc_automation())

    async def hakc_general(self):
        L.l1('[+] Starting main bot process.')
        loop = asyncio.get_running_loop()
        while True:
            try:
                data = await loop.sock_recv(self.sock, 1024)
            except OSError as E:
                L.l3(f'MAIN SOCKET ERROR | ATTEMPING RECONNECT | {E}')
                break
            else:
                if (not data):
                    L.l3('SOCKET CLOSED BY REMOTE SERVER | ATTEMPING RECONNECT')
                    break

                await self._message_handler(data.decode('utf-8', 'ignore').strip())

        # closing socket and recursively calling main to attempt reconnect
        self.sock.close()
        await self.main()

    async def _message_handler(self, data):
        loop, user = asyncio.get_running_loop(), None
        if (data == 'PING :tmi.twitch.tv'):
            await loop.sock_sendall(self.sock, 'PONG :tmi.twitch.tv\r\n'.encode('utf-8'))

        elif ('PRIVMSG' in data):
            valid_data = await self.Spam.pre_process(data)
            if (not valid_data): return

            self.linecount += 1
            self.last_message = fast_time()
            user, message = valid_data
            # function will check if already in progress before sending to the queue
            self.AccountAge.add_to_queue(user)
            await self.Execute.task_handler(user, message)

        # placeholder for when i want to track joins/ see if a user joins
        elif ('JOIN' in data): pass

        # probably a bunk ass message, not sure????? should protect higher tier titles for now.
        else:
            return

        ### FUTURE USE - FOR T2 TITLES ###
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
                self.sock, f'PRIVMSG #{CHANNEL} :{msg}\r\n'.encode('utf-8')
            )

    async def hakc_automation(self):
        L.l1('[+] Starting automated command process.')
        await asyncio.gather(
            self.Automate.reset_line_count(),
            self.Automate.timeout(), # pylint: disable=no-value-for-parameter
            *[self.Automate.timers(k, v) for k,v in self.Commands._AUTOMATE.items()])

class Automate:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        self.hakcusr = USER_TUPLE(
            'hakcbot', False, False, False,
            False, True, fast_time()
        )

    # temp until we switch reference to queue object add function itself.
    def flag_for_timeout(self, username):
        self.timeout.add(username) # pylint: disable=no-member

    @dynamic_looper(func_type='async')
    async def reset_line_count(self):
        time_elapsed = fast_time() - self.Hakcbot.last_message
        if (time_elapsed > FIVE_MIN):
            self.Hakcbot.linecount = 0

        return FIVE_MIN

    @dynamic_looper(func_type='async')
    async def timers(self, cmd, timer):
        if (self.Hakcbot.linecount >= 3):
            getattr(self.Hakcbot.Commands, cmd)(usr=self.hakcusr)

        return ONE_MIN * timer

    @queue(name='timeout', func_type='async')
    async def timeout(self, username):
        message = f'/timeout {username} 3600 account age less than one day.'
        response = f'{username}, you have been timed out for having an account age \
            less that one day old. this is to prevent bot spam. if you are a human \
            (i can tell from first message), i will remove the timeout when i see it, \
            sorry!'

        await self.Hakcbot.send_message(message, response)


class Threads:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        self._last_status = None

    def start(self):
        L.l1('[+] Starting bot threads.')
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
