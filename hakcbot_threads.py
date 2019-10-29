#!/usr/bin/env python3

import time
import requests
import threading

from config import *
from collections import deque


class Threads:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        self.account_age_queue = deque()

    def start(self):
        threading.Thread(target=self.uptime_thread).start()
        threading.Thread(target=self.get_accountage_queue).start()

    # if there is a problem resolving or looking up the uptime, the bot will show an error message
    def uptime_thread(self):
        print('[+] Starting Uptime tracking thread.')
        while True:
            error = False
            try:
                uptime = requests.get("https://decapi.me/twitch/uptime?channel={CHANNEL}")
                uptime = uptime.text.strip('\n')
            except Exception:
                error = True

            if (not error and uptime == 'dowright is offline'):
                self.Hakcbot.online = False
                message = 'DOWRIGHT is OFFLINE'
            elif (not error):
                self.Hakcbot.online = True
                message = self.Hakcbot.Commands.standard_commands['uptime']['message']
                message = f'{message} {uptime}'
            else:
                message = 'Hakcbot is currently being a dumb dumb. :/'

            self.Hakcbot.uptime_message = message

            time.sleep(90)

    def get_accountage_queue(self):
        print('[+] Starting account age queue thread.')
        while True:
            if (not self.account_age_queue):
                time.sleep(1)
                continue

            while self.account_age_queue:
                user = self.account_age_queue.popleft()

                threading.Thread(target=self.get_accountage, args=(user,)).start()

    # return True will mark for timeout, False will add to whitelist, None will check on next message due to errors
    @account_age
    def get_accountage(self, username):
        validate_date = {'years': None, 'months': None, 'weeks': None, 'days': None}
        try:
            account_age = requests.get(f'https://decapi.me/twitch/accountage/{username}?precision=7')
            account_age = account_age.text.strip('\n')
        except Exception:
            return None

        account_age = account_age.split(',')
        for time in account_age:
            number, name = time.strip().split()
            validate_date.update({name: number})

        for length in validate_date:
            if (not length):
                return True

        return False

    @staticmethod
    def account_age(function_to_wrap):
        def wrapper(self, username, account_age_whitelist = set()):
            if (username in account_age_whitelist):
                print(f'adding {username} to account_age whitelist!')
                return

            timeout = function_to_wrap(username)
            if (timeout is None):
                pass
            elif (timeout):
                self.Hakcbot.Automate.flag_for_timeout.append(username)
                print(f'{username} flagged for timeout due to < 1 day account age!')
            else:
                account_age_whitelist.add(username)

            self.Hakcbot.Spam.account_age_check_inprogress.remove(username)

            return wrapper
