import yaml

from . import functions as f
from .__init__ import *

log = logging.getLogger(__name__)

class CredentialManager(object):
    # load and save credentials to QSettings
    # prompt for creds when not found
    config = {
        'tsi': {
            'id_type': 'username',
            'keys': ['id', 'password']},
        'exchange': {
            'id_type': 'email',
            'keys': ['id', 'password']},
        'sap': {
            'id_type': 'username',
            'keys': ['id', 'password', 'token']}}

    def __init__(self, name, prompt=False, gui=True, prefix=True):
        encode_key = 'wwdlkoeedfdk'
        if AZURE_WEB or AZURE_LOCAL: gui = False

        if gui:
            # if gui, will need dialogs for prompts
            from .gui import _global as gbl
            from .gui import dialogs as dlgs
            self.dlgs = dlgs
            
            settings = gbl.get_settings()
            config_gui = {
                'tsi': {
                    'prompt': dlgs.TSIUserName},
                'exchange': {
                    'prompt': dlgs.ExchangeLogin},
                'sap': {
                    'prompt': dlgs.SuncorConnect}}
            
            # merge specific gui config into config
            for key, m in self.config.items():
                m.update(config_gui.get(key, {}))

        else:
            # load from config.yaml
            prefix = False
            p_static_creds = f.resources / 'apikeys/credentials.yaml'
            with open(p_static_creds) as file:
                static_creds_full = yaml.full_load(file)
                static_creds = static_creds_full.get(name, None)

        self.config = self.config.get(name, {})
        id_type = self.config.get('id_type', 'username')

        f.set_self(vars())
        
        if prompt: self.prompt_credentials()
    
    def load(self):
        # load id/pw from QSettings
        name = self.name
        keys = self.config.get('keys', [])
        m = self.load_multi(keys=keys)

        if self.gui and any(m.get(x) is None for x in ('id', 'password')):
            # no creds found in QSettings
            m = self.prompt_credentials()
            if m == False: return None # user exited dialog

        # always return in order defined eg id, password, token
        return tuple(m.get(key, None) for key in keys)
    
    def save_single(self, key, val):

        # obfuscate pw before writing to settings
        if self.gui and 'password' in key.lower():
            val = f.encode(key=self.encode_key, string=val)
            
        if self.prefix:
            key = f'{self.name}_{key.lower()}'

        self.settings.setValue(key, val)
    
    def save_multi(self, vals):
        # vals is dict of keys/vals
        if AZURE_WEB: return

        if self.gui:
            for key, val in vals.items():
                self.save_single(key, val)
        else:
            # for non-gui, need to just dump full file back with updates
            try:
                self.static_creds.update(vals)
                self.static_creds_full[self.name].update(self.static_creds)

                # NOTE could write a better func for updating part of a yaml file
                with open(self.p_static_creds, 'w+') as file:
                    yaml.dump(self.static_creds_full, file)
            except:
                log.warning(f'Failed to write credentials back to file: {vals}')
    
    def load_single(self, key):
        if self.gui:
            if self.prefix:
                key = f'{self.name}_{key}'
                
            val = self.settings.value(key.lower(), defaultValue=None)

            # decrypt pw before usage
            if not val is None and 'password' in key.lower():
                val = f.decode(key=self.encode_key, string=val)
            
            return val

        else:
            # load from static settings in credentials.yaml (for azure funcs)
            return self.static_creds.get(key, None)
    
    def load_multi(self, keys):
        # simple lookup of requested keys, return dict of key/val
        m = {}
        for key in keys:
            m[key] = self.load_single(key=key)

        return m
    
    def prompt_credentials(self):
        # prompt user to input id/password, can be triggered automatically or manually by user
        prompt = self.config.get('prompt', None)

        if not prompt is None:
            dlg = prompt()
            if dlg.exec_():
                # return id/password from dialog and save
                m = {k.lower(): v for k, v in dlg.items.items()} # change to lower() keys
                m['id'] = m.pop(self.id_type, None) # change username/email to 'id'

                self.save_multi(vals=m)
                self.dlgs.msg_simple(msg='Successfully saved credentials.')

                return m
            else:
                return False
        else:
            raise AttributeError(f'Couldn\'t find credential prompt for: {self.name}')
