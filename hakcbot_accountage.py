#!/usr/bin/env python3

import requests
import threading

from collections import deque

from config import BROADCASTER # pylint: disable=no-name-in-module
from hakcbot_regex import AA
from hakcbot_utilities import queue, Log as L


class AccountAge:
    ''' this class is to check the account age of all users sending messages in the twitch/irc chat. this class is a standard
    queue, but once the user gets checked it will be added to a whitelist to prevent subsequent checks until the bot is restart.
    adding to the queue will done as a async function to be compatible with the main bot code, but the class itself will be
    utiliting threads to achieve concurrent processing.
    '''
    _start = False
    _check_in_progress = set()

    whitelist = set()

    def __init__(self, Hakcbot, Threads):
        self._Hakcbot = Hakcbot
        self._Threads = Threads

        self._wl_add = self.whitelist.add
        self._in_prog_del = self._check_in_progress.remove
        self.aa_add = self._account_age.add # pylint: disable=no-member

    @classmethod
    def start(cls, Hakcbot, Automate):
        if (cls._start):
            raise RuntimeError('Account Age has already been started!')

        L.l1('[+] Starting account age queue thread.')

        cls._in_prog_add = cls._check_in_progress.add

        self = cls(Hakcbot, Automate)
        threading.Thread(target=self._account_age).start()

    @classmethod
    def add_to_queue(cls, usr):
        '''adding users to account age queue if they are not whitelisted or have a special role.'''

        #if any([usr.bcast, usr.mod, usr.sub, usr.vip]) or (usr.name in cls.whitelist): return
        if (usr.permit) or (usr.name in cls.whitelist): return

        if (usr.name not in cls._check_in_progress):
            cls._in_prog_add(usr.name)

            cls.aa_add(usr) # pylint: disable=no-member

    @queue(name='account_age', func_type='thread')
    def _account_age(self, user):
        L.l1(f'{user.name} added to account age queue!')

        result, vd, aa = self._get_accountage(user.name)

        if (result is AA.ACCEPT):
            self._wl_add(user.name)

            L.l1(f'{user.name} added to account_age whitelist!')

        elif (result is AA.DROP):
            self._Threads.timeout.add(user.name)

            L.l1(f'user timeout | {user.name} >> {vd} | {aa}')

        elif (result is AA.ERROR):
            L.l1('account age error while connecting to api.')

        self._in_prog_del(user.name)

    @staticmethod
    # return True will mark for timeout, False will add to whitelist, None will check on next message due to errors
    def _get_accountage(username):
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

        if any(validate_date.values()):
            return AA.ACCEPT, validate_date, account_age

        else:
            return AA.DROP, validate_date, account_age
