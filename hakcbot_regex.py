#!/usr/bin/env python3

import re
import time

from enum import Enum
from collections import namedtuple

fast_time = time.time
NULL = (None, None)
ANNOUNCEMENT_INTERVAL = 90 * 60 # 90 minutes
USER_TUPLE = namedtuple('user', 'name bcast mod sub vip permit timestamp')

class AA(Enum):
    ERROR  = 0
    ACCEPT = 1
    DROP   = 2

class AK(Enum):
    DEL = 0
    ADD = 1
    MOD = 2
    EXIST = -1

SUB = re.compile(r'subscriber=(.*?);')
VIP = re.compile(r'vip/1')
MOD = re.compile(r'mod=(.*?);')
USER_TAGS = re.compile(r'@badge-info=(.*?)user-type=')
MESSAGE   = re.compile(r'user-type=(.*)')
TITLE = re.compile(r'(?P<quote>[\'"]).*?(?P=quote)')

VALID_CMD = re.compile(r'(.*?)\((.*?)\)')
CMD = re.compile(r'(.*?)\(')
ARG = re.compile(r'\((.*?)\)')

URL = re.compile(
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z]{2,}\.?)|' # Domain
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # IP Address
    r'(?::\d+)?' # Optional Port eg :8080
    r'(?:/?|[/?]\S+)',
    re.IGNORECASE) # Sepcific pages in url eg /homepage

ONE_MIN = 60
TWO_MIN = 120
THREE_MIN = 180
FIVE_MIN = 300
