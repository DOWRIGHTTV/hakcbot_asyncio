#!/usr/bin/env python3

import time
import requests
import threading

from collections import deque

from config import BROADCASTER
from hakcbot_regex import AA
from hakcbot_utilities import queue, Log as L


class AccountAge:
    ''' this class is to check the account age of all users sending messages in the twitch/irc chat. this class is a standard
    queue, but once the user gets checked it will be added to a whitelist to prevent subsequent checks until the bot is restart.
    adding to the queue will done as a async function to be compatible with the main bot code, but the class itself will be
    utiliting threads to achieve concurrent processing.
    '''
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

        self._check_in_progress = set()

        self.whitelist = set()

    def start(self):
        L.l1('[+] Starting account age queue thread.')
        threading.Thread(target=self.account_age).start()

    def add_to_queue(self, usr):
        '''async io function for adding tasks to account age queue.'''
        if (usr.bcast or usr.mod or usr.sub or usr.vip or usr.name in self.whitelist): return

        if (usr.name not in self._check_in_progress):
            self._check_in_progress.add(usr.name)

            self.account_age.add(usr) # pylint: disable=no-member

    @queue(name='account_age', func_type='thread')
    def account_age(self, user):
        threading.Thread(target=self._account_age, args=(user,)).start()

    def _account_age(self, user):
        L.l1(f'{user.name} added to account age queue!')
        result, vd, aa = self._get_accountage(user.name)
        if (result is AA.ACCEPT):
            L.l1(f'{user.name} added to account_age whitelist!')
            self.whitelist.add(user.name)

        elif (result is AA.DROP):
            self.Hakcbot.Automate.flag_for_timeout.add(user.name)
            L.l1(f'user timeout | {user.name} >> {vd} | {aa}')

        elif (result is AA.ERROR):
            L.l1('account age error while connecting to api.')

        self._check_in_progress.remove(user.name)

    # return True will mark for timeout, False will add to whitelist, None will check on next message due to errors
    def _get_accountage(self, username):
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
            return AA.ERROR, validate_date, account_age

        if ('404' in account_age): return AA.ERROR, None, None

        account_age = account_age.split(',')
        for t in account_age:
            number, name = t.strip().split()
            if (name in validate_date):
                validate_date[name] = number

        for amount in validate_date.values():
            if (amount):
                return AA.ACCEPT, validate_date, account_age
        else:
            return AA.DROP, validate_date, account_age
