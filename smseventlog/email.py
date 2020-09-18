import re

from . import functions as f
from .__init__ import *

if f.is_mac():
    from aeosa.appscript import app, k # noqa
    from aeosa.mactypes import Alias # noqa
elif f.is_win():
    import win32com.client as win32 # noqa

log = logging.getLogger(__file__)

# OUTLOOK
class Outlook(object):
    def __init__(self):
        is_win = f.is_win()
        _folders = None
        _wo_folder = None

        if is_win:
            client = win32.Dispatch('Outlook.Application')
        else:
            client = app('Microsoft Outlook')

        f.set_self(vars())

    @property
    def folders(self):
        if self._folders is None:
            if self.is_win:
                pass
            else:
                self._folders = self.client.mail_folders.get()
        
        return self._folders
    
    def get_folder_messages(self, folder):
        # return folder messages sorted by date_received descending
        if not self.is_win:
            messages = folder.messages()
            messages = sorted(messages, key=lambda x: x.time_received(), reverse=True)
        else:
            pass
    
        return messages
            
    @property
    def wo_folder(self):
        # WO Request folder, used for finding WO request emails to read back into event log
        if self._wo_folder is None:
            wo_folder_list = list(filter(lambda x: 'wo request' in str(x.name()).lower(), self.folders))
            if wo_folder_list:
                self._wo_folder = wo_folder_list[0]

        return self._wo_folder
    
    def get_wo_number(self, unit, title):
        # get WO number from outlook folder 'WO Request'
        # match on unit and title
        return
    
class Message(object):
    def __init__(self, parent=None, subject='', body='', to_recip=None, cc_recip=None, show_=True):
        
        if parent is None: parent = Outlook()
        is_win = parent.is_win
        client = parent.client

        font = 'Calibri'
        body = f'<div style="font-family: {font};">{body}</div>'

        if is_win:
            _msg = client.CreateItem(0)
            _msg.Subject = subject
            
            # GetInspector makes outlook get the message ready for display, which adds in default email sig
            _msg.GetInspector
            initial_body = _msg.HTMLBody
            body_start = re.search("<body.*?>", initial_body).group()
            _msg.HTMLBody = re.sub(
                pattern=body_start,
                repl=f'{body_start}{body}',
                string=initial_body)

        else: # mac
            _msg = client.make(
                new=k.outgoing_message,
                with_properties={k.subject: subject, k.content: body})

        f.set_self(vars())

        self.add_recipients(emails=to_recip, type_='to')
        self.add_recipients(emails=cc_recip, type_='cc')

        if show_: self.show()

    def show(self):
        msg = self._msg

        if self.is_win:
            msg.Display(False)
        else:
            msg.open()
            msg.activate()

    def add_attachments(self, lst_attach=None):
        if lst_attach is None: return
        if not isinstance(lst_attach, list): lst_attach = [lst_attach]
        for p in lst_attach:
            try:
                self.add_attachment(p=p)
            except:
                log.warning(f'Couldn\'t add attachment: {p}')

    def add_attachment(self, p):
        msg = self._msg

        if self.is_win:
            msg.Attachments.Add(Source=str(p))
        else:
            p = Alias(str(p)) # convert string to POSIX/mactypes path idk
            attach = msg.make(new=k.attachment, with_properties={k.file: p})

    def add_recipients(self, emails, type_='to'):
        if emails is None: return

        # ensure email list is unique, sorted alphabetically, and lowercase
        if not isinstance(emails, (list, set)): emails = set(emails)
        emails = sorted({x.lower() for x in emails})

        if self.is_win:
            recips = ';'.join(emails)
            msg = self._msg

            if type_ == 'to':
                msg.To = recips
            elif type_ == 'cc':
                msg.CC = recips

        else:
            # mac needs to make 'recipient' objects and add emails seperately
            for email in emails:
                self.add_recipient(email=email, type_=type_)

    def add_recipient(self, email, type_='to'):

        if type_ == 'to':
            recipient = k.to_recipient
        elif type_ == 'cc':
            recipient = k.cc_recipient

        self._msg.make(new=recipient, with_properties={k.email_address: {k.address: email}})
    
def email_test(df=None):
    # testing to figure out outlook column widths
    from . import styles as st

    style = st.default_style(df, outlook=True) \
        .pipe(st.set_column_widths, vals=dict(Status=100, Description=400, Title=100), outlook=True)

    html = style.hide_index().render()
    st.write_html(html)
    body = f'{f.greeting()}{html}'
    msg = Message(subject='test', body=body)
    return msg
