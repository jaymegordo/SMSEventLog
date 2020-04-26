
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
# Conditional Formatting
# copy selected cells

# TODO: Mark columns as non editable
# TODO: Keyboard shortcuts > ctrl + down, right
# TODO: cell dropdown menu
# TODO: column bold

# TODO: Filter rows
# TODO: load tables on tab first selection?
# TODO: green 'flash' for user confirmation value updated in db
# TODO: Show 'details' menu > QListView?
# TODO: change minesite > ctrl+shift+M

# FUTURE
# Interact with outlook
# Select certain rows to email



# def disable_window_animations_mac(window):
#     # We need to access `.winId()` below. This method has an unwanted (and not
#     # very well-documented) side effect: Calling it before the window is shown
#     # makes Qt turn the window into a "native window". This incurs performance
#     # penalties and leads to subtle changes in behaviour. We therefore wait for
#     # the Show event:
#     def eventFilter(target, event):
#         from objc import objc_object
#         view = objc_object(c_void_p=int(target.winId()))
#         NSWindowAnimationBehaviorNone = 2
#         view.window().setAnimationBehavior_(NSWindowAnimationBehaviorNone)
#     FilterEventOnce(window, QEvent.Show, eventFilter)

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


def get_minesite():
    # get minesite from mainwindow, or use global default for dev
    mainwindow = get_mainwindow()
    if not mainwindow is None:
        return mainwindow.minesite
    else:
        return minesite

class Table(QAbstractTableModel):
    def __init__(self, df, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.parent = parent
        self.title = self.parent.title
        self.tablename = f.config['TableName'][self.title] # name of db model
        self.dbtable = getattr(dbm, self.tablename) # db model definition, NOT instance
        
        self.df = df
        self._cols = list(df.columns)
        self.r, self.c = df.shape[0], df.shape[1]
        
        # create tuple of ints from parent's list of disabled table headers
        self.disabled_cols = tuple(i for i, col in enumerate(self._cols) if col in parent.disabled_cols)
        
        # tuple of ints for date cols
        self.dt_cols = tuple(i for i, val in enumerate(df.dtypes) if val == 'datetime64[ns]')

    def insertRows(self, m, parent=None):
        rows = self.rowCount()
        self.beginInsertRows(QModelIndex(), rows, rows) # parent, first, last
        self.df = self.df.append(m, ignore_index=True)
        self.endInsertRows()

    def removeRows(self, i, parent=None):
        self.beginRemoveRows(QModelIndex(), i, i) # parent, row, count?
        df = self.df
        self.df = df.drop(df.index[i]).reset_index(drop=True)
        self.endInsertRows()

        # return super().removeRows(self, int, parent=parent)

    def rowCount(self, index=QModelIndex()):
        return self.df.shape[0]

    def columnCount(self, index=QModelIndex()):
        return self.df.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        # TableView asks the model for data to display or edit
        df = self.df

        if index.isValid():
            row, col = self.getRowCol(index)
            val = df.iloc[row, col]

            if role in (Qt.DisplayRole, Qt.EditRole):
                if col in self.dt_cols:
                    return val
                elif not pd.isnull(val):
                    return str(val)
                else:
                    return ''

        return None

    def getColIndex(self, header):
        return self.df.columns.get_loc(header)
    
    def getRowCol(self, index):
        return index.row(), index.column()

    def update_db(self, index, val):
        # Update single value from row in database
        # TODO: not used, this could maybe move to TableWidget
        row, col = index.row(), index.column()
        df = self.df
        header = df.columns[col] # view header

        # print(row, df.iloc[row, col], df.iloc[row, 0], df.index[row])

        e = el.Row(tbl=self, i=row)
        e.update_single(header=header, val=val)
    
    def create_model(self, i):
        # Not used currently
        # maybe don't need this, have to create object from database usually?

        # create dbmodel from table model given row index i
        e = self.dbtable()
        df = self.df
        view_cols = self._cols
        model_cols = f.convert_list_view_db(title=self.title, cols=view_cols)

        # loop cols, setattr on model
        for col, v in enumerate(model_cols):
            setattr(e, v, df.iloc[i, col])
        
        return e
               
    def setData(self, index, val, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False
        
        row, col = self.getRowCol(index)
        df = self.df
        df.iloc[row, col] = val

        self.update_db(index=index, val=val)
        self.dataChanged.emit(index, index)

        return True

    def headerData(self, p_int, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._cols[p_int]
            elif orientation == Qt.Vertical:
                return p_int

        return None

    def sort(self, col, order):
        self.layoutAboutToBeChanged.emit()

        self.df.sort_values( 
            self._cols[col],
            ascending=order==Qt.AscendingOrder, inplace=True)

        self.layoutChanged.emit()

    def flags(self, index):
        ans = Qt.ItemIsEnabled | Qt.ItemIsSelectable 
        # Qt.ItemIsEditable ?
        # fl |= Qt.ItemIsDragEnabled
        # fl |= Qt.ItemIsDropEnabled

        if not index.column() in self.disabled_cols:
            ans |= Qt.ItemIsEditable
        
        return ans

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle(title)
        self.setMinimumSize(QSize(1000, 400))

        self.main_widget = MainWidget(self)
        self.setCentralWidget(self.main_widget)

        self.create_actions()
        self.create_menu()

        # Settings
        self.settings = QSettings('sms', 'smseventlog')
        self.resize(self.settings.value('window size', defaultValue=QSize(1200, 1000)))
        self.move(self.settings.value('window position', defaultValue=QPoint(50, 50)))
        self.minesite = self.settings.value('minesite', defaultValue='FortHills')

        # TODO: connect minesite_changed function
        self.statusBar().showMessage(f'Minesite: {self.minesite}')
    
    def after_init(self):
        # TODO: need to show window first, then show loading message
        self.username = self.get_username()
        self.active_table().refresh(default=True)
    
    def active_table(self):
        return self.main_widget.tabs.currentWidget()

    def show_refresh(self):
        self.active_table().show_refresh()
        
    def closeEvent(self, event):
        s = self.settings
        s.setValue('window size', self.size())
        s.setValue('window position', self.pos())
        s.setValue('minesite', self.minesite)
    
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
        e = row.create_model_from_db()
        # el.print_model(e)

        ef = fl.EventFolder(e=e)
        ef.show()

    def create_menu(self):
        bar = self.menuBar()
        file_ = bar.addMenu('File')
        file_.addAction('New item')
        file_.addAction(self.act_refresh)

        edit_ = bar.addMenu('Edit')
        edit_.addAction('Edit item')
        
        help_ = bar.addMenu('Help')
        help_.addAction(self.act_username)

        rows_ = bar.addMenu('Rows')
        rows_.addAction(self.act_open_tsi)
        rows_.addAction(self.act_remove_tsi)
        rows_.addAction(self.act_delete_event)

    def create_actions(self):
        # Menu/shortcuts
        self.act_username = QAction('Reset Username', self, triggered=self.set_username)

        self.act_refresh = QAction('Refresh Menu', self, triggered=self.show_refresh)
        self.act_refresh.setShortcut(QKeySequence('Ctrl+R'))

        self.act_open_tsi = QAction('Open TSI', self, triggered=self.open_tsi)
        self.act_remove_tsi = QAction('Remove TSI', self, triggered=self.remove_tsi)
        self.act_delete_event = QAction('Delete Event', self, triggered=self.delete_event)

        # TODO: only add these to context menu with specific tables, eg not FC Summary?
        t = self.active_table
        self.act_refresh_allopen = QAction('Refresh All Open', self, triggered=lambda: t().refresh_allopen())
        self.act_refresh_allopen.setShortcut(QKeySequence('Ctrl+Shift+R'))
        
        self.act_refresh_lastweek = QAction('Refresh Last Week', self, triggered=lambda: t().refresh_lastweek())
        self.act_refresh_lastmonth = QAction('Refresh Last Month', self, triggered=lambda: t().refresh_lastmonth())

        self.act_viewfolder = QAction('View Folder', self, triggered=self.view_folder)
        self.act_viewfolder.setShortcut(QKeySequence('Ctrl+V'))

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
        table = self.active_table()
    
        if not table.title in ('Event Log', 'Work Orders'):
            msg = 'Please chose a row from the Event Log or Work Orders tab.'
            dlgs.msg_simple(msg=msg, icon='warning')
            return

        row = table.row_from_activerow()
        row.update(vals=dict(StatusTSI='Open', TSIAuthor=self.username))
        # TODO: maybe show status message to confirm TSI opened?

    def remove_tsi(self):
        table = self.active_table()
        
        if table.title == 'TSI':
            e = table.model_from_activerow()
            row = table.row_from_activerow()

            # TODO: bit sketch, should give model to row first then access from dict only?
            m = dict(Unit=e.Unit, DateAdded=e.DateAdded, Title=e.Title)

            msg = f'Are you sure you would like to remove the tsi for:\n\n{f.pretty_dict(m)}\n\n \
                (This will only set the TSI Status to Null, not delete the event).'
            if dlgs.msgbox(msg=msg, yesno=True):
                row.update(vals=dict(StatusTSI=None))
                table.model.removeRows(i=row.i)
    
    def delete_event(self):
        # TODO: need to figure out why this adds 2 blank rows after delete
        table = self.active_table()
        e = table.model_from_activerow()
        row = table.row_from_activerow()

        m = dict(Unit=e.Unit, DateAdded=e.DateAdded, Title=e.Title)

        msg = f'Are you sure you would like to permanently delete the event:\n\n{f.pretty_dict(m)}'
        if dlgs.msgbox(msg=msg, yesno=True):
            row.update(delete=True)
            table.model.removeRows(i=row.i)
            # table.model.removeRow(row.i)


class MainWidget(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Initialize tab screen
        tabs = QTabWidget()
        lst = ['Event Log', 'Work Orders', 'Component CO', 'TSI', 'Unit Info', 'FC Summary', 'FC Details']

        # Add tabs to widget
        for title in lst:
            tabs.addTab(getattr(tbls, title.replace(' ',''))(parent=self), title)

        self.layout.addWidget(tabs)
        self.tabs = tabs


def launch():
    app = get_qt_app()
    app.setStyle('Fusion')
    w = MainWindow()
    # disable_window_animations_mac(w)

    # monitor_num = 1 if f.is_win() else 0

    # monitor = QDesktopWidget().screenGeometry(monitor_num)
    # w.move(monitor.left(), monitor.top())
    # w.showMaximized()
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
