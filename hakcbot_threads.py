#!/usr/bin/env python3

import time
import requests
import threading

from collections import deque


class Threads:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        self.account_age_whitelist = set()
        self.account_age_queue = deque()

    def Start(self):
        threading.Thread(target=self.Uptime).start()
        threading.Thread(target=self.AccountAgeQueue).start()

    def Uptime(self):
        while True:
            uptime = requests.get("https://decapi.me/twitch/uptime?channel=dowright")
            uptime = uptime.text.strip('\n')
            if (uptime == 'dowright is offline'):
                self.Hakcbot.online = False
                message = 'DOWRIGHT is OFFLINE'
            else:
                self.Hakcbot.online = True
                message = self.Hakcbot.Commands.commands['uptime']['message']
                message = f'{message} {uptime}'

            self.Hakcbot.uptime_message = message

            time.sleep(90)

    def AccountAgeQueue(self):
        while True:
            if (not self.account_age_queue):
                time.sleep(1)
                continue

            while self.account_age_queue:
                user = self.account_age_queue.popleft()

                threading.Thread(target=self.CheckAccountAge, args=(user,)).start()

    def CheckAccountAge(self, user):
#        print(f'IN PROG: {self.Hakcbot.Spam.account_age_check_inprogress}')
        error = False
        # if there is a problem resolving or looking up the account age, the bot will auto allow
        try:
            account_age = requests.get(f'https://decapi.me/twitch/accountage/{user}?precision=7')
            account_age = account_age.text.strip('\n')
        except Exception:
            error = True

        if (not error and 'day' not in account_age and 'week' not in account_age
                and 'month' not in account_age and 'year' not in account_age):
            self.Hakcbot.Automate.flag_for_timeout.append(user)

        elif (not error):
            self.Hakcbot.Spam.account_age_whitelist.add(user)

        self.Hakcbot.Spam.account_age_check_inprogress.remove(user)
