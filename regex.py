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

ADD_WL = re.compile(r'addwl\((.*?)\)')
DEL_WL = re.compile(r'delwl\((.*?)\)')

PERMIT_USER = re.compile(r'permit\((.*?)\)')
URL = re.compile(
r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z]{2,}\.?)|' # Domain
r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # IP Address
r'(?::\d+)?' # Optional Port eg :8080
r'(?:/?|[/?]\S+)', re.IGNORECASE) # Sepcific pages in url eg /homepage
