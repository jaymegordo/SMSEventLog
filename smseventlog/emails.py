import io
from pathlib import Path

import exchangelib as ex
import pandas as pd
import yaml

from . import functions as f
from .__init__ import *

if sys.platform.startswith('dar'):
    from appscript import app, k
    from mactypes import Alias

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
    data = io.StringIO(result)
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


# OUTLOOK
class Outlook(object):
    def __init__(self):
        is_win = f.is_win()

        if is_win:
            import win32com.client as win32
            outlook = win32.Dispatch('outlook.application')
            mail = outlook.CreateItem(0)
            mail.Subject = subject_name
            mail.HTMLbody = ''
        else:
            client = app('Microsoft Outlook')
        
        f.set_self(self, vars())
    
class Message(object):
    def __init__(self, parent=None, subject='', body='', to_recip=[], cc_recip=[], show_=True):
        
        if parent is None: parent = Outlook()
        client = parent.client

        msg = client.make(
            new=k.outgoing_message,
            with_properties={k.subject: subject, k.content: body})

        f.set_self(self, vars())

        self.add_recipients(emails=to_recip, type_='to')
        self.add_recipients(emails=cc_recip, type_='cc')

        if show_: self.show()

    def show(self):
        self.msg.open()
        self.msg.activate()

    def add_attachment(self, p):
        p = Alias(str(p)) # convert string to POSIX/mactypes path idk
        attach = self.msg.make(new=k.attachment, with_properties={k.file: p})

    def add_recipients(self, emails, type_='to'):
        if not isinstance(emails, list): emails = [emails]
        for email in emails:
            self.add_recipient(email=email, type_=type_)

    def add_recipient(self, email, type_='to'):
        msg = self.msg

        if type_ == 'to':
            recipient = k.to_recipient
        elif type_ == 'cc':
            recipient = k.cc_recipient

        msg.make(new=recipient, with_properties={k.email_address: {k.address: email}})
        