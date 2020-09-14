from io import StringIO

import exchangelib as ex
import yaml

from . import functions as f
from .__init__ import *

log = logging.getLogger(__name__)


class ExchangeAccount(object):
    def __init__(self, gui=False, login=True):
        if login: self.login()
        _exch = None

        f.set_self(vars(), exclude='login')
    
    @property
    def exch(self):
        # exchangelib account object
        if self._exch is None:
            self._exch = self.create_account()
        
        return self._exch
    
    def get_credentials(self):
        # try getting credentials from QSettings or saved credentials file
        if self.gui:
            from .gui.credentials import CredentialManager
            email, password = CredentialManager(name='exchange').load()

        else:
            m = f.get_credentials(name='exchange')
            email, password = m['email'], m['password']
        
        return email, password
    
    def login(self):
        self._exch = self.create_account()

    def create_account(self, failcount=0):
        try:
            email, password = self.get_credentials()
            credentials = ex.Credentials(email, password)
            account = ex.Account(m['email'], credentials=credentials, autodiscover=True)
        except:
            log.warning(f'Failed creating account: {failcount}')
            failcount +=1
            if failcount <=5:
                account = create_account(failcount=failcount)
        
        return account

def parse_attachment(attachment, d=None, header=2):
    result = str(attachment.content, 'UTF-8')
    data = StringIO(result)
    df = pd.read_csv(data, header=header)
    df['DateEmail'] = d # only used for dt exclusions email, it doesnt have date field
    return df

def combine_email_data(folder, maxdate, subject=None, header=2):
    a = ExchangeAccount().get_account()
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
