#!/usr/bin/env python3

import time
import requests
import threading

from collections import deque


class AccountAge:
    ''' this class is to check the account age of all users sending messages in the twitch/irc chat. this class is a standard
    queue, but once the user gets checked it will be added to a whitelist to prevent subsequent checks until the bot is restart.
    adding to the queue will done as a async function to be compatible with the main bot code, but the class itself will be
    utiliting threads to achieve concurrent processing.
    '''

    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        self.account_age_queue = deque()
        self.aa_check_in_progress = set()

    def start(self):
        threading.Thread(target=self.handle_queue).start()

    async def add_to_queue(self, user):
        if (user.name not in self.aa_check_in_progress):
            self.aa_check_in_progress.add(user.name)

            print(f'added {user.name} to account age queue!')
            self.account_age_queue.append(user)

    def handle_queue(self):
        print('[+] Starting account age queue thread.')
        while True:
            if (not self.account_age_queue):
                time.sleep(1)
                continue

            user = self.account_age_queue.popleft()
            threading.Thread(target=self.get_accountage, args=(user,)).start()

    # pylint: disable=no-self-argument, not-callable
    def account_age(function_to_wrap):
        def wrapper(self, user, account_age_whitelist=set()):
            if (user.sub or user.vip or
                    user.name in account_age_whitelist):
                return

            timeout, vd, aa = function_to_wrap(self, user.name)
            if (timeout is None):
                pass
            elif (timeout):
                self.Hakcbot.Automate.flag_for_timeout.append(user.name)
                print(f'{user.name} flagged for timeout due to < 1 day account age!')
                print(f'{user.name} >> {vd} | {aa}')
            else:
                print(f'adding {user.name} to account_age whitelist!')
                account_age_whitelist.add(user.name)

            self.aa_check_in_progress.remove(user.name)

        return wrapper

    # return True will mark for timeout, False will add to whitelist, None will check on next message due to errors
    @account_age
    def get_accountage(self, username):
        validate_date = {
            'year' : None, 'years' : None,
            'month': None, 'months': None,
            'week' : None, 'weeks' : None,
            'day'  : None, 'days'  : None
            }

        try:
            account_age = requests.get(f'https://decapi.me/twitch/accountage/{username}?precision=7')
            account_age = account_age.text.strip('\n')
        except Exception:
            return None, validate_date, account_age

        account_age = account_age.split(',')
        for time in account_age:
            number, name = time.strip().split()
            if (name in validate_date):
                validate_date[name] = number

        for amount in validate_date.values():
            if (amount):
                return False, validate_date, account_age
        else:
            return True, validate_date, account_age
