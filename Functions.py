# from collections import defaultdict
from datetime import datetime as date
from datetime import timedelta as delta
from pathlib import Path

import yaml


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
