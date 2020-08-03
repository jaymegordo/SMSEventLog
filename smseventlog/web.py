from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.common.exceptions import InvalidArgumentException

from . import functions as f
from .__init__ import *
# find_element_by_class_name',
# 'find_element_by_css_selector',
# 'find_element_by_id',
# 'find_element_by_link_text',
# 'find_element_by_name',
# 'find_element_by_partial_link_text',
# 'find_element_by_tag_name',
# 'find_element_by_xpath',

# %config Completer.use_jedi = False # prevent vscode python interactive from calling @property when using intellisense

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
    def __init__(self):
        pages = {}
        _driver = None
        f.set_self(vars())

    def get_options(self):
        # user-data-dir specifices the location of default chrome profile, to create browser with user's extensions, settings, etc
        options = webdriver.ChromeOptions()

        if f.is_mac():
            ext = 'Library/Application Support/Google/Chrome'
        elif f.is_win():
            ext = 'AppData/Local/Google/Chrome/User Data'

        chrome_profile = Path.home() / ext
        options.add_argument(f'user-data-dir={chrome_profile}')
        options.add_argument('window-size=(1,1)')
        # options.add_argument('--profile-directory=Default')
        
        prefs = {'profile.default_content_settings.popups': 0,
                'download.prompt_for_download': False,
                'download.default_directory': str(Path.home() / 'Downloads'),
                'directory_upgrade': True}
        options.add_experimental_option('prefs', prefs)

        return options

    def create_driver(self, browser='Chrome'):
        def _create_driver(options=None):
            kw = dict(executable_path=f.topfolder / 'selenium/webdriver/chromedriver') if f.frozen else {}
            return webdriver.Chrome(options=options, **kw)

        if browser == 'Chrome':
            options = self.get_options()

            try:
                driver = _create_driver(options=options)
            except InvalidArgumentException:
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
    
    def check_driver(self):
        if self._driver is None:
            self.set_driver()

        try:
            self._driver.title # check if driver is alive and attached
            self._driver.current_url
        except:        
            self.set_driver()

    @property
    def driver(self):
        self.check_driver()

        # NOTE not sure if this actually works
        # try:
        #     self._driver = attach_to_session(*get_driver_id(self._driver))
        # except:
        #     # print('failed to reattach, creating new driver')
        #     self.set_driver()

        return self._driver
    
    def set_driver(self):
        self._driver = self.create_driver()

    def wait(self, time, cond):
        driver = self.driver
        try:
            element = WebDriverWait(driver, time).until(cond)
            return element
        except:
            # f.send_error()
            print(f'Failed waiting for: {cond}')
            return None

    def set_val(self, element, val):
        driver = self.driver
        val = str(val).replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n')
        try:
            driver.execute_script("document.getElementById('{}').value='{}'".format(element.get_attribute('id'), val))
        except:
            print(f'couldn\'t set value: {val}')
            element.send_keys(val)
        
        # TODO check val was set, if not, try again using send_keys(val)
    
    def new_browser(self):
        driver = self.driver
        driver.set_window_position(0, 0)
        driver.maximize_window()
    
    def current_page_name(self):
        # convert current url to nice page name
        pages_lookup = f.inverse(self.pages)
        url = self.driver.current_url.split('?')[0] # remove ? specific args
        # print(url)
        return pages_lookup.get(url, None)
    
    def current_page_index(self, page_order):
        # find index of current page name in given page order
        current_page = self.current_page_name()
        # print(f'current_page: {current_page}')
        i = page_order.index(current_page) if current_page in page_order else -1
        return i

class SuncorConnect(Web):
    # auto login to suncor's SAP system
    def __init__(self):
        super().__init__()
        self.pages.update({'home': 'https://connect.suncor.com'})

        user = Path.home().name
        if user == 'Jayme':
            self.username = 'jagordon'
            self.password = 'SMSrel0)'
            self.token_pin = '1234'

    def get_options(self):
        # need to trick Suncor Connect to thinking chrome is safari
        options = super().get_options()
        options.add_argument('--user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Safari/605.1.15"')

        return options

    def login(self):
        # get rsa fob
        from .gui import dialogs as dlgs

        # get current RSA token before login
        ok, token = dlgs.inputbox(msg='Enter RSA token:')
        if not ok: return

        driver = self.driver

        # TODO reuse existing driver/webpage if possible?
        self.new_browser()
        driver.get(self.pages['home'])

        element = driver.find_element_by_id('input_1')
        self.set_val(element, self.username)

        element = driver.find_element_by_id('input_2')
        self.set_val(element, self.password)

        element = driver.find_element_by_id('input_3')
        self.set_val(element, self.token_pin + token)

        element = driver.find_element_by_class_name('credentials_input_submit')
        element.send_keys(Keys.ENTER)

        # wait till page loaded

    def open_sap(self):
        driver = self.driver
        wait = self.wait

        if not 'vdesk/webtop' in driver.current_url:
            self.login()

        element = wait(10, EC.presence_of_element_located(
            (By.XPATH, '/html/body/div[1]/div[2]/div[1]/span[13]/span[2]')))
        element.click()

        # first click the popup window to make it active
        element = wait(2, EC.presence_of_element_located((By.CLASS_NAME, 'browserCitrix')))
        element.click()

        element = wait(30, EC.presence_of_element_located(
            (By.XPATH, '/html/body/div[4]/div[3]/div/span[2]/span[2]')))
        element.click()

        # citrix option > doesn't always come up
        try:
            element = wait(2, EC.presence_of_element_located(
                (By.XPATH, '/html/body/div[4]/div[3]/input[1]')))
            element.click()
        except:
            pass
        
        # driver.close()

class TSIWebPage(Web):
    def __init__(self, field_vals={}, serial=None, model=None, _driver=None, parent=None):
        super().__init__()
        tsi_number = None
        is_init = True
        # serial, model = 'A40029', '980E-4'

        # try loading username + pw from QSettings if running in app
        if not parent is None:
            username, password = parent.mainwindow.get_tsi_username()

            if username is None:
                from .gui import dialogs as dlgs
                msg = 'Can\'t get TSI uesrname or password!'
                dlgs.msg_simple(msg=msg, icon='critical')
                is_init = False

        else: # get from command line
            username, password = input('Username:'), input('Password:')

        form_vals_default = {
            'Failed Part Qty': 1,
            'Cause': 'Uncertain.',
            'Correction': 'Component replaced with new.'}
        field_vals.update(form_vals_default)

        form_fields = {
            'Failure SMR': 'elogic_machinesmr',
            'Failure Date': 'elogic_failuredate_datepicker_description',
            'Repair Date': 'kom_machinerepaircompletiondate_datepicker_description',
            'Hours On Parts': 'kom_hoursonparts',
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

        homepage = 'https://komatsuna.microsoftcrmportals.com/en-US/'
        self.pages.update({
            'login': 'https://www.komatsuamerica.net/northamerica/kirc/tsr2/',
            'home': homepage,
            'tsi_home': f'{homepage}tsi/',
            'tsi_create': f'{homepage}tsi-view/create-tsi-case/',
            'all_tsi': f'{homepage}mytsi/'})

        f.set_self(vars())

    def open_tsi(self, serial=None, model=None, save_tsi=True):
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
        
    def fill_field(self, name, val):
        id_ = self.form_fields.get(name, None)

        if not id_ is None:
            try:
                element = self.wait(10, EC.element_to_be_clickable((By.ID, id_)))
                # element = self.driver.find_element_by_id(id_)
                # element.click()
                # element.send_keys(val)
                self.set_val(element, val)
            except:
                f.send_error()
                print(f'Couldn\'t set field value: {name, val}')

        return

    def fill_all_fields(self, field_vals=None):

        if field_vals is None:
            field_vals = self.field_vals

        for name, val in field_vals.items():
            self.fill_field(name, val)

            # try to wait and fill first element, then give up
            if not self.current_page_name() == 'tsi_create':
                print('not at tsi_create page')
                return

    def fill_dropdowns(self):
        driver = self.driver
        for name, vals in self.form_dropdowns.items():
            id_, val = vals[0], vals[1]
            try:
                element = self.wait(10, EC.element_to_be_clickable((By.ID, id_)))
                Select(element).select_by_visible_text(val)
            except:
                f.send_error()
                print(f'Couldn\'t set dropdown value: {name}')
    
    def tsi_home(self):
        self.login_tsi(max_page='home')
    
    def login_tsi(self, serial=None, model=None, max_page=None):
        driver = self.driver
        wait = self.wait
        page_order = ['login', 'home', 'tsi_home', 'tsi_create']

        # get name of current page
        # complete section if index of current page is less than index of name at current position

        def login():
            # these elements exist on same url, harder to separate
            self.new_browser()
            driver.get(self.pages['login'])

            # TODO save/load user pw from QSettings
            try:
                element = driver.find_element_by_id('txtUserID')
                self.set_val(element, self.username)
                
                element = driver.find_element_by_id('Password')
                self.set_val(element, self.password)

                driver.find_element_by_id('btnSubmit').submit()
            finally:
                element = wait(60, EC.presence_of_element_located((By.LINK_TEXT, 'Go to (SQIS)TSR Portal')))
                element.send_keys(Keys.ENTER)

        def home():            
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
            
            # also try wait for upload attachments link to load
            # element = wait(30, EC.presence_of_element_located((By.LINK_TEXT, 'Upload Attachments')))

        # check where current page is in order of pages we need to log in, then complete funcs from there
        original_index = self.current_page_index(page_order)
        max_index = page_order.index(max_page) if max_page is not None and max_page in page_order else 10
        for func_name in page_order:
            check_index = page_order.index(func_name)
            # print(f'func_name: {func_name}, check_index: {check_index}, original_index: {original_index}')
            if check_index >= original_index and check_index <= max_index:
                vars().get(func_name)()


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
