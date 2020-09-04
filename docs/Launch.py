# file must be copied to:
# /Users/Jayme/.ipython/profile_default/startup
# these commands/imports run when vscode Python Interactive window is started/reloaded
# print statements dont show

#%% IMPORTS
import sys
import os
import json
import yaml
from pathlib import Path
import logging
from collections import defaultdict as dd
import inspect

from time import time
from timeit import Timer

import pandas as pd
import numpy as np
import pypika as pk
import sqlalchemy as sa

from pypika import Case, Criterion
from pypika import CustomFunction as cf
from pypika import Order, Query
from pypika import Table as T
from pypika import functions as fn
from pypika.analytics import RowNumber

try:
    # logging.basicConfig(level=logging.NOTSET)
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)
    # sh = logging.StreamHandler()
    # sh.setLevel(logging.DEBUG)
    # log.addHandler(sh)
    # log.info('imports started')
except:
    pass

from datetime import (date, datetime as dt, timedelta as delta)

if not sys.platform.startswith('win'):
    project_path = '/Users/Jayme/OneDrive/Python/SMS' 
else:
    project_path = 'Y:/OneDrive/Python/SMS'
sys.path.append(project_path) # so we can import from smseventlog

from smseventlog import (
    functions as f,
    dbtransaction as dbt,
    errors as er,
    queries as qr,
    factorycampaign as fc,
    folders as fl,
    email as em,
    availability as av,
    units as un,
    reports as rp,
    styles as st,
    charts as ch,
    oilsamples as oil,
    web)

from smseventlog.gui import (
    startup,
    gui as ui,
    dialogs as dlgs,
    refreshtables as rtbls,
    tables as tbls,
    datamodel as dm,
    eventfolders as efl,
    formfields as ff)

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

