from datetime import datetime as date
import logging

import azure.functions as func
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[1] / 'smseventlog'))

import functions as f
import units as un


def main(mytimer: func.TimerRequest) -> None:
    try:
        un.import_unit_hrs_email()
    except:
        f.senderror()
