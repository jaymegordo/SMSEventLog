import functools
import logging
from logging.handlers import RotatingFileHandler
import operator as op
import os
import sys
import time
from collections import defaultdict as dd
from datetime import date
from datetime import datetime as dt
from datetime import timedelta as delta
from functools import partial
from pathlib import Path
from timeit import default_timer as timer
import copy

import pandas as pd
import numpy as np
import pypika as pk
from dateutil.relativedelta import relativedelta
from pypika import Case, Criterion, DatePart
from pypika.terms import PseudoColumn
from pypika import CustomFunction as cf
from pypika import Order, Query
from pypika import Table as T
from pypika import functions as fn
from pypika.analytics import RowNumber

try:
    from IPython.display import display
except ModuleNotFoundError:
    pass

__version__ = '3.3.5'
VERSION = __version__

# Set environments
AZURE_LOCAL = os.getenv('AZURE_FUNCTIONS_ENVIRONMENT', False) # dont think these are used
AZURE_WEB = True if os.getenv('WEBSITE_SITE_NAME', None) else False

SYS_FROZEN = getattr(sys, 'frozen', False)

def getlog(name):
    """Factory to create logger with 'smseventlog' removed from name"""
    name = '.'.join(str(name).split('.')[1:])
    
    # cant set name to nothing or that calls the ROOT logger
    if name == '': name = 'base'

    log = logging.getLogger(name)

    if not AZURE_WEB:
        log.setLevel(logging.DEBUG)
        log.addHandler(sh)
        log.addHandler(fh)

    return log

if sys.platform.startswith('win'):
    applocal = Path.home() / 'AppData/Local/SMS Equipment Inc/SMS Event Log'
else:
    applocal = Path.home() / 'Library/Application Support/SMS Event Log'

if not AZURE_WEB:
    # create logger
    p_log = applocal / 'logging'
    if not p_log.exists():
        p_log.mkdir(parents=True)

    log_path = p_log / 'smseventlog.log'
    fmt_stream = logging.Formatter('%(levelname)-7s %(lineno)-4d %(name)-20s %(message)s')
    fmt_file = logging.Formatter(
        '%(asctime)s  %(levelname)-7s %(lineno)-4d %(name)-20s %(message)s', datefmt='%m-%d %H:%M:%S')

    # Console/stream handler
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt_stream)

    # File handler for log file
    fh = RotatingFileHandler(log_path, maxBytes=100000, backupCount=0)

    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt_file)

