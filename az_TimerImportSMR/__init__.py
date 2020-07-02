from datetime import datetime as date
import logging

import azure.functions as func
import sys
from pathlib import Path

from __app__.smseventlog import (
    functions as f,
    units as un)


def main(mytimer: func.TimerRequest) -> None:
    try:
        un.import_unit_hrs_email()
    except:
        f.senderror()
