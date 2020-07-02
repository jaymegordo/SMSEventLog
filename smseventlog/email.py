from . import functions as f
from .__init__ import *

if f.is_mac():
    from aeosa.appscript import app, k
    from aeosa.mactypes import Alias
elif f.is_win():
    import win32com.client as win32


# OUTLOOK
class Outlook(object):
    def __init__(self):
        is_win = f.is_win()

        if is_win:
            outlook = win32.Dispatch('outlook.application')
            mail = outlook.CreateItem(0)
            mail.Subject = '' #subject_name
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
        