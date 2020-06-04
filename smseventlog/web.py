from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.remote.webdriver import WebDriver

from . import functions as f

class TSIWebPage():
    def __init__(self, form_vals=None, serial=None, model=None):
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
            'Notes': 'kom_additionalnotes'}

        form_dropdowns = {
            'Country': ('kom_workingcountry', 'Canada'),
            'Altitude': ('kom_altitudecase', '1500(m) [5000(ft)] and below'),
            'Correction Task': ('kom_correctiontask', 'Replace'),
            'Application': ('elogic_machineapplication', 'Energy'),
            'Jobsite Material': ('kom_casejobsitematerialtype', 'Soil'),
            'Jobsite Function': ('kom_casemachinejobsitefunction', 'Carrying'),
            'Parts Returnable': ('kom_partsreturnable', 'No')}

        f.set_self(self, vars())

    def open_tsi(self, serial=None, model=None):
        # open web browser and log in to tsi form
        if serial is None: serial = self.serial
        if model is None: model = self.model

        self.driver = self.login_tsi(serial=serial, model=model)  

        if not self.form_vals is None:
            self.fill_forms(form_vals=self.form_vals)

        self.fill_dropdowns()
        
        return self.driver

    def fill_forms(self, form_vals=None):
        if form_vals is None:
            form_vals = self.form_vals

        for name, val in form_vals.items():
            id_ = self.form_fields.get(name, None)

            if not id_ is None:
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.ID, id_)))
                    # element = self.driver.find_element_by_id(id_)
                    element.click()
                    element.send_keys(val)
                except:
                    print(f'Couldn\'t set field value: {name}')

    def fill_dropdowns(self):
        for name, vals in self.form_dropdowns.items():
            id_, val = vals[0], vals[1]
            try:
                element = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, id_))) #presence_of_element_located
                element.click() # need to click to make element active
                Select(element).select_by_visible_text(val)
            except:
                f.send_error()
                print(f'Couldn\'t set dropdown value: {name}')
    
    def login_tsi(self, serial=None, model=None, browser='Safari'):
        driver = getattr(webdriver, browser)()
        driver.set_window_position(0, 0)
        driver.maximize_window()
        driver.get('https://www.komatsuamerica.net/northamerica/kirc/tsr2/')

        username = driver.find_element_by_id('txtUserID')
        password = driver.find_element_by_id('Password')

        username.send_keys('GordoJ3')
        password.send_keys("8'Bigmonkeys")

        driver.find_element_by_id('btnSubmit').submit()

        try:
            sqis_text = 'Go to (SQIS)TSR Portal'
            element = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.LINK_TEXT, sqis_text)))
            element.send_keys("\n")
            
            tsi_btn_text = 'MACHINE QUALITY INFORMATION'
            element = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.LINK_TEXT, tsi_btn_text)))
            element.send_keys("\n")

            # enter serial number
            serial_num = 'serialNumberCreate'
            element = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, serial_num)))
            element.send_keys(serial)
            element.send_keys('\n')

            # wait for model options to be populated then select correct model
            model_create = 'modelCreate'
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, model_create)))

            Select(element).select_by_visible_text(model)

            button_create = 'buttonCreateTsi'
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, button_create)))
            element.send_keys(Keys.SPACE)

            element = WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.ID, 'InsertButton')))

        except:
            f.send_error()

        return driver

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