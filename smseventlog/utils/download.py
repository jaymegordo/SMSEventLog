import json

import requests

from .__init__ import *
from . import fileops as fl
from ..gui.dialogs import msgbox

log = getlog(__name__)

class Downloader(object):
    """Class to download files from internet"""    
    def __init__(self, mw=None, **kw):
        name = self.__class__.__name__

        gui = True if not mw is None else False
        p_ext = f.applocal / 'extensions'
        if not p_ext.exists():
            p_ext.mkdir(parents=True)
        
        f.set_self(vars())

    @property
    def exists(self):
        """Check if kaleido exe exists"""
        return self.p_root.exists()

    @staticmethod
    @er.errlog('Failed to download file.', err=True)
    def download_file(url: str, p_dest: Path) -> Path:
        """Download file and save to specified location.

        Parameters
        ----------
        url : str
            Download url\n
        p_save : Path\n
            Directory to save file
        
        Examples
        ---
        >>> url = 'https://github.com/plotly/Kaleido/releases/download/v0.0.3.post1/kaleido_mac.zip'
        >>> p_save = Path.home() / 'Desktop'
        >>> fl.download_file(url, p_save)
        """    

        name = url.split('/')[-1]
        p = p_dest / f'{name}'

        r = requests.get(url, stream=True, allow_redirects=True)
        r.raise_for_status()
        with open(p, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return p   

    def update_statusbar(self, msg):
        self.set_status(msg=msg)

        if not self.mw is None:
            self.mw.update_statusbar(msg)
        else:
            print(msg)
    
    def set_status(self, msg):
        self.status = msg
        log.info(msg)

class Gtk(Downloader):
    def __init__(self, **kw):
        super().__init__(**kw)
        url = 'https://chromedriver.storage.googleapis.com/86.0.4240.22/chromedriver_mac64.zip'
        p_root = self.p_ext / 'chromedriver'

        f.set_self(vars())
    
    def check(self):

        return self.exists
    
    def download_and_unpack(self):
        self.download_file(url=self.url, p_dst=self.p_root)
    
    def get_latest_url(self):
        # need to check current version of chrome
        chrome_ver = self.get_current_chrome_ver()

        return


class Kaleido(Downloader):
    """Downloader object to check for Kaleido executable and install if required"""
    def __init__(self, **kw):
        super().__init__(**kw)
        url_github = 'https://api.github.com/repos/plotly/Kaleido/releases/latest'
        p_dest = ''
        p_root = self.p_ext / 'kaleido'

        f.set_self(vars())
    
    def check(self):
        """Main function to call, check exe exists, dl if it doesnt"""
        if self.exists:
            return True # already exists, all good
        
        msg = f'Kaleido not found at: {self.p_root}.\n\n\
            The Kaleido extension is required to render charts to images in pdfs.\
            Would you like to download now? (report will not be created, try again after download).'
        
        # if not msgbox(msg, yesno=True):
        #     return
        # else:
        return self.download_and_unpack()
    
    def download_with_worker(self):
        if not self.mw is None:
            from ..gui.multithread import Worker

            Worker(func=self.download_and_unpack, mw=self.mw) \
                .add_signals(('result', dict(func=self.handle_dl_result))) \
                .start()

    def handle_dl_result(self, result=None):
        if not result is None:
            self.update_statusbar('Successfully downloaded and unpacked Kaleido')
        else:
            self.update_statusbar('Failed to downlaod Kaleido!')

    def download_and_unpack(self):
        url = self.get_latest_url()
        self.update_statusbar(f'Kaleido does not exist. Downloading from: {url}')

        p = self.download_file(url=url, p_dest=self.p_ext)
        if not p is None and p.exists():
            fl.unzip(p, delete=True)
            return True

    def get_latest_url(self):
        """Check github api for latest release of kaleido and return download url
        (Kaleido needed to render Plotly charts)"""
        m_platform = dict(
            mac=dict(
                ver_find='mac',
                fallback='https://github.com/plotly/Kaleido/releases/download/v0.0.3.post1/kaleido_mac.zip'),
            win=dict(
                ver_find='win_x64',
                fallback='https://github.com/plotly/Kaleido/releases/download/v0.0.3.post1/kaleido_win_x64.zip'))
        info = m_platform.get(f.platform)

        try:
            result = requests.get(self.url_github)
            m = json.loads(result.content)       

            # returns ~10 assets, filter to the one we want
            key = 'browser_download_url'
            lst = list(filter(lambda x: info['ver_find'] in x[key] and 'zip' in x[key], m['assets']))
            return lst[0][key]
        except:
            # fallback
            log.warning('Couldn\'t download latest release from Kaleido.')
            return info['fallback']