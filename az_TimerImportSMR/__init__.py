from datetime import datetime as date
import logging

import azure.functions as func
import sys
from pathlib import Path

from __app__.smseventlog import (
    errors as er)
from __app__.smseventlog.data import (
    units as un)

@er.errlog(discord=True)
def main(mytimer: func.TimerRequest) -> None:
    er.init_sentry()
    un.import_unit_hrs_email_all()
