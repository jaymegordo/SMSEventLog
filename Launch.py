#%% IMPORTS
import sys
from pathlib import Path
import logging
from collections import defaultdict as dd
logging.basicConfig(level=logging.WARNING)

from datetime import (date, datetime as dt, timedelta as delta)

# from smseventlog import *
import json
from time import time
from timeit import Timer

import pandas as pd
import numpy as np
import pypika as pk
import xlwings as xw
import yaml
import sqlalchemy as sa
from appscript import *

from smseventlog import (
    functions as f,
    eventlog as el,
    queries as qr,
    factorycampaign as fc,
    folders as fl,
    emails as em,
    availability as av,
    units as un,
    reports as rp,
    styles as st,
    charts as ch,
    web)

from smseventlog.gui import (
    startup,
    gui as ui,
    dialogs as dlgs,
    refreshtables as rtbls,
    tables as tbls,
    datamodel as dm)

from smseventlog.dbmodel import *
from smseventlog.database import db

print('**import finished')

# from PyQt5.QtCore import (QDate, QDateTime)


#%%
if False:
    import cProfile
    import pstats

    filename = 'profile_stats.stats'

    # cProfile.run('run_single(symbol=symbol,\
    # 						strattype=strattype,\
    # 						startdate=startdate,\
    # 						dfall=df,\
    # 						speed0=speed[0],\
    # 						speed1=speed[1],\
    # 						norm=norm)',
    # 						filename = filename)

    p = 'P:/Regional/SMS West Mining/SMS Event Log/Import FC/GordoJ3_200215104610_wb1.xls'
    cProfile.run('fc.read_fc(p=p)', filename=filename)
    stats = pstats.Stats(filename)
    stats.strip_dirs().sort_stats('cumulative').print_stats(30)

