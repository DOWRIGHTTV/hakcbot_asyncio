#!/usr/bin/env python3

import os
import json
import re
import time
import threading
import asyncio

from collections import deque

from hakcbot_regex import NULL, fast_time, fast_sleep, afast_sleep
from config import BROADCASTER, IDENT

#will load json data from file, convert it to a python dict, then return as object
def load_from_file(filename):
    if not filename.endswith('.json'):
        filename += '.json'

    with open(f'{filename}', 'r') as settings:
        settings = json.load(settings)

    return settings

def write_to_file(data, filename):
    if not filename.endswith('.json'):
        filename += '.json'

    with open(f'{filename}', 'w') as settings:
        json.dump(data, settings, indent=4)

def load_tlds():
    with open('TLDs') as TLDs:
        tlds = TLDs.read().splitlines()

        return set([t.lower() for t in tlds if len(t) <= 6 and not t.startswith('#')])

def dynamic_looper(*, func_type='thread'):
    '''decorator to maintain daemon loop which will sleep for the returned integer length.
    if no return is specified, sleep will not be called. default func type is for threads.'''
    def decorator(loop_function):
        if (func_type == 'thread'):
            def wrapper(*args):
                while True:
                    sleep_len = loop_function(*args)
                    if (not sleep_len): continue

                    fast_sleep(sleep_len)

        elif (func_type == 'async'):
            async def wrapper(*args):
                while True:
                    sleep_len = await loop_function(*args)
                    if (not sleep_len): continue

                    await afast_sleep(sleep_len)

        else:
            raise ValueError(f'{func_type} if not a valid. must be thread, async.')

        return wrapper
    return decorator

def queue(name, *, func_type='thread'):
    '''decorator to add custom queue mechanism for any queue handling functions. This
    is a direct replacement for dynamic/async_looper for queues.

    the func_type keyword argument will determine which wrapper gets used.
    options: thread, async

    default func type is for threads.

    example:
        @queue(Log, name='Bot', func_type='thread')
        def some_func(job):
            process(job)

    '''
    def decorator(func):

        queue = deque()
        queue_add = queue.append
        queue_get = queue.popleft

        job_available = threading.Event()
        job_wait  = job_available.wait
        job_clear = job_available.clear
        job_set   = job_available.set

        if (func_type == 'thread'):
            def wrapper(*args):
                Log.l1(f'{name}/thread-queue started.')
                while True:
                    job_wait()
                    # clearing job notification
                    job_clear()
                    # processing all available jobs
                    while queue:
                        try:
                            job = queue_get()
                            func(*args, job)
                        except Exception as E:
                            Log.l0(f'error while processing a {name}/thread-queue started job. | {E}')
                            fast_sleep(.001)

        elif (func_type == 'async'):
            async def wrapper(*args):
                Log.l1(f'{name}/async-queue started.')
                while True:
                    notified = job_wait(timeout=0)
                    if (not notified):
                        await afast_sleep(1)
                        continue

                    # clearing job notification
                    job_clear()

                    # processing all available jobs
                    while queue:
                        try:
                            job = queue_get()
                            await func(*args, job)
                        except Exception as E:
                            Log.l0(f'error while processing a {name}/async-queue started job. | {E}')
                            await afast_sleep(.1)

        else:
            raise ValueError(f'{func_type} is not valid. must be thread, async.')

        def add(job):
            '''adds job to work queue, then marks event indicating a job is available.'''
            queue_add(job)
            job_set()

        wrapper.add = add
        return wrapper
    return decorator

# LOG HANDLING #

def level(lvl):
    def decorator(_):
        @classmethod
        def wrapper(cls, *args):
            if (lvl <= cls.LEVEL): # pylint: disable=no-member
                cls.log(*args) # pylint: disable=no-member
        return wrapper
    return decorator


class Log:
    LEVEL = 2
    valid_levels = [str(i) for i in range(5)]

    @classmethod
    def log(cls, message):
        print(f'{IDENT}: {message}' if ':' not in message else message)

    @level(0)
    def l0(self, message):
        '''raised/caught exceptions.'''
        pass

    @level(1)
    def l1(self, message):
        '''bot logic eg. putting command on cooldown.'''
        pass

    @level(2)
    def l2(self, message):
        '''local generated chat messages.'''
        pass

    @level(3)
    def l3(self, message):
        '''informational output.'''
        pass

    @level(4)
    def l4(self, message):
        '''debug output.'''
        pass


class CommandStructure:
    _COMMANDS = {}
    _AUTOMATE = {}
    _SPECIAL  = {}

    # general methods for dealing with bot commands
    ## checking each word in message for a command.
    def task_handler(self, user, message):
        # if user is broadcaster and the join of words matches a valid command, the return will be the join.
        # otherwise the original message will be returned
        self._special_command = False # NOTE: this can be done better prob.
        message = self._special_check(user, message)
        for word in message:
            cmd, args = self._get_command(word)
            if (not cmd): continue

            try:
                response = getattr(self, cmd)(*args, usr=user) # pylint: disable=not-an-iterable
            except Exception as E:
                Log.l0(E)

            else:

                if (response):
                    return response

    def _special_check(self, usr, msg):
        Log.l4('special command parse started.')
        if (not usr.bcast and not usr.mod): return msg

        Log.l4('bcaster or mod identified. checking for command match.')
        join_msg = ' '.join(msg)
        if not re.fullmatch(VALID_CMD, join_msg): return msg

        Log.l4('valid command match. cross referencing special commands list.')
        cmd = re.findall(CMD, join_msg)[0]
        if cmd not in self._SPECIAL: return msg

        Log.l3(f'returning special command {join_msg}')

        self._special_command = True
        return [join_msg]

    def _get_command(self, word):
        if not re.fullmatch(VALID_CMD, word): return NULL

        cmd = re.findall(CMD, word)[0]
        if (cmd not in self._COMMANDS): return NULL

        args = re.findall(ARG, word)[0]
        if (args.startswith(',') or args.endswith(',')): return NULL
        args = args.split(',')

        Log.l3(f'pre args filter | {args}')
        for arg in args:
            if self._get_title(arg.strip()): continue

            for l in arg:

                # allow special commands to have urls. required for url whitelist.
                if ('.' in l and self._special_command): continue

                # ensuring users cannot abuse commands to bypass security control. underscores are fine because they pose
                # no (known) threat and are commonly used in usernames.
                if (not l.isalnum() and l != '_'):
                    Log.l3(f'"{l}" is not a valid command string.')
                    return NULL

        return cmd, tuple([a.strip() for a in args if a])

    # command wrappers/ utilites to make command maintenance and creation easier.

    @classmethod
    def on_cooldown(cls, c_name):
        cd_time = cls._COMMANDS.get(c_name, None)
        if (fast_time() <= cd_time): return True

        return False

    @classmethod
    def cmd(cls, cmd, cd, *, auto=None):
        cls._COMMANDS[cmd] = 1
        if (auto):
            cls._AUTOMATE[cmd] = auto
        def decorator(command_function):
            def wrapper(*args, usr):
                if any([usr.bcast, usr.mod, usr.vip, usr.sub]): pass # cooldown bypass
                elif cls.on_cooldown(cmd): return NULL
                try:
                    response = command_function(*args)
                except TypeError:
                    return NULL
                else:
                    Log.l1(f'Putting {cmd} on cooldown.')
                    cls._COMMANDS[cmd] = fast_time() + cd
                    # making msgs an iterator for compatibility with multiple response commands.
                    return (response,)
            return wrapper
        return decorator

    @classmethod
    def mod(cls, cmd, *, spc=False):
        cls._COMMANDS[cmd] = 0
        if (spc):
            cls._SPECIAL[cmd] = 1
        def decorator(command_function):
            def wrapper(*args, usr):
                if (not usr.mod and not usr.bcast): return NULL

                return command_function(*args)
            return wrapper
        return decorator

    @classmethod
    def brc(cls, cmd, *, spc=False):
        cls._COMMANDS[cmd] = 0
        if (spc):
            cls._SPECIAL[cmd] = 1
        def decorator(command_function):
            def wrapper(*args, usr):
                if (not usr.bcast): return NULL

                return command_function(*args)
            return wrapper
        return decorator
