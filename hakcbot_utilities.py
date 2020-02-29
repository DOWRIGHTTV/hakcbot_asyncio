#!/usr/bin/env python3

import os
import json
import re
import time

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

class CommandStructure:
    COMMANDS = {}

    @classmethod
    def on_cooldown(cls, c_name):
        cd_time = cls.COMMANDS.get(c_name, None)
        if (time.time() <= cd_time):
            return True

        return False

    @classmethod
    def command(cls, c_name, cd_len):
        def decorator(command_function):
            cls.COMMANDS[c_name] = 0
            async def wrapper(*args, usr):
                if (usr.mod or usr.name == BROADCASTER): pass # cooldown bypass
                elif cls.on_cooldown(c_name): return NULL

                response = await command_function(*args)
                return cd_len, (response,) # forcing tuple to ensure general compatibility
            return wrapper
        return decorator

    @classmethod
    def mod(cls, c_name):
        def decorator(command_function):
            cls.COMMANDS[c_name] = 0
            async def wrapper(*args, usr):
                if (not usr.mod and usr.name != BROADCASTER): return NULL

                return None, await command_function(*args)
            return wrapper
        return decorator

    @classmethod
    def broadcaster(cls, c_name):
        def decorator(command_function):
            cls.COMMANDS[c_name] = 0
            async def wrapper(*args, usr):
                if (usr.name != BROADCASTER): return NULL

                return None, await command_function(*args)
            return wrapper
        return decorator
