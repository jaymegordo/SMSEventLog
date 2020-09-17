import functools
import logging
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

import pandas as pd
import numpy as np
import pypika as pk
from dateutil.relativedelta import relativedelta
from pypika import Case, Criterion
from pypika import CustomFunction as cf
from pypika import Order, Query
from pypika import Table as T
from pypika import functions as fn
from pypika.analytics import RowNumber

try:
    from IPython.display import display
except ModuleNotFoundError:
    pass

__version__ = '3.1.13'
VERSION = __version__

AZURE_ENV = os.getenv("AZURE_FUNCTIONS_ENVIRONMENT") # dont think these are used
AZURE_WEB = os.getenv('WEBSITE_INSTANCE_ID')

SYS_FROZEN = getattr(sys, 'frozen', False)

# create logger
fmt = logging.Formatter('%(levelname)s: %(name)s - %(lineno)d -  %(message)s')
sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(fmt)
# log.addHandler(sh)