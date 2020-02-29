#!/usr/bin/python3

import threading, asyncio
import requests
import time
import traceback

from config import *
from socket import socket
from collections import deque

from hakcbot_init import Init
from hakcbot_accountage import AccountAge
from hakcbot_execute import Execute
from hakcbot_spam import Spam
from hakcbot_commands import Commands


class Hakcbot:
    def __init__(self):
        self.sock = socket()
        self.Init   = Init(self)

        self.Automate = Automate(self)
        self.Execute = Execute(self)
        self.Spam = Spam(self)
        self.Commands = Commands(self)
        self.AccountAge = AccountAge(self)

        self.linecount = 0

        self.online = False
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
            user, message = valid_data
            # function will check if already in progress before sending to the queue
            await self.AccountAge.add_to_queue(user)
            await self.Execute.parse_message(user, message)

        # placeholder for when i want to track joins/ see if a user joins
        elif ('JOIN' in data): pass

    # async def hakc_automation(self):
    #     cmds = []
    #     timers = []

    #     for t_count, cmd in enumerate(self.Commands.automated, 1):
    #         cmds.append(cmd)
    #         timers.append(self.Commands.automated[cmd]['timer'])

    #     try:
    #         await asyncio.gather(
    #             self.Automate.reset_line_count(), self.Automate.timeout(),
    #             *[self.Automate.timers(cmds[t], timers[t]) for t in range(t_count)])

    #     except Exception as E:
    #         print(f'AsyncIO General Error | {E}')

    # pylint: disable=undefined-variable
    async def send_message(self, message, response=None):
        loop = asyncio.get_running_loop()
        print(f'hakcbot: {message}')
        message = f'PRIVMSG #{CHANNEL} :{message}'

        await loop.sock_sendall(self.sock, f'{message}\r\n'.encode('utf-8'))
        if (response):
            response = f'PRIVMSG #{CHANNEL} :{response}'
            await loop.sock_sendall(self.sock, f'{response}\r\n'.encode('utf-8'))

    # if there is a problem resolving or looking up the uptime, the bot will show an error message
    def uptime_thread(self):
        print('[+] Starting Uptime tracking thread.')
        while True:
            error = False
            try:
                uptime = requests.get(f'https://decapi.me/twitch/uptime?channel={CHANNEL}')
                uptime = uptime.text.strip('\n')
            except Exception:
                error = True

            if (not error and uptime == 'dowright is offline'):
                self.online = False
                message = 'DOWRIGHT is OFFLINE'
            elif (not error):
                self.online = True
                message = f'DOWRIGHT has been live for {uptime}'
            else:
                message = 'Hakcbot is currently being a dumb dumb. :/'

            self.uptime_message = message

            time.sleep(90)

class Automate:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        self.flag_for_timeout = deque()
        self.thread_message_queue = deque()

    async def reset_line_count(self):
        while True:
            await asyncio.sleep(60 * 5)
            self.Hakcbot.linecount = 0

    async def timers(self, cmd, timer):
        try:
            message = self.Hakcbot.Commands.standard_commands[cmd]['message']
            while True:
                await asyncio.sleep(60 * timer)
                cooldown = getattr(self.Hakcbot.Commands, f'hakc{cmd}')
                if (not cooldown and self.Hakcbot.linecount >= 3):
                    await self.Hakcbot.send_message(message)
                elif (cooldown):
                    print(f'hakcbot: {cmd} command on cooldown')
        except Exception as E:
            print(f'AsyncIO Timer Error: {E}')

    async def timeout(self):
        while True:
            if (not self.flag_for_timeout):
                await asyncio.sleep(1)
                continue

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
