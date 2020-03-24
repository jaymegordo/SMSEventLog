import logging
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parents[1] / 'smseventlog'))

import azure.functions as func

import functions as f
import availability as av

def err():
    return func.HttpResponse('ERROR: Http function not triggered.', status_code=400)

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        action = req.params.get('action')
        if not action:
            try:
                req_body = req.get_json()
            except:
                return err()
            else:
                action = req_body.get('action')

        if action == 'import':
            av.import_downtime()
        else:
            return err()
        
        return func.HttpResponse(f'{action} success!', status_code=200)
    except:
        try:
            f.senderror()
        finally:
            return err()
        