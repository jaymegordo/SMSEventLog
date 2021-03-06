import functools
import traceback
from PyQt5.QtCore import QGenericReturnArgument

import chromedriver_autoinstaller as cdi # checks and auto updates chromedriver version
from selenium import webdriver
from selenium.common.exceptions import (InvalidArgumentException,
                                        NoSuchElementException,
                                        NoSuchWindowException,
                                        WebDriverException)
from selenium.webdriver.common import keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from .__init__ import *
from .credentials import CredentialManager

log = getlog(__name__)

# make chrome not show console on windows
# https://stackoverflow.com/questions/33983860/hide-chromedriver-console-in-python
# https://www.zacoding.com/en/post/python-selenium-hide-console/

# find_element_by_class_name',
# 'find_element_by_css_selector',
# 'find_element_by_id',
# 'find_element_by_link_text',
# 'find_element_by_name',
# 'find_element_by_partial_link_text',
# 'find_element_by_tag_name',
# 'find_element_by_xpath',

# %config Completer.use_jedi = False # prevent vscode python interactive from calling @property when using intellisense

def any_of(*expected_conditions):
    """
    NOTE this is from selenium 3.141.59 which isn't on pypi yet. Putting the func here works fine

    An expectation that any of multiple expected conditions is true.
    Equivalent to a logical 'OR'.
    Returns results of the first matching condition, or False if none do. """
    def any_of_condition(driver):
        for expected_condition in expected_conditions:
            try:
                result = expected_condition(driver)
                if result:
                    return result
            except WebDriverException:
                pass
        return False
    return any_of_condition

def tsi_form_vals():
    from . import dbtransaction as dbt
    from .dbmodel import EventLog

    serial, model = 'A40035', '980E-4'

    uid = 12608230555
    row = dbt.Row(keys=dict(UID=uid), dbtable=EventLog)
    e = row.create_model_from_db()

    d = e.DateAdded.strftime('%-m/%-d/%Y')

    field_vals = {
        'Failure Date': d,
        'Repair Date': d,
        'Failure SMR': e.SMR,
        'Hours On Parts': e.ComponentSMR,
        'Serial': e.SNRemoved,
        'Part Number': e.PartNumber,
        'Part Name': e.TSIPartName,
        'New Part Serial': e.SNInstalled,
        'Work Order': e.WorkOrder,
        'Complaint': e.TSIDetails}
    
    return field_vals

class Web(object):
    def __init__(self, table_widget=None, mw=None, _driver=None, headless=False, use_user_settings=True, download_dir=None, **kw):
        pages = {}
        if not table_widget is None: mw = table_widget.mainwindow

        # if specific error, may need to exit with a nice message and suppress all else
        # NOTE loose end > may need a way to turn this back on if object is to be reused
        suppress_errors = False
        f.set_self(vars())

        er.wrap_all_class_methods_static(obj=self, err_func=self.e, exclude='driver')

    def e(self, func):
        # handle all errors in Web, allow suppression of errors if eg user closes window
        if self.suppress_errors:
            log.info(f'ignoring function: {func}')
            return

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except:
                if not self.suppress_errors:
                    raise
                else:
                    log.debug('error suppressed')
        
        return wrapper

    def update_statusbar(self, msg, *args, **kw):
        if not self.mw is None:
            self.mw.update_statusbar(msg, *args, **kw)
        else:
            log.warning(f'self.mainwindow is none, msg: {msg}')

    def get_options(self):
        # user-data-dir specifices the location of default chrome profile, to create browser with user's extensions, settings, etc
        options = webdriver.ChromeOptions()

        if self.use_user_settings:
            if f.is_mac():
                ext = 'Library/Application Support/Google/Chrome'
            else:
                ext = 'AppData/Local/Google/Chrome/User Data'

            chrome_profile = Path.home() / ext
            options.add_argument(f'user-data-dir={chrome_profile}')

        if self.headless:
            # options.headless = True
            options.add_argument('--headless')
            # options.add_argument('--no-sandbox')
            # options.add_argument('--disable-gpu')
        else:
            options.add_argument('window-size=(1,1)')

        # options.add_argument('--profile-directory=Default')
        
        # chrome://settings/content/pdfDocuments
        # cant use user settings with custom settings!!!!
        download_dir = self.__dict__.get('download_dir', Path.home() / 'Downloads')
        prefs = {
            # 'profile.default_content_settings.popups': 0,
            'plugins.always_open_pdf_externally': True,
            # 'plugins.plugins_disabled': ['Chrome PDF Viewer'],
            # "plugins.plugins_list": [{"enabled": False, "name": "Chrome PDF Viewer"}],
            # 'download.extensions_to_open': 'applications/pdf',
            'download.prompt_for_download': False,
            'download.default_directory': str(download_dir),
            'download.directory_upgrade': True}

        options.add_experimental_option('prefs', prefs)

        # disables the 'loading of internal extensions disabled by admin' warning, but stops window resizing
        options.add_experimental_option('useAutomationExtension', False)

        return options

    def create_driver(self, browser='Chrome'):

        def _create_driver(options=None):
            # kw = dict(executable_path=f.topfolder / 'selenium/webdriver/chromedriver') if SYS_FROZEN else {}

            # get path to chromedriver in eg extensions/chromedriver/86/chromedriver
            ver = cdi.utils.get_chrome_version()
            major_ver = cdi.utils.get_major_version(ver)
            exename = cdi.utils.get_chromedriver_filename() # chromedriver.exe
            p_exe = f.p_ext / f'chromedriver/{major_ver}/{exename}'

            # install chromedriver if doesnt exists for current version of chrome
            if not p_exe.exists():
                log.info(f'installing chromedriver: {p_exe}')
                cdi.install(p_install=f.p_ext / 'chromedriver')

            kw = dict(executable_path=p_exe)
            if f.is_win():
                # this didn't quite work
                # from selenium.webdriver.chrome.service import Service
                # from subprocess import CREATE_NO_WINDOW

                # service = Service(p_exe)
                # service.creationflags = CREATE_NO_WINDOW
                # kw['service'] = service
                # kw['executable_path'] = None
                kw['service_args'] = ['hide_console']

            return webdriver.Chrome(options=options, **kw)

        if browser == 'Chrome':
            options = self.get_options()

            try:
                driver = _create_driver(options=options)
            except InvalidArgumentException as e:
                log.debug('InvalidArgumentException\n' + traceback.format_exc())
                # user already has a chrome window open with default profile open
                # delete user-data-dir from options args and try again
                # NOTE try and quit the initial browser too > (kinda hard)
                # https://stackoverflow.com/questions/56585508/invalidargumentexception-message-invalid-argument-user-data-directory-is-alre
                
                for i, val in enumerate(options.arguments):
                    if 'user-data-dir' in val:
                        del options.arguments[i]
                        break

                driver = _create_driver(options=options)

        else:
            driver = getattr(webdriver, browser)()

        return driver
    
    def set_driver(self):
        self._driver = self.create_driver()

    def check_driver(self):
        if self._driver is None:
            self.set_driver()

        try:
            self._driver.title # check if driver is alive and attached
            self._driver.current_url
        except:
            log.debug('failed driver title check, setting driver again.')      
            self.set_driver()

    @property
    def driver(self):
        if self.suppress_errors: return None
        self.check_driver()

        # NOTE not sure if this actually works
        # try:
        #     self._driver = attach_to_session(*get_driver_id(self._driver))
        # except:
        #     # print('failed to reattach, creating new driver')
        #     self.set_driver()

        return self._driver
    
    def wait(self, time, cond, msg=None, raise_err=True):
        try:
            element = WebDriverWait(self.driver, time).until(method=cond, message=msg)
            return element
        except NoSuchWindowException:
            # user closed the window
            self.suppress_errors = True
            self._driver.quit()
            self.update_statusbar('User closed browser window, stopping execution.', warn=True)
        except Exception as e:
            if not raise_err:
                self.update_statusbar(msg, warn=True)
                return

            # add extra info to selenium's error message
            msg = f'\n\nFailed waiting for web element:'
            if hasattr(cond, 'locator'):
                msg = f'{msg} {cond.locator}'

            if hasattr(e, 'msg'):
                if not e.msg is None:
                    e.msg += msg
                else:
                    e.msg = msg
            else:
                log.warning(msg)
            raise

    def set_val(self, element, val, disable_check=False, send_enter=False, send_keys=False, **kw):
        driver = self.driver
        val = str(val).replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n')
            
        try:
            if send_keys:
                element.send_keys(val)
            else:
                driver.execute_script("document.getElementById('{}').value='{}'".format(element.get_attribute('id'), val))

            if send_enter:
                element.send_keys(Keys.ENTER) # date fields need an ENTER to set val properly

        except:
            log.warning(f'couldn\'t set value: {val}')
            if self.suppress_errors: return
            element.send_keys(val)
           
    def new_browser(self):
        driver = self.driver
        driver.set_window_position(0, 0)
        driver.maximize_window()
    
    def open_url_new_tab(self, url, switch=False):
        # Open a new window
        driver = self.driver
        driver.execute_script("window.open('');")
        # Switch to the new window and open URL B

        
        driver.switch_to.window(driver.window_handles[1])
        driver.get(url)

        # …Do something here
        # print("Current Page Title is : %s" %browser.title)
        # Close the tab with URL B
        # browser.close()
        # Switch back to the first tab with URL A
        driver.switch_to.window(driver.window_handles[0])
        # print("Current Page Title is : %s" %browser.title)

    def current_page_name(self):
        """Convert current url to nice page name"""
        pages_lookup = f.inverse(self.pages)
        url = self.driver.current_url.split('?')[0] # remove ? specific args
        return pages_lookup.get(url, None)
    
    def current_page_index(self, page_order):
        """Find index of current page name in given page order"""
        current_page = self.current_page_name()
        print(f'current_page: {current_page}')
        i = page_order.index(current_page) if current_page in page_order else -1
        return i

    def java_click(self, element):
        self.driver.execute_script("arguments[0].click();", element)

    def click_multi(self, vals, wait=10, by=None):
        """Click multi values, accepts dict or list of xpaths"""
        if by is None:
            by_defualt = By.CSS_SELECTOR
        else:
            by_defualt = by

        if not isinstance(vals, dict):
            # convert list of identifiers to click to dict
            vals = {key: by for key in vals}

        for key, val in vals.items():
            if not isinstance(val, dict):
                by = val
            else:
                # get by or other args from sub dict
                by = val.get('by', by_defualt)
                frame_name = val.get('iframe', None)
                
                # switch to iframe
                if frame_name:
                    self.driver.switch_to_frame(frame_name)

            element = self.wait(wait, EC.element_to_be_clickable((by, key)))
            self.java_click(element)
    
    def fill_multi(self, vals, wait=20, by=None, inv=False, **kw):
        """Fill multiple fields by key:value + selector
        
        Returns
        ------
        list : of elements found for further selecting if necessary
        """
        if by is None:
            by = By.XPATH
        
        # reverse dict
        if inv:
            vals = {v: k for k, v in vals.items()}

        elements = []
        for key, val in vals.items():
            element = self.wait(wait, EC.presence_of_element_located((by, key)))
            elements.append(element)
            self.set_val(element, val, **kw)
        
        return elements


class SuncorConnect(Web):
    # auto login to suncor's SAP system
    def __init__(self, ask_token=True, **kw):
        super().__init__(**kw)
        self.pages.update({'home': 'https://connect.suncor.com'})
        token = None

        username, password, token_pin = CredentialManager('sap').load()
        
        f.set_self(vars())
        if ask_token: self.set_token()

    def get_options(self):
        # need to trick Suncor Connect to thinking chrome is safari
        options = super().get_options()
        options.add_argument('--user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Safari/605.1.15"')

        return options

    def set_token(self):
        # get current RSA token before login
        # may want to ask during init or may not
        from ..gui import dialogs as dlgs
        ok, self.token = dlgs.inputbox(msg='Enter RSA token:')
        return ok

    def login(self):
        if self.token is None:
            if self.ask_token or not self.set_token(): return # cant login if token not set, dont ask twice

        driver = self.driver

        # TODO reuse existing driver/webpage if possible?
        self.new_browser()
        driver.get(self.pages['home'])

        element = driver.find_element_by_id('input_1')
        self.set_val(element, self.username)

        element = driver.find_element_by_id('input_2')
        self.set_val(element, self.password)

        element = driver.find_element_by_id('input_3')
        self.set_val(element, self.token_pin + self.token)

        element = driver.find_element_by_class_name('credentials_input_submit')
        element.send_keys(Keys.ENTER)

        # wait till page loaded

    def open_sap(self):
        driver = self.driver
        wait = self.wait

        if not 'vdesk/webtop' in driver.current_url:
            self.login()

        msg = 'Couldn\'t log in. Ensure password is correct.'
        element = wait(10, EC.presence_of_element_located(
            (By.XPATH, '/html/body/div[1]/div[2]/div[1]/span[13]/span[2]')), msg=msg, raise_err=False)
            
        if element is None: return
        element.click()

        # first click the popup window to make it active
        element = wait(2, EC.presence_of_element_located((By.CLASS_NAME, 'browserCitrix')))
        element.click()

        # SAP 760 button
        element = wait(30, EC.element_to_be_clickable(
            (By.XPATH, '/html/body/div[4]/div[3]/div/span[2]/span[2]')))
        if not element is None:
            element.click()
        else:
            log.warning('Failed to find "SAP Logon 760" button.')

        # citrix option > doesn't always come up
        try:
            element = wait(2, EC.presence_of_element_located(
                (By.XPATH, '/html/body/div[4]/div[3]/input[1]')))
            element.click()
        except:
            pass
        
        return self

class SuncorWorkRemote(Web):
    def __init__(self, ask_token=True, **kw):
        super().__init__(**kw)
        self.pages.update(dict(
            home='https://workremote.suncor.com',
            citrix='https://workremote.suncor.com/+CSCO+0075676763663A2F2F666861666F702E6668617062652E70627A++/Citrix/CitrxPRD-CGYWeb/'))
        token = None

        username, password, token_pin = CredentialManager('sap').load()
        
        f.set_self(vars())

    def open_sap(self):
        driver = self.driver
        self.new_browser()
        driver.get(self.pages['home'])

        login_creds = dict(
            username=self.username,
            password_input=self.password)
        self.fill_multi(vals=login_creds, by=By.ID)

        # 20s to accept Microsoft Authenticator prompt on phone after first btn
        btns = {
            'input[type=submit]': By.CSS_SELECTOR,
            'input[type=button]:nth-child(2)': By.CSS_SELECTOR,
            'Suncor Citrix': dict(iframe='content', by=By.PARTIAL_LINK_TEXT),
            'protocolhandler-welcome-installButton': By.ID,
            'protocolhandler-detect-alreadyInstalledLink': By.ID}

        self.click_multi(vals=btns, by=By.CSS_SELECTOR)

        # fill second login form
        login_creds = dict(
            username=self.username,
            password=self.password)
        self.fill_multi(vals=login_creds, by=By.ID)

        btns = {
            'loginBtn': By.ID,
            'SAP 760': By.PARTIAL_LINK_TEXT,
            'SAP Logon 760': By.PARTIAL_LINK_TEXT,
        }
        self.click_multi(vals=btns)

class Komatsu(Web):
    def __init__(self, **kw):
        super().__init__(**kw)

        username, password = CredentialManager('tsi').load()
        username_sms, password_sms = CredentialManager('sms').load() # need sms pw for new system

        if username is None or username_sms is None:
            from ..gui import dialogs as dlgs
            msg = 'Can\'t get TSI uesrname or password!'
            dlgs.msg_simple(msg=msg, icon='critical')
            is_init = False

        self.pages.update({
            'login': 'https://www.komatsuamerica.net/',})

        f.set_self(vars())

    def login_ka(self):
        """Login to main page (default to ka homepage, subclasses will overwrite)"""
        driver = self.driver
        driver.get(self.pages['login'])

        self.fill_multi(vals=dict(
            txtUserID=self.username,
            Password=self.password), by=By.ID, disable_check=True)

        driver.find_element_by_id('btnSubmit').submit()

class PSNDownload(Komatsu):
    """
    TODO make table in database
    TODO make upload func to add new psns not in db
    TODO Add table to EL
    TODO Add refresh func/menu
    TODO Add Download new menu (min date selection)
    TODO Make email new psns func
    """
    def __init__(self, days=14, use_user_settings=False, **kw):
        download_dir = f.drive / 'Regional/SMS West Mining/PSN/PSNs'

        super().__init__(use_user_settings=use_user_settings, download_dir=download_dir, **kw)

        startdate = (dt.now() + delta(days=days * -1)).strftime('%m/%d/%Y')

        self.pages.update({
            'login': 'https://www.komatsuamerica.net/northamerica/service/css/csslookup/psnlookup.aspx#',})

        f.set_self(vars())

    def search_psns(self):
        """Fill psn search page and load table of psns"""
        self.fill_multi(
            by=By.ID,
            vals=dict(tbIssueDate=self.startdate))

        # deselect All, select PSN/FN
        self.click_multi(
            by=By.ID,
            vals=['chkCategory_0', 'chkCategory_4', 'btnSearch'])
    
    def df_all_psns(self):
        """Loop all tables and concat dfs"""
        element = self.wait(10, EC.presence_of_element_located((By.CSS_SELECTOR, '#dgMain > tbody > tr.data')))
        pages = element.text.split(' ')
        dfs = []

        for page_num in pages:

            # first page is already selected
            if not page_num == '1':
                css = f'#dgMain > tbody > tr.data > td > a:nth-child({page_num})'
                element = self.driver.find_element_by_css_selector(css)
                element.click()
            
            dfs.append(self.df_psns())

        # TODO parse models list with json.dumps/loads
        return pd.concat(dfs)

    def df_psns(self):
        """Get df of psns info from table"""
        element = self.driver.find_element_by_css_selector('#dgMain')

        return pd.read_html(
                io=element.get_attribute('outerHTML'),
                header=0)[0] \
            .iloc[:-1, :6] \
            .pipe(f.lower_cols) \
            .pipe(f.parse_datecols) \
            .rename(columns=dict(reference_number='psn'))

    def download_all_psns(self, df=None):
        if df is None:
            df = self.df_all_psns()
        self.df = df

        psns = df.psn.unique().tolist()
        downloaded = []

        for psn in psns:
            p = self.download_dir / f'{psn}.pdf'
            if not p.exists():
                downloaded.append(psn)
                self.download_psn(psn)

        return downloaded

    def download_psn(self, psn):
        # url = f'https://www.komatsuamerica.net/northamerica/service/css/csslookup/viewpsn.aspx?psn={psn}.pdf'
        url = f'https://www.komatsuamerica.net/cssdocs/epsn/{psn}.pdf'
        # self.open_url_new_tab(url=url)
        self.driver.get(url)
        

class TSIWebPage(Komatsu):
    def __init__(self, field_vals={}, serial=None, model=None, table_widget=None, uid=None, docs=None, **kw):
        super().__init__(table_widget=table_widget, **kw)
        tsi_number = None
        is_init = True
        uploaded_docs = 0
        # serial, model = 'A40029', '980E-4'

        form_vals_default = {
            'Failed Part Qty': 1,
            'Cause': 'Uncertain.',
            'Correction': 'Component replaced with new.'}
        form_vals_default.update(field_vals)
        field_vals = form_vals_default.copy()

        form_fields = {
            'Unit': 'kom_titlesuffix',
            'Failure SMR': 'kom_failuresmr',
            'Hours On Parts': 'kom_hoursonpartsdecimal',
            'Failure Date': 'elogic_failuredate_datepicker_description',
            'Repair Date': 'kom_machinerepaircompletiondate_datepicker_description',
            'Part Number': 'kom_failedpartnumber',
            'Part Name': 'kom_failedpartname',
            'Serial': 'kom_failedcomponentserialnumber',
            'New Part Number': 'kom_replacedpartcomponentnumber',
            'New Part Serial': 'kom_replacedcomponentserialnumber',
            'Work Order': 'kom_distributorworkordernumber',
            'Complaint': 'kom_request',
            'Cause': 'kom_causeoffailure',
            'Correction': 'kom_correctionoffailure',
            'Notes': 'kom_additionalnotes',
            'Failed Part Qty': 'kom_failedpartquantity'}

        form_dropdowns = {
            'Country': ('kom_workingcountry', 'Canada'),
            'Altitude': ('kom_altitudecase', '1500(m) [5000(ft)] and below'),
            'Correction Task': ('kom_correctiontask', 'Replace'),
            'Application': ('elogic_machineapplication', 'Energy'),
            'Jobsite Material': ('kom_casejobsitematerialtype', 'Soil'),
            'Jobsite Function': ('kom_casemachinejobsitefunction', 'Carrying'),
            'Parts Returnable': ('kom_partsreturnable', 'No')}

        # https://komatsuna.microsoftcrmportals.com/en-US/tsi/
        homepage = 'https://komatsuna.microsoftcrmportals.com/en-US/'
        self.pages.update({
            'login': homepage,
            'home': homepage,
            'tsi_home': f'{homepage}tsi/',
            'tsi_create': f'{homepage}tsi-view/create-tsi-case/',
            'all_tsi': f'{homepage}mytsi/'})

        f.set_self(vars())

    def open_tsi(self, serial=None, model=None, save_tsi=True, submit_tsi=False, **kw):
        # open web browser and log in to tsi form
        if serial is None: serial = self.serial
        if model is None: model = self.model

        self.login_tsi(serial=serial, model=model)

        if not self.field_vals is None:
            self.fill_all_fields(field_vals=self.field_vals)

        self.fill_dropdowns()

        if save_tsi:
            driver = self.driver

            # press create button
            element = self.wait(20, EC.element_to_be_clickable((By.ID, 'InsertButton')))
            element.send_keys(Keys.SPACE)

            # wait for page to load, find TSI number at top of page and return
            element = self.wait(30, EC.presence_of_element_located((By.CLASS_NAME, 'breadcrumb'))) \
                .find_element_by_class_name('active')
            self.tsi_number = element.text

            # cant attach docs unless tsi is 'saved' first
            self.upload_attachments()
            
            if submit_tsi:
                self.submit_tsi()
        
        if self.suppress_errors: return None
        return self
    
    def upload_attachments(self):
        # also try wait for upload attachments link to load
        wait, docs = self.wait, self.docs
        if docs is None: return

        element = wait(30, EC.presence_of_element_located((By.LINK_TEXT, 'Upload Attachments')))
        element.send_keys(Keys.ENTER)

        # 'Other' button
        element = wait(20, EC.element_to_be_clickable(
            (By.XPATH, '/html/body/div[1]/div/div[3]/div/div/div[2]/div/div/div[1]/button[4]')))
        element.click()

        # loop docs and attach in dialog
        id_num_start = 30 # 'Other' Choose File buttons start at id=30
        for i, doc in enumerate(docs):
            if i > 7:
                log.warning('Can only attach max 8 files.')
                break
            
            try:
                element = wait(10, EC.presence_of_element_located(
                    (By.XPATH, f'//*[@id="{id_num_start + i}"]')))
                element.send_keys(doc)
            except:
                log.warning(f'Couldn\'t attach file: {doc}')
        
        # Upload Selected Files
        element = wait(10, EC.element_to_be_clickable(
            (By.ID, 'upload-modal-button')))
        element.click()

        # wait for confirmation alert to pop up
        alert_obj = wait(120, EC.alert_is_present(), msg='Timed out waiting for upload confirmation alert.')
        alert_obj.accept()
        self.uploaded_docs = len(docs)

    def fill_field(self, name, val):
        id_ = self.form_fields.get(name, None)

        if not id_ is None:
            try:
                element = self.wait(10, EC.element_to_be_clickable((By.ID, id_)))

                # date fields need to set text + press enter to set val properly
                send_enter = False if not 'date' in name.lower() else True

                self.set_val(element, val, send_enter=send_enter)
            except Exception as e:
                log.warning(f'Couldn\'t set field value: {name}, {val}, {e}')

    def fill_all_fields(self, field_vals=None):

        if field_vals is None:
            field_vals = self.field_vals

        for name, val in field_vals.items():
            self.fill_field(name, val)

            # try to wait and fill first element, then give up
            if not self.current_page_name() == 'tsi_create':
                log.warning(f'Not at tsi_create page, couldn\'t fill value: {name}, {val}')
                return

    def fill_dropdowns(self):
        for name, vals in self.form_dropdowns.items():
            id_, val = vals[0], vals[1]
            try:
                element = self.wait(10, EC.element_to_be_clickable((By.ID, id_)))
                Select(element).select_by_visible_text(val)
            except:
                log.warning(f'Couldn\'t set dropdown value: {name}')
    
    def tsi_home(self):
        self.login_tsi(max_page='home')
    
    def login_tsi(self, serial=None, model=None, max_page=None):
        driver = self.driver
        wait = self.wait
        page_order = ['login', 'home', 'tsi_home', 'tsi_create']

        # get name of current page
        # complete section if index of current page is less than index of name at current position

        def check_logged_in(login_item_id='lightbox'):
            """Wait for either a part of the login chain, or the machine quality info button"""

            element = wait(20, any_of(
                EC.presence_of_element_located((By.ID, login_item_id)),
                EC.presence_of_element_located((By.LINK_TEXT, 'MACHINE QUALITY INFORMATION')),
            ))
            
            # True if already logged in
            return 'machine' in element.text.lower()

        def login():
            # these elements exist on same url, harder to separate
            # self.login_ka()
            self.driver.get(self.pages['home'])

            # element = wait(60, EC.presence_of_element_located((By.LINK_TEXT, 'Go to (SQIS)TSR Portal')))
            # element.send_keys(Keys.ENTER)

            # this could either be login dialog ('Pick an account' OR 'sign in') OR straight to TSI homepage
            # need to check which dialog (by title) then either fill, or select from list
            # sign in\ncan’t access your account?\nsign-in options
            
            if check_logged_in('lightbox'):
                return

            element = wait(20, EC.text_to_be_present_in_element((By.ID, 'lightbox'), 'account'))
            element = wait(20, EC.presence_of_element_located((By.ID, 'lightbox')))

            if 'pick an account' in element.text.lower():
                # acccount already saved, select it
                self.click_multi(vals=[f'//*[text() = "{self.username_sms}"]'], by=By.XPATH)
            else:
                # account not saved, fill it in
                self.fill_multi(vals=dict(i0116=self.username_sms), by=By.ID, send_keys=True)
                self.click_multi(vals=['idSIButton9'], by=By.ID) # submit button

            if check_logged_in('userNameInput'):
                return

            self.fill_multi(vals=dict(
                userNameInput=self.username_sms,
                passwordInput=self.password_sms), by=By.ID)
            self.click_multi(vals=['submitButton'], by=By.ID)

            # WAIT for authenticator/other sign in here

            # Stay signed in dialog / dontshowagain checkbox
            # NOTE probably doesn't need to be in try/except now
            try:
                log.info('Waiting 60s for staySignedIn dialog')
                if check_logged_in('KmsiCheckboxField'):
                    return

                element = self.wait(60, EC.element_to_be_clickable((By.ID, 'KmsiCheckboxField')))
                if not element.is_selected():
                    element.click()

                self.click_multi(vals=['idSIButton9'], by=By.ID)
            except:
                log.info('No "stay signed in" dialog.')
                pass

            
        def home():
            """Press MACHINE QUALITY INFORMATION button
            - NOTE could also just login to this page but would have to rewrite the "logged in" check"""         
            element = wait(60, EC.presence_of_element_located((By.LINK_TEXT, 'MACHINE QUALITY INFORMATION')))
            element.send_keys(Keys.ENTER)
      
        def tsi_home():
            # enter serial number
            if serial is None: raise AttributeError('Serial number missing!')
            element = wait(30, EC.presence_of_element_located((By.ID, 'serialNumberCreate')))
            element.send_keys(serial) # need to send keys here for some reason
            element.send_keys(Keys.ENTER)

            # wait for model options to be populated then select correct model
            element = wait(10, EC.element_to_be_clickable((By.ID, 'modelCreate')))
            Select(element).select_by_visible_text(model)

            element = wait(10, EC.element_to_be_clickable((By.ID, 'buttonCreateTsi')))
            element.send_keys(Keys.SPACE)

        def tsi_create():
            # probably not necessary
            element = wait(10, EC.presence_of_element_located((By.ID, 'InsertButton')))
            
            # wait for KA to populate serial number before filling dropdowns
            element = wait(30, EC.text_to_be_present_in_element_value((By.ID, 'elogic_serialnumber'), serial))

        # check where current page is in order of pages we need to log in, then complete funcs from there
        original_index = self.current_page_index(page_order)
        max_index = page_order.index(max_page) if max_page is not None and max_page in page_order else 10
        for func_name in page_order:
            check_index = page_order.index(func_name)
            # print(f'func_name: {func_name}, check_index: {check_index}, original_index: {original_index}')
            if check_index >= original_index and check_index <= max_index:
                
                # loop funcs in login steps
                vars().get(func_name)()
    
    def submit_tsi(self):
        # not used yet
        element = self.wait(30, EC.element_to_be_clickable((By.ID, 'SendForApproval')))
        element.click()

        self.update_statusbar(f'TSI Submitted: {self.tsi_number}', success=True)


def attach_to_session(executor_url, session_id):
    original_execute = WebDriver.execute
    def new_command_execute(self, command, params=None):
        if command == "newSession":
            # Mock the response
            return {'success': 0, 'value': None, 'sessionId': session_id}
        else:
            return original_execute(self, command, params)
    # Patch the function before creating the driver object
    WebDriver.execute = new_command_execute
    driver = webdriver.Remote(command_executor=executor_url, desired_capabilities={})
    driver.session_id = session_id

    # Replace the patched function with original function
    WebDriver.execute = original_execute
    return driver

def get_driver_id(driver):
    executor_url = driver.command_executor._url
    session_id = driver.session_id

    return executor_url, session_id

def tsi_example(docs=None):
    from ..dbtransaction import example
    uid = 101133020820
    e = example(uid=uid)
    serial, model = 'A40048', '980E-4'
    d = e.DateAdded.strftime('%m/%d/%Y')

    field_vals = {
        'Failure Date': d,
        'Repair Date': d,
        'Failure SMR': e.SMR,
        'Hours On Parts': e.ComponentSMR,
        'Serial': e.SNRemoved,
        'Part Number': e.PartNumber,
        'Part Name': e.TSIPartName,
        'New Part Serial': e.SNInstalled,
        'Work Order': e.WorkOrder,
        'Complaint': e.Title,
        'Cause': e.FailureCause,
        'Notes': e.Description}
        
    tsi = TSIWebPage(
        field_vals=field_vals,
        serial=serial,
        model=model,
        uid=e.UID,
        docs=docs)

    return tsi
