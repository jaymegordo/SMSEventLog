from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.command import Command
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from . import functions as f


def tsi_form_vals():
    from . import eventlog as el
    from .dbmodel import EventLog

    serial, model = 'A40035', '980E-4'

    uid = 12608230555
    row = el.Row(keys=dict(UID=uid), dbtable=EventLog)
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
    def __init__(self, user):
        self.user = user
        self.pages = {}

    def create_driver(self, browser='Chrome'):
        if browser == 'Chrome':
            options = webdriver.ChromeOptions()
            if not f.is_win():
                chrome_profile = f'/Users/{self.user}/Library/Application Support/Google/Chrome/'
                options.add_argument(f'user-data-dir={chrome_profile}')
                options.add_argument('window-size=(1,1)')
            driver = webdriver.Chrome(options=options)
        else:
            driver = getattr(webdriver, browser)()

        return driver
    
    # @property
    def get_driver(self):
        if self._driver is None:
            self._driver = self.create_driver()
        else:
            try:
                # print('trying to execute STATUS')
                self._driver.execute(Command.STATUS) # check if driver is alive and attached
            except:
                try:
                    print('trying to reattach')
                    self._driver = attach_to_session(*get_driver_id(self._driver))
                except:
                    print('failed to reattach, creating new driver')
                    self._driver = self.create_driver()

        return self._driver

    def wait(self, time, cond):
        driver = self.get_driver()
        try:
            element = WebDriverWait(driver, time).until(cond)
            return element
        except:
            print(f'Failed waiting for: {cond}')
            return None

    def set_val(self, element, val):
        driver = self.get_driver()
        val = str(val).replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n')
        try:
            driver.execute_script("document.getElementById('{}').value='{}'".format(element.get_attribute('id'), val))
        except:
            print(f'couldn\'t set value: {val}')
            element.send_keys(val)
    
    def new_browser(self):
        driver = self.get_driver()
        driver.set_window_position(0, 0)
        driver.maximize_window()
    
    def current_page_name(self):
        # convert current url to nice page name
        pages_lookup = f.inverse(self.pages)
        url = self.get_driver().current_url.split('?')[0] # remove ? specific args
        # print(url)
        return pages_lookup.get(url, None)
    
    def current_page_index(self, page_order):
        # find index of current page name in given page order
        current_page = self.current_page_name()
        # print(f'current_page: {current_page}')
        i = page_order.index(current_page) if current_page in page_order else -1
        return i

class TSIWebPage(Web):
    def __init__(self, field_vals=None, serial=None, model=None, user='Jayme', _driver=None):
        super().__init__(user=user)
        tsi_number = None
        # _driver = None
        username, password = 'GordoJ3', '8\'Bigmonkeys'
        # serial, model = 'A40029', '980E-4'
        # TODO need to get this for other users, or just use default probably

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
            'all_tsi': f'{homepage}mytsi/',
        })
        f.set_self(self, vars())

    def open_tsi(self, serial=None, model=None, save_tsi=True):
        # open web browser and log in to tsi form
        if serial is None: serial = self.serial
        if model is None: model = self.model

        self.login_tsi(serial=serial, model=model)

        if not self.field_vals is None:
            self.fill_all_fields(field_vals=self.field_vals)

        self.fill_dropdowns()

        if save_tsi:
            driver = self.get_driver()

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
        driver = self.get_driver()
        for name, vals in self.form_dropdowns.items():
            id_, val = vals[0], vals[1]
            try:
                element = self.wait(10, EC.element_to_be_clickable((By.ID, id_)))
                Select(element).select_by_visible_text(val)
            except:
                f.send_error()
                print(f'Couldn\'t set dropdown value: {name}')
    
    def login_tsi(self, serial, model):
        driver = self.get_driver()
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
        for func_name in page_order:
            check_index = page_order.index(func_name)
            print(f'func_name: {func_name}, check_index: {check_index}, original_index: {original_index}')
            if check_index >= original_index:
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
