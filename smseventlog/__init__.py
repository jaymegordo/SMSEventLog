import sys

__version__ = '3.0.0'

if not getattr(sys, 'frozen', False):
    # when not running from packaged app, import all libraries for easy access in interactive terminal
    import json
    from datetime import (datetime as date, timedelta as delta)
    from pathlib import Path
    from time import time
    from timeit import Timer

    import pandas as pd
    import pypika as pk
    import xlwings as xw
    import yaml
    import sqlalchemy as sa

    from . import (
        eventlog as el,
        factorycampaign as fc,
        folders as fl,
        functions as f,
        gui as ui,
        emails as em,
        availability as av,
        units as un,
        reports as rp)
    from .dbmodel import *
    from .database import db