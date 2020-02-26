# from collections import defaultdict
import sys
from datetime import datetime as date
from datetime import timedelta as delta
from pathlib import Path

import yaml

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

config = getconfig()