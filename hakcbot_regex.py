#!/usr/bin/env python3

import sys as _sys
import re as _re
import time as _time
import asyncio as _asyncio

from enum import Enum as _Enum
from collections import namedtuple as _namedtuple

fast_time = _time.time
fast_sleep = _time.sleep
afast_sleep = _asyncio.sleep

write_err = _sys.stderr.write

NULL = (None, None)
ANNOUNCEMENT_INTERVAL = 120 * 60 # 120 minutes
USER_TUPLE = _namedtuple('user', 'name bcast mod sub vip permit timestamp')

class AA(_Enum):
    ERROR  = 0
    ACCEPT = 1
    DROP   = 2

class AK(_Enum):
    DEL = 0
    ADD = 1
    MOD = 2
    EXIST = -1

SUB = _re.compile(r'subscriber=(.*?);')
VIP = _re.compile(r'vip/1')
MOD = _re.compile(r'mod=(.*?);')
USER_TAGS = _re.compile(r'@badge-info=(.*?)user-type=')
MESSAGE   = _re.compile(r'user-type=(.*)')
TITLE = _re.compile(r'(?P<quote>[\'"]).*?(?P=quote)')

VALID_CMD = _re.compile(r'(.*?)\((.*?)\)')
CMD = _re.compile(r'(.*?)\(')
ARG = _re.compile(r'\((.*?)\)')

URL = _re.compile(
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z]{2,}\.?)|' # Domain
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # IP Address
    r'(?::\d+)?' # Optional Port eg :8080
    r'(?:/?|[/?]\S+)',
    _re.IGNORECASE) # Sepcific pages in url eg /homepage

ONE_MIN = 60
TWO_MIN = 120
THREE_MIN = 180
FIVE_MIN = 300
