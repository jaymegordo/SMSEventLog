import logging
import os
import sys

__version__ = '3.0.0'

azure_env = os.getenv("AZURE_FUNCTIONS_ENVIRONMENT")
azure_web = os.getenv('WEBSITE_INSTANCE_ID')
sys_frozen = getattr(sys, 'frozen', False)

m = dict(azure_env=azure_env,
    azure_web=azure_web,
    sys_frozen=sys_frozen,
    sys_platform=sys.platform)

if not (sys_frozen or 'linux' in sys.platform):
    # when not running from packaged app, import all libraries for easy access in interactive terminal
    import json
    from datetime import (datetime as dt, timedelta as delta)
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
        emails as em,
        availability as av,
        units as un,
        reports as rp)

    from .gui import gui as ui
    from .gui import dialogs as dlgs
    from .gui import refreshtables as rtbls
    from .gui import tables as tbls
    from .dbmodel import *
    from .database import db