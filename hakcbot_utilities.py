#!/usr/bin/env python3

import os
import json
import re
import time
import asyncio

from hakcbot_regex import NULL
from config import BROADCASTER

#will load json data from file, convert it to a python dict, then return as object
def load_from_file(filename):
    with open(f'{filename}', 'r') as settings:
        settings = json.load(settings)

    return settings

def write_to_file(data, filename, folder='data'):
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


class CommandStructure:
    COMMANDS = {}
    AUTOMATE = {}

    @classmethod
    def on_cooldown(cls, c_name):
        cd_time = cls.COMMANDS.get(c_name, None)
        if (time.time() <= cd_time):
            return True

        return False

    @classmethod
    def command(cls, cmd, cd, *, auto=None):
        cls.COMMANDS[cmd] = 0
        if (auto):
            cls.AUTOMATE[cmd] = auto
        def decorator(command_function):
            async def wrapper(*args, usr):
                if (usr.mod or usr.name == BROADCASTER): pass # cooldown bypass
                elif cls.on_cooldown(cmd): return NULL

                response = await command_function(*args)
                return cd, (response,) # forcing tuple to ensure general compatibility
            return wrapper
        return decorator

    @classmethod
    def mod(cls, cmd):
        cls.COMMANDS[cmd] = 0
        def decorator(command_function):
            async def wrapper(*args, usr):
                if (not usr.mod and usr.name != BROADCASTER): return NULL

                return None, await command_function(*args)
            return wrapper
        return decorator

    @classmethod
    def broadcaster(cls, cmd):
        cls.COMMANDS[cmd] = 0
        def decorator(command_function):
            async def wrapper(*args, usr):
                if (usr.name != BROADCASTER): return NULL

                return None, await command_function(*args)
            return wrapper
        return decorator
