from datetime import datetime as date
import logging

import azure.functions as func
import sys
from pathlib import Path

from __app__.smseventlog import ( # noqa
    functions as f)
from __app__.smseventlog.data import ( # noqa
    availability as av)

log = logging.getLogger(__name__)

def main(mytimer: func.TimerRequest) -> None:
    try:
        av.import_downtime_email()
        av.import_dt_exclusions_email()
        log.info('Ran import_downtime_email')
    except:
        log.info('failed to run')
        f.senderror()
