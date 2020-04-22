#!/usr/bin/env python3

import os
import json
import re
import time
import threading
import asyncio

from collections import deque

from hakcbot_regex import NULL
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

def dynamic_looper(*, func_type='thread'):
    '''decorator to maintain daemon loop which will sleep for the returned integer length.
    if no return is specified, sleep will not be called. default func type is for threads.'''
    def decorator(loop_function):
        if (func_type == 'thread'):
            def wrapper(*args):
                while True:
                    sleep_len = loop_function(*args)
                    if (not sleep_len): continue

                    time.sleep(sleep_len)

        elif (func_type == 'async'):
            async def wrapper(*args):
                while True:
                    sleep_len = await loop_function(*args)
                    if (not sleep_len): continue

                    await asyncio.sleep(sleep_len)

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
                            time.sleep(.001)

        elif (func_type == 'async'):
            async def wrapper(*args):
                Log.l1(f'{name}/async-queue started.')
                while True:
                    notified = job_wait(timeout=0)
                    if (not notified):
                        await asyncio.sleep(2)
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
                            await asyncio.sleep(.1)

        else:
            raise ValueError(f'{func_type} if not a valid. must be thread, async.')

        def add(job):
            '''adds job to work queue, then marks event indicating a job is available.'''
            queue_add(job)
            job_available.set()

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
    def l0(self):
        '''raised/caught exceptions.'''
        pass

    @level(1)
    def l1(self):
        '''bot logic eg. putting command on cooldown.'''
        pass

    @level(2)
    def l2(self):
        '''local generated chat messages.'''
        pass

    @level(3)
    def l3(self):
        '''informational output.'''
        pass

    @level(4)
    def l4(self):
        '''debug output.'''
        pass


class CommandStructure:
    _COMMANDS = {}
    _AUTOMATE = {}
    _SPECIAL  = {}

    @classmethod
    def on_cooldown(cls, c_name):
        cd_time = cls._COMMANDS.get(c_name, None)
        if (time.time() <= cd_time): return True

        return False

    @classmethod
    def cmd(cls, cmd, cd, *, auto=None):
        cls._COMMANDS[cmd] = 0
        if (auto):
            cls._AUTOMATE[cmd] = auto
        def decorator(command_function):
            def wrapper(*args, usr):
                if (usr.mod or usr.bcast): pass # cooldown bypass
                elif cls.on_cooldown(cmd): return NULL
                try:
                    response = command_function(*args)
                except TypeError:
                    return NULL
                else:
                    # making msgs an iterator for compatibility with multiple response commands.
                    return cd, (response,)
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

                return None, command_function(*args)
            return wrapper
        return decorator

    @classmethod
    def brc(cls, cmd, *, spc=False):
        if (spc):
            cls._SPECIAL[cmd] = 1
        cls._COMMANDS[cmd] = 0
        def decorator(command_function):
            def wrapper(*args, usr):
                if (not usr.bcast): return NULL

                return None, command_function(*args)
            return wrapper
        return decorator
