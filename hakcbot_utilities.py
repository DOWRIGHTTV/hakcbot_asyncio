#!/usr/bin/env python3

import os
import json
import re
import time
import asyncio

from collections import deque

from hakcbot_regex import NULL
from config import BROADCASTER, IDENT

#will load json data from file, convert it to a python dict, then return as object
def load_from_file(filename):
    with open(f'{filename}', 'r') as settings:
        settings = json.load(settings)

    return settings

def write_to_file(data, filename):
    with open(f'{filename}', 'w') as settings:
        json.dump(data, settings, indent=4)

def dynamic_looper(loop_function):
    '''decorator to maintain daemon loop which will sleep for the returned integer length.
    if no return is specified, sleep will not be called.'''
    def wrapper(*args):
        while True:
            sleep_len = loop_function(*args)
            if (not sleep_len): continue

            time.sleep(sleep_len)
    return wrapper

def async_looper(loop_function):
    '''async decorator to maintain daemon loop which will sleep for the returned integer length.
    if no return is specified, sleep will not be called.'''
    async def wrapper(*args):
        while True:
            sleep_len = await loop_function(*args)
            if (not sleep_len): continue

            await asyncio.sleep(sleep_len)
    return wrapper

def level(lvl):
    def decorator(_):
        @classmethod
        def wrapper(cls, *args):
            if (lvl <= cls._LEVEL): # pylint: disable=no-member
                cls.log(*args) # pylint: disable=no-member
        return wrapper
    return decorator


class Log:
    _LEVEL = 2

    @classmethod
    def log(cls, message):
        print(f'{IDENT}: {message}')

    @level(0)
    def l0(cls):
        '''raised/caught exceptions.'''
        pass

    @level(1)
    def l1(cls):
        '''bot logic eg. putting command on cooldown.'''
        pass

    @level(2)
    def l2(cls):
        '''local generated chat messages.'''
        pass

    @level(3)
    def l3(cls):
        '''informational output.'''
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

                response = command_function(*args)
                # making msgs an iterator for compatibility with multiple response commands.
                return cd, (response,)
            return wrapper
        return decorator

    @classmethod
    def mod(cls, cmd):
        cls._COMMANDS[cmd] = 0
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
