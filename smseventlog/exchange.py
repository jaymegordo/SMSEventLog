from io import StringIO

import exchangelib as ex
import yaml

from . import functions as f
from .__init__ import *

log = logging.getLogger(__name__)


def get_credentials():
    p = Path(f.datafolder / 'email.yaml')
    with open(p) as file:
        m = yaml.full_load(file)
    return m

def create_account(failcount=0):
    log.info(f'Test logging with named logger works')
    try:
        m = get_credentials()
        credentials = ex.Credentials(m['email'], m['password'])
        account = ex.Account(m['email'], credentials=credentials, autodiscover=True)
    except:
        log.warning(f'Failed creating account: {failcount}')
        failcount +=1
        if failcount <=5:
            account = create_account(failcount=failcount)
    
    return account

def get_account():
    account = create_account()
    return account

def parse_attachment(attachment, d=None, header=2):
    result = str(attachment.content, 'UTF-8')
    data = StringIO(result)
    df = pd.read_csv(data, header=header)
    df['DateEmail'] = d # only used for dt exclusions email, it doesnt have date field
    return df

def combine_email_data(folder, maxdate, subject=None, header=2):
    a = get_account()
    fldr = a.root / 'Top of Information Store' / folder
    tz = ex.EWSTimeZone.localzone()

    # filter downtime folder to emails with date_received 2 days greater than max shift date in db
    fltr = fldr.filter(
        datetime_received__range=(
            tz.localize(ex.EWSDateTime.from_datetime(maxdate)),
            tz.localize(ex.EWSDateTime.now())))

    if not subject is None:
        fltr = fltr.filter(subject__contains=subject)

    try:
        df = pd.concat([parse_attachment(
            item.attachments[0],
            header=header,
            d=item.datetime_received.date() + delta(days=-1)) for item in fltr])
    except:
        log.warning('No emails found.')
        df = None

    return df
