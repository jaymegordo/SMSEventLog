from datetime import datetime as date
import logging

import azure.functions as func
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[1] / 'smseventlog'))

import functions as f
import availability as av


def main(mytimer: func.TimerRequest) -> None:
    try:
        av.import_downtime()
    except:
        f.senderror()
