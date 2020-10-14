# from pkg_resources import parse_version
import warnings
import logging

from pyupdater.client import Client
from hurry.filesize import size

from .. import functions as f
from .. import errors as er
from ..__init__ import VERSION
from ..utils import fileops as fl

warnings.simplefilter('ignore', DeprecationWarning) # pyupdater turns this on, annoying
log = logging.getLogger(__name__)

# Use Pyupdater Client/AppUpdate classes to check, download, and install updates

class ClientConfig(object):
    PUBLIC_KEY = 'Rbk396oV6YSKhJtYTZHGdu/z7P/Gom11LdqI/w3AlyQ'
    APP_NAME = 'SMS Event Log'
    COMPANY_NAME = 'SMS Equipment Inc.'
    HTTP_TIMEOUT = 30
    MAX_DOWNLOAD_RETRIES = 3
    UPDATE_URLS = ['https://smseventlog.s3.amazonaws.com']

class Updater(object):
    def __init__(self, mw=None, test_version=None, channel='stable'):
        try:
            client = Client(ClientConfig(), progress_hooks=[self.print_status_info])

            warnings.simplefilter('ignore', DeprecationWarning) # pyupdater turns this on, annoying

            _version = VERSION if test_version is None else test_version
            update_available = False
            app_update = None
            status = 'initialized'
        except:
            er.log_error(log=log, msg='Failed to initialize updater!')

        f.set_self(vars())

    def update_statusbar(self, msg):
        self.set_status(msg=msg)

        if not self.mw is None:
            self.mw.update_statusbar(msg)
        else:
            print(msg)
    
    def set_status(self, msg):
        self.status = msg
        log.info(msg)

    def get_app_update(self):
        client = self.client
        client.refresh() # download version info

        app_update = client.update_check(client.app_name, self.version, channel=self.channel)
        if not app_update is None:
            self.update_available = True
            self.app_update = app_update

        return app_update
    
    def check_update(self, **kw):
        app_update = self.get_app_update()
        self.update_statusbar(msg='Checking for update.')

        if self.update_available:
            self.update_statusbar(msg='Update available, download started.')

            # download can fail to rename '...zip.part' to '...zip' if zombie locking process exists
            fl.kill_sms_proc_locking(filename='zip')

            app_update.download() # background=True # don't need, already in a worker thread
            if app_update.is_downloaded():
                self.update_statusbar(msg=f'Update successfully downloaded. New version: {self.latest_version}')

                return self

        else:
            self.update_statusbar(msg=f'No update available. Current version: {self.version}')
        
    def install_update(self, restart=True):
        app_update = self.app_update
        if not app_update is None and app_update.is_downloaded():
            if restart:
                self.set_status(msg='Extracting update and restarting.')
                app_update.extract_restart()
            else:
                self.set_status(msg='Extracting on close without restart.')
                app_update.extract_overwrite()

    def print_finished(self):
        self.update_statusbar(msg='Download finished.')
    
    def print_failed(self, *args, **kw):
        self.update_statusbar(msg=f'Update failed at: {self.status}')
    
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

