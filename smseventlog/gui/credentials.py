from . import _global as gbl
from . import dialogs as dlgs
from .__init__ import *


class CredentialManager(object):
    # load and save credentials to QSettings
    # prompt for creds when not found
    config = {
        'tsi': {
            'prompt': dlgs.TSIUserName,
            'id_type': 'username'},
        'exchange': {
            'prompt': dlgs.ExchangeLogin,
            'id_type': 'email'}}

    def __init__(self, name, prompt=False):
        settings = gbl.get_settings()
        _id, _password = None, None
        id_type = self.config.get(name, {}).get('id_type', 'username')

        f.set_self(vars())
        
        if prompt: self.prompt_credentials()
    
    def load(self):
        # load id/pw from QSettings
        s, name = self.settings, self.name

        _id = s.value(f'{name}_{self.id_type}', defaultValue=None)
        _password = s.value(f'{name}_password', defaultValue=None)

        if _id is None or _password is None:
            # no creds found in QSettings
            self.prompt_credentials()
        else:
            # save to self
            self._id, self._password = _id, _password

        return self._id, self._password
    
    def prompt_credentials(self):
        # prompt user to input id/password, can be triggered automatically or manually by user
        prompt = self.config.get(self.name, {}).get('prompt', None)

        if not prompt is None:
            dlg = prompt()
            if dlg.exec_():
                # return id/password from dialog and save
                m = dlg.items
                _id, password = m[self.id_type.title()], m['Password']
                self.save(id=_id, password=password)

                return True
            else:
                return False
        else:
            raise AttributeError(f'Couldn\'t find credential prompt for: {self.name}')
    
    def save(self, id, password):
        s, name = self.settings, self.name
        s.setValue(f'{name}_{self.id_type}', id)
        s.setValue(f'{name}_password', password)
        dlgs.msg_simple(msg='Successfully saved credentials.')
        self._id, self._password = id, password
