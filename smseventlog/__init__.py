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

__version__ = '3.0.5'
VERSION = __version__

azure_env = os.getenv("AZURE_FUNCTIONS_ENVIRONMENT")
azure_web = os.getenv('WEBSITE_INSTANCE_ID')
sys_frozen = getattr(sys, 'frozen', False)

m = dict(azure_env=azure_env,
    azure_web=azure_web,
    sys_frozen=sys_frozen,
    sys_platform=sys.platform)


