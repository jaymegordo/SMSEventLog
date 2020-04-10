import io
from pathlib import Path

import exchangelib as ex
import pandas as pd
import yaml

from . import functions as f

def get_credentials():
    p = Path(f.datafolder / 'email.yaml')
    with open(p) as file:
        m = yaml.full_load(file)
    return m

def create_account(failcount=0):
    try:
        m = get_credentials()
        credentials = ex.Credentials(m['email'], m['password'])
        account = ex.Account(m['email'], credentials=credentials, autodiscover=True)
    except:
        print(f'Failed creating account: {failcount}')
        failcount +=1
        if failcount <=5:
            account = create_account(failcount=failcount)
    
    return account

def get_account():
    account = create_account()
    return account

def parse_attachment(attachment, header=2):
    result = str(attachment.content, 'UTF-8')
    data = io.StringIO(result)
    df = pd.read_csv(data, header=header)
    return df

def combine_email_data(folder, maxdate):
    a = get_account()
    fldr = a.root / 'Top of Information Store' / folder
    tz = ex.EWSTimeZone.localzone()

    # filter downtime folder to emails with date_received 2 days greater than max shift date in db
    fltr = fldr.filter(
        datetime_received__range=(
            tz.localize(ex.EWSDateTime.from_datetime(maxdate)),
            tz.localize(ex.EWSDateTime.now())))
    try:
        df = pd.concat([parse_attachment(item.attachments[0]) for item in fltr])
    except:
        df = None

    return df