from . import _global as gbl
from . import dialogs as dlgs
from . import tables as tbls
from .__init__ import *
from .multithread import Worker
from . import multithread as mlt
from .update import Updater
from .credentials import CredentialManager

log = logging.getLogger(__name__)

# FEATURES NEEDED
# TODO Keyboard shortcuts > ctrl + down, right
# TODO green 'flash' for user confirmation value updated in db
# TODO save previous query and run when tab first selected

class MainWindow(QMainWindow):
    minesite_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(gbl.title)
        self.setMinimumSize(QSize(1000, 400))
        self.minesite_changed.connect(self.update_minesite_label)
        self.status_label = QLabel() # permanent label for status bar so it isnt changed by statusTips
        self.statusBar().addPermanentWidget(self.status_label)

        # Settings
        s = QSettings('sms', 'smseventlog')
        self.resize(s.value('window size', defaultValue=QSize(1200, 1000)))
        self.move(s.value('window position', defaultValue=QPoint(50, 50)))
        self.minesite = s.value('minesite', defaultValue='FortHills')
        self.settings = s

        self.create_actions()
        self.create_menu()

        tabs = TabWidget(self)
        self.setCentralWidget(tabs)
        tabs.setCurrentIndex(tabs.get_index(title=s.value('active table', 'Event Log')))
        self.update_minesite_label()

        self.tabs = tabs

        self.threadpool = QThreadPool()
    
    @property
    def minesite(self):
        return self._minesite

    @minesite.setter
    def minesite(self, val):
        self._minesite = val
        self.minesite_changed.emit(val)
    
    def update_minesite_label(self, *args):
        # status_label is special label to always show current minesite (bottom right)
        self.status_label.setText(f'Minesite: {self.minesite}')
    
    def update_statusbar(self, msg=None, *args):
        # statusbar shows temporary messages that disappear on any context event
        if not msg is None:
            self.statusBar().showMessage(msg)

    def after_init(self):
        # TODO: need to show window first, then show loading message
        self.username = self.get_username()
        self.init_sentry()
        self.active_table_widget().refresh(default=True)

        self.u = users.User(username=self.username, mainwindow=self).login()

        # initialize updater
        # test_version = '3.0.4'
        test_version = None
        self.updater = Updater(test_version=test_version, mw=self)

        self.check_update()
        self.start_update_timer()
    
    def start_update_timer(self, mins=180):
        # check for updates every 3 hrs
        if not SYS_FROZEN: return

        msec = mins * 60 * 1000

        self.update_timer = QTimer(parent=self)
        self.update_timer.timeout.connect(self.check_update)
        self.update_timer.start(msec)

    def check_update(self):
        # check for update and download in a worker thread

        if not SYS_FROZEN:
            self.update_statusbar('App not frozen, not checking for updates.')
            return

        if self.updater.update_available:
            # update has been previously checked and downloaded but user declined to install initially
            self._install_update(updater=self.updater)
        else:
            Worker(func=self.updater.check_update, mw=self) \
                .add_signals(signals=('result', dict(func=self._install_update))) \
                .start()
    
    def _install_update(self, updater=None, ask_user=True):
        if updater is None: return

        # prompt user to install update and restart
        msg = f'An updated version of the Event Log is available.\n\n\
            Current: {updater.version}\n\
            Latest: {updater.latest_version}\n\n\
            Would you like to restart and update now?'

        if ask_user:
            if not dlgs.msgbox(msg=msg, yesno=True): return

        Worker(func=updater.install_update, mw=self).start()
        self.update_statusbar('Extracting update and restarting...')

    def init_sentry(self):
        # sentry is error logging application
        with configure_scope() as scope:
            scope.user = dict(
                username=self.username,
                email=self.get_setting('email'))
            # scope.set_extra('version', VERSION) # added to sentry release field
                
    def active_table_widget(self):
        return self.tabs.currentWidget()
       
    def active_table(self):
        return self.active_table_widget().view
    
    def show_changeminesite(self):
        dlg = dlgs.ChangeMinesite(parent=self)
        return dlg.exec_()
        
    def closeEvent(self, event):
        s = self.settings
        s.setValue('window size', self.size())
        s.setValue('window position', self.pos())
        s.setValue('minesite', self.minesite)
        s.setValue('active table', self.active_table_widget().title)

        # update on closeEvent if update available... maybe not yet
        # if self.updater.update_available:
        #     self._install_update(updater=self.updater, ask_user=False)
    
    def get_setting(self, key):
        return self.settings.value(key, defaultValue=None)
    
    def get_username(self):
        s = self.settings
        username = self.get_setting('username')
        email = self.get_setting('email')

        if username is None or email is None:
            self.set_username()
            username = self.username

        return username
    
    def set_username(self):
        # show username dialog and save first/last name to settings
        s = self.settings
        dlg = dlgs.InputUserName(self)
        if not dlg.exec_(): return

        s.setValue('username', dlg.username)
        s.setValue('email', dlg.email)
        self.username = dlg.username

    def set_tsi_username(self):
        CredentialManager(name='tsi').prompt_credentials()
    
    # def load_tsi_username(self):
    #     # try to load from settings
    #     return CredentialManager(name='tsi').load()
    #     s = self.settings
    #     username = s.value('tsi_username', defaultValue=None)
    #     password = s.value('tsi_password', defaultValue=None)

    #     return username, password

    # def get_tsi_username(self):
    #     # TSIWebpage asks main window for username/pw
    #     username, password = self.load_tsi_username()

    #     # if not in settings, prompt user with dialog
    #     if username is None or password is None:
    #         if self.set_tsi_username():
    #             return self.load_tsi_username() # try one more time
    #         else:
    #             return None, None
        
    #     return username, password
            
    @property
    def driver(self):
        return self._driver if hasattr(self, '_driver') else None

    @driver.setter
    def driver(self, driver):
        self._driver = driver
            
    def open_sap(self):
        from ..web import SuncorConnect
        self.sc = SuncorConnect(ask_token=True, mw=self, _driver=self.driver)
        Worker(func=self.sc.open_sap, mw=self) \
            .add_signals(signals=('result', dict(func=self.handle_sap_result))) \
            .start()
        self.update_statusbar('SAP opened in worker thread.')
    
    def handle_sap_result(self, sc=None):
        # just need to keep a referece to the driver in main thread so chrome doesnt close
        if sc is None: return
        self.driver = sc.driver

    def create_menu(self):
        bar = self.menuBar()
        file_ = bar.addMenu('File')
        file_.addAction(self.act_new_item)
        file_.addAction(self.act_refresh)
        file_.addAction(self.act_refresh_allopen)
        file_.addAction(self.act_prev_tab)
        file_.addAction(self.act_change_minesite)
        file_.addAction(self.act_viewfolder)

        edit_ = bar.addMenu('Edit')
        edit_.addAction('Edit item')
        
        table_ = bar.addMenu('Table')
        table_.addAction(self.act_email_table)
        table_.addAction(self.act_export_excel_table)

        rows_ = bar.addMenu('Rows')
        rows_.addAction(self.act_open_tsi)
        rows_.addAction(self.act_delete_event)
        rows_.addAction(self.act_update_component)
        rows_.addAction(self.act_detailsview)

        database_ = bar.addMenu('Database')
        database_.addAction(self.act_update_comp_smr)
        database_.addAction(self.act_reset_db)
        database_.addAction(self.act_open_sap)

        help_ = bar.addMenu('Help')
        help_.addAction(self.act_show_about) # this actually goes to main 'home' menu
        help_.addAction(self.act_username)
        help_.addAction(self.act_tsi_username)
        help_.addAction(self.act_check_update)
        help_.addAction(self.act_test_error)

    def test_error(self):
        a = 5
        b = 6

        return a / 0

    def create_actions(self):
        # Menu/shortcuts
        t = self.active_table_widget

        act_test_error = QAction('Test Error', self, triggered=self.test_error)

        act_show_about = QAction('About', self, triggered=dlgs.about)
        act_username = QAction('Reset Username', self, triggered=self.set_username)
        act_tsi_username = QAction('Set TSI Username', self, triggered=self.set_tsi_username)
        act_open_sap = QAction('Open SAP', self, triggered=self.open_sap)
        act_check_update = QAction('Check for Update', self, triggered=self.check_update)

        act_refresh = QAction('Refresh Menu', self,
            triggered=lambda: t().show_refresh(),
            shortcut=QKeySequence('Ctrl+R'))
        act_new_item = QAction('Add New Row', self,
            triggered=lambda: t().show_addrow(),
            shortcut=QKeySequence('Ctrl+Shift+N'))

        act_prev_tab = QAction('Previous Tab', self,
            triggered=lambda: self.tabs.activate_previous(),
            shortcut=QKeySequence('Meta+Tab'))

        act_change_minesite = QAction('Change MineSite', self,
            triggered=self.show_changeminesite,
            shortcut=QKeySequence('Ctrl+Shift+M'))

        act_open_tsi = QAction('Open TSI', self, triggered=self.open_tsi)
        act_delete_event = QAction('Delete Row', self, triggered=lambda: t().remove_row())

        from .. import units as un
        from ..database import db
        act_update_comp_smr = QAction('Update Component SMR', self, triggered=un.update_comp_smr)
        act_reset_db = QAction('Reset Database Connection', self, triggered=db.reset)

        # TODO: only add these to context menu with specific tables, eg not FC Summary?
        act_refresh_allopen = QAction('Refresh All Open', self, 
            triggered=lambda: t().refresh_allopen(default=True),
            shortcut=QKeySequence('Ctrl+Shift+R'))
        
        act_refresh_lastweek = QAction('Refresh Last Week', self, 
            triggered=lambda: t().refresh_lastweek(default=True))
        act_refresh_lastmonth = QAction('Refresh Last Month', self, 
            triggered=lambda: t().refresh_lastmonth(default=True))

        act_viewfolder = QAction('View Folder', self, triggered=lambda: t().view_folder(), shortcut=QKeySequence('Ctrl+Shift+V'))

        act_detailsview = QAction('Details View', self, triggered=lambda: t().show_details(), shortcut=QKeySequence('Ctrl+Shift+D'))

        act_update_component = QAction('Update Component', self, triggered=lambda: t().show_component())
        act_email_table = QAction('Email Table', self, 
            triggered=lambda: t().email_table())
        act_export_excel_table = QAction('Export to Excel', self, triggered=lambda: t().export_excel())

        f.set_self(vars())

    def contextMenuEvent(self, event):
        # TODO: use caller to check current tab?
        source = self.sender()
        child = self.childAt(event.pos())

        menu = QMenu(self)
        menu.addAction(self.act_viewfolder)

        # add actions based on current tab
        
        menu.addSeparator()
        menu.addAction(self.act_refresh)
        menu.addAction(self.act_refresh_allopen)
        menu.addAction(self.act_refresh_lastweek)
        menu.addAction(self.act_refresh_lastmonth)

        menu.addSeparator()

        menu.addAction(self.act_detailsview)

        action = menu.exec_(self.mapToGlobal(event.pos()))

    def open_tsi(self):
        # NOTE should probs move to table_widget
        view = self.active_table()
    
        if not view.parent.title in ('Event Log', 'Work Orders', 'Component CO'):
            msg = 'Please chose a row from the Event Log or Work Orders tab.'
            dlgs.msg_simple(msg=msg, icon='warning')
            return

        e, row = view.e, view.row
        if row is None: return

        row.update(vals=dict(StatusTSI='Open', TSIAuthor=self.username))
        self.update_statusbar(msg=f'TSI opened for: {e.Unit} - {e.Title}')  


class TabWidget(QTabWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.tabindex = dd(int)
        
        m = f.config['TableName']['Class'] # get list of table classes from config
        lst = ['EventLog', 'WorkOrders', 'TSI', 'ComponentCO', 'UnitInfo', 'FCSummary', 'FCDetails', 'EmailList', 'Availability']
       
        # Add tabs to widget
        for i, title in enumerate(lst):
            self.addTab(getattr(tbls, title)(parent=self), m[title])
            self.tabindex[m[title]] = i
        
        self.currentChanged.connect(self.save_activetab)
        self.prev_index = self.currentIndex()
        self.current_index = self.prev_index

    def get_index(self, title):
        return self.tabindex[title]
    
    def get_widget(self, title):
        i = self.get_index(title)
        return self.widget(i)
    
    def activate_tab(self, title):
        i = self.get_index(title)
        self.setCurrentIndex(i)
    
    def save_activetab(self, *args):
        s = self.parent().settings
        s.setValue('active table', self.currentWidget().title)
        
        # keep track of previous indexes for ctrl+tab to revert
        self.prev_index = self.current_index
        self.current_index = self.currentIndex()
    
    def activate_previous(self):
        self.setCurrentIndex(self.prev_index)

      
# ARCHIVE
def disable_window_animations_mac(window):
    # We need to access `.winId()` below. This method has an unwanted (and not
    # very well-documented) side effect: Calling it before the window is shown
    # makes Qt turn the window into a "native window". This incurs performance
    # penalties and leads to subtle changes in behaviour. We therefore wait for
    # the Show event:
    def eventFilter(target, event):
        from objc import objc_object
        view = objc_object(c_void_p=int(target.winId()))
        NSWindowAnimationBehaviorNone = 2
        view.window().setAnimationBehavior_(NSWindowAnimationBehaviorNone)
    FilterEventOnce(window, QEvent.Show, eventFilter)

class FilterEventOnce(QObject):
    def __init__(self, parent, event_type, callback):
        super().__init__(parent)
        self._event_type = event_type
        self._callback = callback
        parent.installEventFilter(self)
    def eventFilter(self, target, event):
        if event.type() == self._event_type:
            self.parent().removeEventFilter(self)
            self._callback(target, event)
        return False
