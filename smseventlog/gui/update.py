# from pkg_resources import parse_version
import warnings

from pyupdater.client import Client
from hurry.filesize import size

from .. import functions as f
from ..__init__ import VERSION

warnings.simplefilter('ignore', DeprecationWarning) # pyupdater turns this on, annoying

# Use Pyupdater Client/AppUpdate classes to check, download, and install updates

class ClientConfig(object):
    PUBLIC_KEY = 'Rbk396oV6YSKhJtYTZHGdu/z7P/Gom11LdqI/w3AlyQ'
    APP_NAME = 'SMS Event Log'
    COMPANY_NAME = 'SMS Equipment Inc.'
    HTTP_TIMEOUT = 30
    MAX_DOWNLOAD_RETRIES = 3
    UPDATE_URLS = ['https://smseventlog.s3.amazonaws.com']

class Updater(object):
    def __init__(self, mw=None, test_version=None):
        client = Client(ClientConfig(), progress_hooks=[self.print_status_info])

        warnings.simplefilter('ignore', DeprecationWarning) # pyupdater turns this on, annoying

        _version = VERSION if test_version is None else test_version
        update_available = False
        app_update = None

        f.set_self(vars())

    def update_statusbar(self, msg):
        if not self.mw is None:
            self.mw.update_statusbar(msg)
        else:
            print(msg)

    def get_app_update(self):
        client = self.client
        client.refresh()

        app_update = client.update_check(client.app_name, self.version)
        if not app_update is None:
            self.update_available = True
            self.app_update = app_update

        return app_update
    
    def check_update(self):
        app_update = self.get_app_update()

        if self.update_available:
            self.update_statusbar(msg='Update is available, download started.')

            app_update.download() # background=True # don't need, already in a worker thread
            if app_update.is_downloaded():
                self.update_statusbar(msg='Update successfully downloaded.')

                return self

        else:
            self.update_statusbar(msg='No update available.')
        
    def install_update(self):
        app_update = self.app_update
        if not app_update is None and app_update.is_downloaded():
            app_update.extract_restart()

    def print_finished(self):
        self.update_statusbar(msg='download finished.')
    
    def print_status_info(self, info):
        total = info.get('total')
        downloaded = info.get('downloaded')
        status = info.get('status')
        pct = downloaded / total
        self.update_statusbar(msg=f'Update {status} - {size(total)} - {pct:.0%}')
    
    @property
    def version(self):
        if not self.app_update is None:
            ver_long = self.app_update.current_version
            ver = '.'.join(ver_long.split('.')[:3])
            return ver
        else:
            return self._version
    
    @property
    def latest_version(self):
        if not self.app_update is None:
            return self.app_update.version
        else:
            return None





def create_client():
    # from smseventlog.gui.client_config import ClientConfig


    # warnings.simplefilter('ignore', DeprecationWarning)
    # logging.basicConfig(level='ERROR')
    client.refresh()


    return client
