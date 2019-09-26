#!/usr/bin/env python3

import re

YOUR_MOM = re.compile(r'yourmom\((.*?)\)')
YOUR_MUM = re.compile(r'yourmum\((.*?)\)')
FLAG = re.compile(r'flag\((.*?)\)')
UNFLAG = re.compile(r'unflag\((.*?)\)')
PRAISE = re.compile(r'praise\((.*?)\)')
QUOTE = re.compile(r'quote\((.*?)\)')
QUOTE_ADD = re.compile(r'quoteadd\((.*?),(.*?)\)')

GIVE_ENTER = re.compile(r'enter\((.*?)\)')
GIVE_STATUS = re.compile(r'status\((.*?)\)')

USER_TAGS = re.compile(r'@badge-info=(.*?)user-type=')
MESSAGE = re.compile(r'user-type=(.*)')