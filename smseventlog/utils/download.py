import json
import shutil

import requests
from packaging.version import parse as parse_version

from ..gui.dialogs import msgbox
from . import fileops as fl
from .__init__ import *

log = getlog(__name__)

class Downloader(object):
    """Class to download files from internet"""    
    def __init__(self, mw=None, v_min=None, **kw):
        name = self.__class__.__name__

        # create version obj for comparisons
        if not v_min is None:
            # make sure '0.1.0' instead of '0.1.0.post1'
            v_min = parse_version(parse_version(v_min).base_version)

        gui = True if not mw is None else False
        p_ext = f.applocal / 'extensions'
        if not p_ext.exists():
            p_ext.mkdir(parents=True)
        
        f.set_self(vars())

    @property
    def exists(self):
        """Check if kaleido exe exists"""
        return self.p_root.exists()
    
    @property
    @er.errlog('Version file doesn\'t exist', err=False, warn=True, default=False)
    def version_good(self):
        """Check if current installed version is up to date with self.v_min
        - NOTE this works for kaleido but may not for others
        """

        with open(self.p_root / 'version', 'r+') as file:
           v_cur = parse_version(file.readline())

        log.info(f'{self.__class__.__name__} - Existing ver: {v_cur}, minimum ver: {self.v_min}')
        
        return v_cur >= self.v_min

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
        >>> url = 'https://github.com/plotly/Kaleido/releases/download/v0.1.0/kaleido_mac.zip'
        >>> p_save = Path.home() / 'Desktop'
        >>> fl.download_file(url, p_save)
        """    

        name = url.split('/')[-1]
        p = p_dest / f'{name}'

        print(p_dest.exists(), p_dest)
        if not p_dest.exists():
            p_dest.mkdir(parents=True)

        r = requests.get(url, stream=True, allow_redirects=True)
        r.raise_for_status()
        with open(p, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return p   

    def update_statusbar(self, msg, *args, **kw):
        self.set_status(msg=msg, *args, **kw)

        if not self.mw is None:
            self.mw.update_statusbar(msg)
        else:
            print(msg)
    
    def set_status(self, msg):
        self.status = msg
        log.info(msg)

class Gtk(Downloader):
    """NOTE not finished!!"""
    def __init__(self, **kw):
        super().__init__(**kw)
        url_github = 'https://api.github.com/repos/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/latest'
        p_root = self.p_ext / 'gtk'

        f.set_self(vars())
    
    def check(self):

        return self.exists
    
    def download_and_unpack(self):
        self.download_file(url=self.url, p_dst=self.p_root)
    
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


class Kaleido(Downloader):
    """Downloader object to check for Kaleido executable and install if required"""
    def __init__(self, **kw):
        import kaleido as kal
        super().__init__(v_min=kal.__version__, **kw)
        # url_github = 'https://api.github.com/repos/plotly/Kaleido/releases/latest' # not used now
        p_dest = ''
        p_root = self.p_ext / 'kaleido'

        f.set_self(vars())
    
    def check(self):
        """Main function to call, check exe exists, dl if it doesnt"""

        if self.exists and self.version_good:
            return True # already exists, all good
        else:
            return self.download_and_unpack(remove_old=True)
    
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
            self.update_statusbar('Warning: Failed to downlaod Kaleido!')

    def download_and_unpack(self, remove_old=False):
        url = self.get_latest_url()
        self.update_statusbar(f'Kaleido (for rendering images in reports) does not exist or needs to be updated. Downloading from: {url}')
        log.info(f'Downloading new Kaleido package from: {url}')

        if remove_old and self.p_root.exists():
            log.info(f'removing outdated kaleido dir: {self.p_root}')
            shutil.rmtree(self.p_root)

        p = self.download_file(url=url, p_dest=self.p_root)
        if not p is None and p.exists():
            fl.unzip(p, delete=True)
            log.info(f'Kaleido downloaded successfully to: {p}')
            return True

    def get_latest_url(self):
        """Check github api for latest release of kaleido and return download url
        (Kaleido needed to render Plotly charts)"""
        # key 'name' = 'v0.1.0.post1' from gh api data
        m_platform = dict(
            mac=dict(
                ver_find='mac',
                name='kaleido_mac.zip'),
            win=dict(
                ver_find='win_x64',
                name='kaleido_win_x64.zip'))
        info = m_platform.get(f.platform)

        # base_version to exclude '.post1' for now
        info['fallback'] = f'https://github.com/plotly/Kaleido/releases/download/v{self.v_min.base_version}/{info["name"]}'

        # just going to download explicit version to match current kaleido version in package
        # try:
        #     result = requests.get(self.url_github)
        #     m = json.loads(result.content)

        #     # returns ~10 assets, filter to the one we want
        #     key = 'browser_download_url'
        #     lst = list(filter(lambda x: info['ver_find'] in x[key] and 'zip' in x[key], m['assets']))
        #     return lst[0][key]
        # except:
        #     # fallback
        #     log.warning('Couldn\'t download latest release from Kaleido.')
        return info['fallback']
