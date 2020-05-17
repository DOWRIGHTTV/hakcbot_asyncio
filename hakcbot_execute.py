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


class Execute:
    def __init__(self, Hakcbot):
        self.Hakcbot = Hakcbot

    def adjust_whitelist(self, url, action):
        current_whitelist = self.Hakcbot.url_whitelist
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

        self.Hakcbot.Threads.add_file_task('url_whitelist')

    # NOTE: currently unused
    def adjust_blacklist(self, url=None, action=None):
        config = load_from_file('config.json')
        self.blacklist = set(config['blacklist'])

    def adjust_titles(self, name, title, tier, action):
        if (action is AK.DEL):
            user_data = self.Hakcbot.titles.pop(name, None)
            old_title = user_data['title']

            L.l1(f'removed title for {name}, the {title}.')

            message = f'{name} is no longer known as the {old_title}'

        else:
            if (action is AK.ADD):

                # default to one if not specified. did not want to make kwarg default 1 though to not conflict with updates.
                if (not tier):
                    tier = 1

                self.Hakcbot.titles[name] = {
                    'tier': tier,
                    'title': title
                }
                L.l1(f'added title for {name}, the {title}.')

                message = f'{name} is now known as the {title}'

            elif (action is AK.MOD):
                user_data = self.Hakcbot.titles.get(name)
                old_title = user_data['title']

                # if tier is not defined, we will grab current user tier.
                if (not tier):
                    tier = user_data['tier']

                if (not title or len(title) < 5):
                    title = user_data['title']

                self.Hakcbot.titles[name] = {
                    'tier': tier,
                    'title': title
                }
                L.l1(f'updated tier {tier} title for {name}, the {title} formerly the {old_title}.')

                if (old_title == title):
                    message = f'{name}, the {title}, is now tier {tier}'

                else:
                    message = f'{name} (tier {tier}) is now known as the {title}, formerly the {old_title}'

        self.Hakcbot.Threads.add_file_task('titles')

        return message

    def _get_title(self, arg):
        title = re.match(TITLE, arg)

        return title[0] if title else None
