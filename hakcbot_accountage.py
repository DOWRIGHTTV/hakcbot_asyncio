#!/usr/bin/env python3

import time
import requests
import threading

from collections import deque


class AcountAge:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        self.account_age_queue = deque()
        self.aa_check_in_progress = set()

    def start(self):
        threading.Thread(target=self.get_accountage_queue).start()

    async def add_to_accountage_queue(self, user):
        if (user not in self.aa_check_in_progress):
            self.aa_check_in_progress.add(user)

            self.account_age_queue.append(user)

    @staticmethod
    def account_age(function_to_wrap):
        def wrapper(self, username, in_progress = set(), account_age_whitelist = set()):
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

            self.aa_check_in_progress.remove(username)

            return wrapper

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
