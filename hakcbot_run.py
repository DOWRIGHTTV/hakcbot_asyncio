#!/usr/bin/python3

import threading, asyncio
import requests
import time
import traceback

from config import *
from socket import socket
from collections import deque

from hakcbot_init import Init
from hakcbot_spam import Spam
from hakcbot_execute import Execute
from hakcbot_commands import Commands
from hakcbot_accountage import AccountAge
from hakcbot_utilities import dynamic_looper, async_looper, CommandStructure as cs


class Hakcbot:
    def __init__(self):
        self.sock = socket()
        self.Init = Init(self)

        self.Automate = Automate(self)
        self.Spam     = Spam(self)
        self.Execute  = Execute(self)
        self.Commands = Commands(self)
        self.AccountAge = AccountAge(self)

        self.online = False
        self.linecount = 0
        self.last_message = 0
        self.uptime_message = 'hakbot is still initializing! try again in a bit.'

    def start(self):
        threading.Thread(target=self.uptime_thread).start()

        self.AccountAge.start()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        asyncio.run(self.main())

    async def main(self):
        await self.Init.initialize()

        await self.Spam.create_tld_set()
        await self.Spam.adjust_blacklist()
        await self.Spam.adjust_whitelist()

        await asyncio.gather(self.hakc_general()) #, self.hakc_automation())

    async def hakc_general(self):
        loop = asyncio.get_running_loop()
        while True:
            try:
                data = await loop.sock_recv(self.sock, 1024)
            except OSError as E:
                print(f'MAIN SOCKET ERROR | ATTEMPING RECONNECT | {E}')
                break
            else:
                if (not data):
                    print('SOCKET CLOSED BY REMOTE SERVER | ATTEMPING RECONNECT')
                    break

                await self._message_handler(data.decode('utf-8', 'ignore').strip())

        # closing socket and recursively calling main to attempt reconnect
        self.sock.close()
        await self.main()

    async def _message_handler(self, data):
        loop = asyncio.get_running_loop()
        if (data == 'PING :tmi.twitch.tv'):
            await loop.sock_sendall(self.sock, 'PONG :tmi.twitch.tv\r\n'.encode('utf-8'))

        elif ('PRIVMSG' in data):
            valid_data = await self.Spam.main(data)
            if (not valid_data): return

            self.linecount += 1
            self.last_message = time.time()
            user, message = valid_data
            # function will check if already in progress before sending to the queue
            await self.AccountAge.add_to_queue(user)
            await self.Execute.parse_message(user, message)

        # placeholder for when i want to track joins/ see if a user joins
        elif ('JOIN' in data): pass

    async def hakc_automation(self):
        await asyncio.gather(
            self.Automate.reset_line_count(),
            self.Automate.timeout(),
            *[self.Automate.timers(k, v) for k,v in cs.AUTOMATE.items()])

    # pylint: disable=undefined-variable
    async def send_message(self, message, response=None):
        loop = asyncio.get_running_loop()
        print(f'hakcbot: {message}')
        message = f'PRIVMSG #{CHANNEL} :{message}'

        await loop.sock_sendall(self.sock, f'{message}\r\n'.encode('utf-8'))
        if (not response): return

        response = f'PRIVMSG #{CHANNEL} :{response}'
        await loop.sock_sendall(self.sock, f'{response}\r\n'.encode('utf-8'))

    @dynamic_looper
    def uptime_thread(self):
#        print('[+] Starting Uptime tracking thread.')
        try:
            uptime = requests.get(f'https://decapi.me/twitch/uptime?channel={CHANNEL}')
            uptime = uptime.text.strip('\n')
        except Exception:
            self.uptime_message = 'Hakcbot is currently being a dumb dumb. :/'
        else:
            if (uptime == 'dowright is offline'):
                self.online = False
                self.uptime_message = 'DOWRIGHT is OFFLINE'
            else:
                self.online = True
                self.uptime_message = f'DOWRIGHT has been live for {uptime}'

        return 90


class Automate:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        self.flag_for_timeout = deque()
        self.thread_message_queue = deque()

    @async_looper
    async def reset_line_count(self):
        time_elapsed = time.time() - self.Hakcbot.last_message
        if (time_elapsed > 300):
            self.Hakcbot.linecount = 0

        return 300

    async def timers(self, cmd, timer):
        if (self.Hakcbot.linecount >= 3):
            await getattr(self.Hakcbot.Commands, cmd)(usr=None)

        return 60 * timer

    @async_looper
    async def timeout(self):
        if (not self.flag_for_timeout): return 1

        while self.flag_for_timeout:
            username = self.flag_for_timeout.popleft()
            message = f'/timeout {username} 3600 account age less than one day.'
            response = f'{username}, you have been timed out for having an account age \
                less that one day old. this is to prevent bot spam. if you are a human \
                (i can tell from first message), i will remove the timeout when i see it, \
                sorry!'

            await self.Hakcbot.send_message(message, response)

def main():
    Hb = Hakcbot()
    Hb.start()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Exiting Hakcbot :(')
