from . import tables as tbls
from .__init__ import *
from . import dialogs as dlgs

log = logging.getLogger(__name__)

global title, minsize, minsize_ss, minesite, customer
title = 'SMS Event Log'
minsize = QSize(200, 100)
minsize_ss = 'QLabel{min-width: 100px}'
minesite, customer = 'FortHills', 'Suncor'

# FEATURES NEEDED
# TODO copy selected cells
# TODO Keyboard shortcuts > ctrl + down, right
# TODO column bold
# TODO green 'flash' for user confirmation value updated in db
# TODO Show 'details' menu > QListView?
# TODO remember state of refresh dialogs
# TODO refresh dialog tab order
# TODO save previous query and run when tab first selected
# TODO selected rows highlight behind existing colors


class MainWindow(QMainWindow):
    minesite_changed = pyqtSignal(str)

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle(title)
        self.setMinimumSize(QSize(1000, 400))
        self.minesite_changed.connect(self.update_statusbar)

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
        self.update_statusbar()

        self.tabs = tabs
    
    @property
    def minesite(self):
        return self._minesite

    @minesite.setter
    def minesite(self, val):
        self._minesite = val
        self.minesite_changed.emit(val)
    
    def update_statusbar(self):
        self.statusBar().showMessage(f'Minesite: {self.minesite}')

    def after_init(self):
        # TODO: need to show window first, then show loading message
        self.username = self.get_username()
        self.active_table_widget().refresh(default=True)
    
    def active_table_widget(self):
        return self.tabs.currentWidget()
       
    def active_table(self):
        return self.active_table_widget().view

    def show_refresh(self):
        self.active_table_widget().show_refresh()
    
    def show_changeminesite(self):
        try:
            dlg = dlgs.ChangeMinesite(parent=self)
            return dlg.exec_()
        except:
            msg = 'couldn\'t change minesite'
            f.send_error(msg)
            log.error(msg)
        
    def closeEvent(self, event):
        s = self.settings
        s.setValue('window size', self.size())
        s.setValue('window position', self.pos())
        s.setValue('minesite', self.minesite)
        s.setValue('active table', self.active_table_widget().title)
    
    def get_username(self):
        s = self.settings
        username = s.value('username', defaultValue=None)

        if username is None:
            self.set_username()
            username = self.username

        return username
    
    def set_username(self):
        # show username dialog and save first/last name to settings
        s = self.settings
        dlg = dlgs.InputUserName(self)
        dlg.exec_()
        m = dlg.items
        if not m is None:
            username = '{} {}'.format(m['First'].strip(), m['Last'].strip()).title()
        else:
            username = None

        s.setValue('username', username)
        self.username = username
        print(f'setting username: {self.username}')

    def view_folder(self):
        row = self.active_table().row_from_activerow()
        if row is None: return
        e = row.create_model_from_db() # TODO: this won't work with mixed tables eg FCSummary
        # el.print_model(e)

        fl.EventFolder(e=e).show()

    def create_menu(self):
        bar = self.menuBar()
        file_ = bar.addMenu('File')
        file_.addAction('New item')
        file_.addAction(self.act_refresh)
        file_.addAction(self.act_change_minesite)
        file_.addAction(self.act_viewfolder)

        edit_ = bar.addMenu('Edit')
        edit_.addAction('Edit item')
        
        table_ = bar.addMenu('Table')
        table_.addAction(self.act_email_table)

        rows_ = bar.addMenu('Rows')
        rows_.addAction(self.act_open_tsi)
        rows_.addAction(self.act_remove_tsi)
        rows_.addAction(self.act_delete_event)
        rows_.addAction(self.act_update_component)

        help_ = bar.addMenu('Help')
        help_.addAction(self.act_username)

    def create_actions(self):
        # Menu/shortcuts
        act_username = QAction('Reset Username', self, triggered=self.set_username)

        act_refresh = QAction('Refresh Menu', self, triggered=self.show_refresh)
        act_refresh.setShortcut(QKeySequence('Ctrl+R'))

        act_change_minesite = QAction('Change MineSite', self, triggered=self.show_changeminesite)
        act_change_minesite.setShortcut(QKeySequence('Ctrl+Shift+M'))

        act_open_tsi = QAction('Open TSI', self, triggered=self.open_tsi)
        act_remove_tsi = QAction('Remove TSI', self, triggered=self.remove_tsi)
        act_delete_event = QAction('Delete Event', self, triggered=self.delete_event)

        # TODO: only add these to context menu with specific tables, eg not FC Summary?
        t = self.active_table_widget
        act_refresh_allopen = QAction('Refresh All Open', self, 
            triggered=lambda: t().refresh_allopen(default=True))
        act_refresh_allopen.setShortcut(QKeySequence('Ctrl+Shift+R'))
        
        act_refresh_lastweek = QAction('Refresh Last Week', self, 
            triggered=lambda: t().refresh_lastweek(default=True))
        act_refresh_lastmonth = QAction('Refresh Last Month', self, 
            triggered=lambda: t().refresh_lastmonth(default=True))

        act_viewfolder = QAction('View Folder', self, triggered=self.view_folder)
        act_viewfolder.setShortcut(QKeySequence('Ctrl+Shift+V'))

        act_update_component = QAction('Update Component', self, triggered=lambda: t().show_component())
        act_email_table = QAction('Email Table', self, 
            triggered=lambda: t().email_table())

        f.set_self(self, vars())

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
        action = menu.exec_(self.mapToGlobal(event.pos()))

    def open_tsi(self):
        view = self.active_table()
    
        if not view.parent.title in ('Event Log', 'Work Orders', 'Component CO'):
            msg = 'Please chose a row from the Event Log or Work Orders tab.'
            dlgs.msg_simple(msg=msg, icon='warning')
            return

        row = view.row_from_activerow()
        if row is None: return
        row.update(vals=dict(StatusTSI='Open', TSIAuthor=self.username))
        # TODO: maybe show status message to confirm TSI opened?

    def remove_tsi(self):
        view = self.active_table()
        
        if view.parent.title == 'TSI':
            e = view.model_from_activerow()
            row = view.row_from_activerow()
            if row is None: return

            # TODO: bit sketch, should give model to row first then access from dict only?
            m = dict(Unit=e.Unit, DateAdded=e.DateAdded, Title=e.Title)

            msg = f'Are you sure you would like to remove the tsi for:\n\n{f.pretty_dict(m)}\n\n \
                (This will only set the TSI Status to Null, not delete the event).'
            if dlgs.msgbox(msg=msg, yesno=True):
                row.update(vals=dict(StatusTSI=None))
                view.model.removeRows(i=row.i)
    
    def delete_event(self):
        # TODO: need to figure out why this adds 2 blank rows after delete
        view = self.active_table()
        e = view.model_from_activerow()
        row = view.row_from_activerow()
        if row is None: return

        m = dict(Unit=e.Unit, DateAdded=e.DateAdded, Title=e.Title)

        msg = f'Are you sure you would like to permanently delete the event:\n\n{f.pretty_dict(m)}'
        if dlgs.msgbox(msg=msg, yesno=True):
            row.update(delete=True)
            view.model().removeRows(i=row.i)

class TabWidget(QTabWidget):
    def __init__(self, parent):
        super(QTabWidget, self).__init__(parent)
        self.tabindex = dd(int)
        
        m = f.config['TableName']['Class'] # get list of table classes from config
        lst = ['EventLog', 'WorkOrders', 'TSI', 'ComponentCO', 'UnitInfo', 'FCSummary', 'FCDetails', 'EmailList', 'Availability']
       
        # Add tabs to widget
        for i, title in enumerate(lst):
            self.addTab(getattr(tbls, title)(parent=self), m[title])
            self.tabindex[m[title]] = i
        
        self.currentChanged.connect(self.save_activetab)

    def get_index(self, title):
        return self.tabindex[title]
    
    def get_widget(self, title):
        i = self.get_index(title)
        return self.widget(i)
    
    def activate_tab(self, title):
        i = self.get_index(title)
        self.setCurrentIndex(i)
    
    def save_activetab(self):
        s = self.parent().settings
        s.setValue('active table', self.currentWidget().title)


def launch():
    app = get_qt_app()
    app.setStyle('Fusion')
    w = MainWindow()
    # disable_window_animations_mac(w)

    w.show()
    w.after_init()
    return app.exec_()

def get_qt_app():
    app = QApplication.instance()
    
    if app is None:
        app = QApplication([sys.executable])
        
    app.setWindowIcon(QIcon(str(f.datafolder / 'images/SMS Icon.png')))
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    return app

def get_mainwindow():
    # Global function to find the (open) QMainWindow in application
    app = QApplication.instance()
    for widget in app.topLevelWidgets():
        if isinstance(widget, QMainWindow):
            return widget
    return None

def get_minesite():
    # get minesite from mainwindow, or use global default for dev
    mainwindow = get_mainwindow()
    if not mainwindow is None:
        return mainwindow.minesite
    else:
        return minesite

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
