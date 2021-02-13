import logging
import sys
import os
from pathlib import Path

import azure.functions as func

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

from __app__.smseventlog import (
    errors as er,
    functions as f)
from __app__.smseventlog.data import (
    availability as av,
    units as un)

def err():
    msg = 'Http function not triggered.'
    log.error(msg, exc_info=True)
    return func.HttpResponse(msg, status_code=400)

@er.errlog(discord=True)
def main(req: func.HttpRequest) -> func.HttpResponse:
    action = req.params.get('action')
    log.info(f'HTTP trigger function processed request: {action}')
    if not action:
        try:
            req_body = req.get_json()
        except:
            return err()
        else:
            action = req_body.get('action')

    if action == 'import_downtime':
        av.import_downtime_email()
    elif action == 'import_smr':
        un.import_unit_hrs_email()
    else:
        return err()
    
    return func.HttpResponse(f'{action} success!', status_code=200)
        