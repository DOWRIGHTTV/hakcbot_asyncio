#!/usr/bin/python3


import re
import threading
import asyncio
import time
import requests
import json
import traceback

from config import * # pylint: disable=unused-wildcard-import
from hakcbot_regex import * # pylint: disable=unused-wildcard-import
from hakcbot_utilities import load_from_file, write_to_file
from datetime import datetime
from hakcbot_utilities import Log as L
from string import ascii_letters, digits

__all__ = (
    'adjust_whitelist', 'adjust_titles'
)

def adjust_whitelist(Bot, url, action):
    current_whitelist = Bot.url_whitelist
    if (action is AK.ADD):
        if (url in current_whitelist):
            return f'{url} already actively whitelisted.'

        current_whitelist.add(url)
        L.l1(f'added {url} to whitelist')

    elif (action is AK.DEL):
        try:
            current_whitelist.remove(url)
        except KeyError:
            return f'{url} does not have an active whitelist.'

        L.l1(f'removed {url} from whitelist')

    Bot.Threads.add_file_task('url_whitelist')

def adjust_titles(Bot, name, title, tier, action):
    if (action is AK.DEL):
        user_data = Bot.titles.pop(name, None)
        old_title = user_data['title']

        L.l1(f'removed title for {name}, the {title}.')

        message = f'{name} is no longer known as the {old_title}'

    else:
        if (action is AK.ADD):

            # default to one if not specified. did not want to make kwarg default 1 though to not conflict with updates.
            if (not tier):
                tier = 1

            Bot.titles[name] = {
                'tier': tier,
                'title': title
            }
            L.l1(f'added title for {name}, the {title}.')

            message = f'{name} is now known as the {title}'

        elif (action is AK.MOD):
            user_data = Bot.titles.get(name)
            old_title = user_data['title']

            # if tier is not defined, we will grab current user tier.
            if (not tier):
                tier = user_data['tier']

            if (not title or len(title) < 5):
                title = user_data['title']

            Bot.titles[name] = {
                'tier': tier,
                'title': title
            }
            L.l1(f'updated tier {tier} title for {name}, the {title} formerly the {old_title}.')

            if (old_title == title):
                message = f'{name}, the {title}, is now tier {tier}'

            else:
                message = f'{name} (tier {tier}) is now known as the {title}, formerly the {old_title}'

    Bot.Threads.add_file_task('titles')

    return message
