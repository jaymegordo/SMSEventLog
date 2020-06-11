from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.remote.webdriver import WebDriver

from . import functions as f

class Web(object):
    def __init__(self, user):
        self.user = user

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

        return self._driver

    def wait(self, time, cond):
        driver = self.get_driver()
        element = WebDriverWait(driver, time).until(cond)
        return element

    def set_val(self, element, val):
        driver = self.get_driver()
        val = str(val).replace("'", "\\'")
        driver.execute_script("document.getElementById('{}').value='{}'".format(element.get_attribute('id'), val))

class TSIWebPage(Web):
    def __init__(self, form_vals=None, serial=None, model=None, user='Jayme'):
        super().__init__(user=user)
        tsi_number = None
        _driver = None
        username, password = 'GordoJ3', '8\'Bigmonkeys'
        # serial, model = 'A40029', '980E-4'
        # TODO need to get this for other users, or just use default probably

        form_vals_default = {
            'Failed Part Qty': 1,
            'Cause': 'Uncertain.',
            'Correction': 'Component replaced with new.'}
        form_vals.update(form_vals_default)

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

        homepage = 'https://komatsuna.microsoftcrmportals.com/en-US'
        pages = {
            'tsi_home': f'{homepage}/tsi/',
            'all_tsi': f'{homepage}/mytsi/'
        }
        f.set_self(self, vars())

    def open_tsi(self, serial=None, model=None, save_tsi=True):
        # open web browser and log in to tsi form
        if serial is None: serial = self.serial
        if model is None: model = self.model

        self.login_tsi(serial=serial, model=model)

        if not self.form_vals is None:
            self.fill_forms(form_vals=self.form_vals)

        self.fill_dropdowns()

        if save_tsi:
            driver = self.get_driver()

            # press create button
            element = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, 'InsertButton')))
            element.send_keys(Keys.SPACE)

            # wait for page to load, find TSI number at top of page and return
            element = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'breadcrumb'))) \
                .find_element_by_class_name('active')
            self.tsi_number = element.text

    def fill_forms(self, form_vals=None):
        if form_vals is None:
            form_vals = self.form_vals

        for name, val in form_vals.items():
            id_ = self.form_fields.get(name, None)
            driver = self.get_driver()

            if not id_ is None:
                try:
                    element = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, id_)))
                    # element = self.driver.find_element_by_id(id_)
                    # element.click()
                    # element.send_keys(val)
                    self.set_val(element, val)
                except:
                    f.send_error()
                    print(f'Couldn\'t set field value: {name}')

    def fill_dropdowns(self):
        driver = self.get_driver()
        for name, vals in self.form_dropdowns.items():
            id_, val = vals[0], vals[1]
            try:
                element = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, id_))) #presence_of_element_located
                # element.click() # need to click to make element active
                Select(element).select_by_visible_text(val)
            except:
                f.send_error()
                print(f'Couldn\'t set dropdown value: {name}')
    
    def login_tsi(self, serial, model):
        driver = self.get_driver()
        driver.set_window_position(0, 0)
        driver.maximize_window()
        driver.get('https://www.komatsuamerica.net/northamerica/kirc/tsr2/')
        wait = self.wait

        # TODO save/load user pw from QSettings
        element = driver.find_element_by_id('txtUserID')
        self.set_val(element, self.username)
        
        element = driver.find_element_by_id('Password')
        self.set_val(element, self.password)

        driver.find_element_by_id('btnSubmit').submit()

        try:
            element = wait(60, EC.presence_of_element_located((By.LINK_TEXT, 'Go to (SQIS)TSR Portal')))
            element.send_keys(Keys.ENTER)
            
            element = wait(60, EC.presence_of_element_located((By.LINK_TEXT, 'MACHINE QUALITY INFORMATION')))
            element.send_keys(Keys.ENTER)

            # enter serial number
            element = wait(30, EC.presence_of_element_located((By.ID, 'serialNumberCreate')))
            element.send_keys(serial) # need to send keys here for some reason
            element.send_keys(Keys.ENTER)

            # wait for model options to be populated then select correct model
            element = wait(10, EC.element_to_be_clickable((By.ID, 'modelCreate')))
            Select(element).select_by_visible_text(model)

            element = wait(10, EC.element_to_be_clickable((By.ID, 'buttonCreateTsi')))
            element.send_keys(Keys.SPACE)

            # probably not necessary
            element = wait(10, EC.presence_of_element_located((By.ID, 'InsertButton')))
            
            # wait for KA to populate serial number before filling dropdowns
            element = wait(30, EC.text_to_be_present_in_element_value((By.ID, 'elogic_serialnumber'), serial))
            
            # also try wait for upload attachments link to load
            element = wait(30, EC.presence_of_element_located((By.LINK_TEXT, 'Upload Attachments')))

        except:
            f.send_error()


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