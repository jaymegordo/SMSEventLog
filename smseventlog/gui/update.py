from pyupdater.client import Client
# from pkg_resources import parse_version
import warnings

from .. import functions as f
from ..__init__ import VERSION


class ClientConfig(object):
    PUBLIC_KEY = 'Rbk396oV6YSKhJtYTZHGdu/z7P/Gom11LdqI/w3AlyQ'
    APP_NAME = 'smseventlog'
    COMPANY_NAME = 'SMS Equipment Inc.'
    HTTP_TIMEOUT = 30
    MAX_DOWNLOAD_RETRIES = 3
    UPDATE_URLS = ['https://smseventlog.s3.amazonaws.com']

class Updater(object):
    def __init__(self, _version=None):
        client = Client(ClientConfig(), progress_hooks=[print_status_info])

        warnings.simplefilter('ignore', DeprecationWarning) # pyupdater turns this on, annoying

        if _version is None: _version = VERSION # only pass in _version for testing
        update_available = False
        app_update = None

        f.set_self(vars())

    def get_app_update(self):
        client = self.client
        client.refresh()

        app_update = client.update_check(client.app_name, self.version)
        if not app_update is None:
            self.update_available = True
            self.app_update = app_update

        return app_update
    
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



def print_status_info(info):
    total = info.get('total')
    downloaded = info.get('downloaded')
    status = info.get('status')
    print(downloaded, total, status)

def create_client():
    # from smseventlog.gui.client_config import ClientConfig


    # warnings.simplefilter('ignore', DeprecationWarning)
    # logging.basicConfig(level='ERROR')
    client.refresh()


    return client

