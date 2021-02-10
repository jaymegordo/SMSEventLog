from datetime import datetime as date
import logging

import azure.functions as func
import sys
from pathlib import Path

from __app__.smseventlog import ( # noqa
    errors as er)
from __app__.smseventlog.data import ( # noqa
    availability as av)

log = logging.getLogger(__name__)

@er.errlog(discord=True)
def main(mytimer: func.TimerRequest) -> None:
    er.init_sentry()
    av.import_downtime_email()
    av.import_dt_exclusions_email()
    log.info('Ran import_downtime_email')
