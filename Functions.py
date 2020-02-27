# from collections import defaultdict
import functools
import sys
from datetime import datetime as date
from datetime import timedelta as delta
from pathlib import Path

import pandas as pd
import yaml
from IPython.display import display

global drive
global config
if sys.platform.startswith('win'):
    drive = 'P:/'
else:
    drive = '/Volumes/Public/'

def topfolder():
    # TODO: this needs to be dynamic
    return Path(__file__).parent

def getconfig():
    p = Path(topfolder()) / 'config.yaml'
    with open(p) as file:
        m = yaml.full_load(file)
    
    return m

def deltasec(start, end):
    return str(delta(seconds=end - start)).split('.')[0]

def cursor_to_df(cursor):
    data = (tuple(t) for t in cursor.fetchall())
    cols = [column[0] for column in cursor.description]
    return pd.DataFrame(data=data, columns=cols)

def left_justified(df, header=False):
    formatters = {}
    for li in list(df.columns):
        max = df[li].str.len().max()
        form = "{{:<{}s}}".format(max)
        formatters[li] = functools.partial(str.format, form)
    # display(formatters)
    return df.to_string(formatters=formatters, index=False, header=header)

config = getconfig()
