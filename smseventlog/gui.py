from timeit import default_timer as timer
start = timer()

import sys
import time
from datetime import (datetime as date, timedelta as delta)

import pandas as pd
import qdarkstyle
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import (QAbstractTableModel, QDate, QDateTime, QFile, QSize,
                          Qt, QTextStream, QTimer, pyqtSignal)
from PyQt5.QtGui import QIcon, QIntValidator, QFont
from PyQt5.QtWidgets import (QApplication, QComboBox, QCheckBox, QDateEdit, QDesktopWidget, QDialog,
                             QDialogButtonBox, QFormLayout, QGridLayout, QHBoxLayout,
                             QInputDialog, QLabel, QLineEdit, QMainWindow,
                             QMessageBox, QPushButton, QStyledItemDelegate, QSpinBox,
                             QTableView, QTabWidget, QTextEdit, QVBoxLayout,
                             QWidget, QSizePolicy, QAbstractItemView)

from . import (
    dbmodel as dbm,
    eventlog as el,
    functions as f)
from .database import db

global title, minsize, minsize_ss, minesite, customer
title = 'SMS Event Log'
minsize = QSize(200, 100)
minsize_ss = 'QLabel{min-width: 100px}'
minesite, customer = 'FortHills', 'Suncor'

# FEATURES NEEDED
# Conditional Formatting
# copy selected cells
# Mark columns as non editable

# Keyboard shortcuts > ctrl + down, right
# TODO: cell dropdown menu
# TODO: column bold
# TODO: Make load rows form, cmd+R to refresh table
# TODO: Add new rows
# TODO: Filter rows
# TODO: load tables on tab first selection?

# FUTURE
# Interact with outlook
# Select certain rows to email


class InputField():
    def __init__(self, text, col_db=None, box=None, dtype='text', default=None):
        self.text = text
        if col_db is None: col_db = text
        self.col_db = col_db
        self.box = box
        self.dtype = dtype
        self.default = default
    
    def get_val(self):
        box = self.box

        if isinstance(box, QLineEdit):
            val = box.text()
        if isinstance(box, QTextEdit):
            val = box.toPlainText()
        elif isinstance(box, QComboBox):
            val = box.currentText()
        elif isinstance(box, QSpinBox):
            val = box.value()
        elif isinstance(box, QDateEdit):
            val = box.dateTime().toPyDateTime()

        return val

    def set_val(self, val):
        box = self.box

        if isinstance(box, (QLineEdit, QTextEdit)):
            box.setText(val)
        elif isinstance(box, QComboBox):
            box.setCurrentText(val)
        elif isinstance(box, QSpinBox):
            box.setValue(val)
        elif isinstance(box, QDateEdit):
            box.setDate(val)
    
    def set_default(self):
        if not self.box is None and not self.default is None:
            self.box.setCurrentText(self.default)

# DIALOG WINDOWS
class AddRow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        if not parent is None:
            self.table = parent.view.model()
            self.tablename = self.table.tablename
            self.title = self.table.title
        else:
            self.tablename = 'EventLog'
            self.title = 'Event Log'
        
        self.row = getattr(dbm, self.tablename)()

        self.setWindowTitle('Add Item')
        self.vLayout = QVBoxLayout(self)
        self.formLayout = QFormLayout(self)
        self.formLayout.setLabelAlignment(Qt.AlignLeft)
        self.formLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.vLayout.addLayout(self.formLayout)
        self.fields = []
    
    def show(self):
        btnbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btnbox.accepted.connect(self.accept)
        btnbox.accepted.connect(self.okay_pressed)
        btnbox.rejected.connect(self.reject)
        self.vLayout.addWidget(btnbox, alignment=Qt.AlignBottom | Qt.AlignCenter)

        self.setFixedSize(self.sizeHint())

    def add_input(self, field, items=None, layout=None):
        text, dtype = field.text, field.dtype

        if not items is None:
            box = QComboBox()
            box.setEditable(True)
            box.setMaxVisibleItems(20)
            box.addItems(items)
        elif dtype == 'text':
            box = QLineEdit()
        elif dtype == 'textbox':
            box = QTextEdit()
            box.setTabChangesFocus(True)
            box.setMaximumSize(box.sizeHint().width(), 60)
        elif dtype == 'int':
            box = QSpinBox()
            box.setRange(0, 1000000)
        elif dtype == 'date':
            box = QDateEdit()
            box.setDate(QDate().currentDate())
            box.setCalendarPopup(True)

        setattr(self, 'f{}'.format(field.text.replace(' ', '')), field)
        field.box = box
        field.set_default()
        self.fields.append(field)
        if layout is None:
            layout = self.formLayout
        layout.addRow(QLabel(f'{text}:'), box)
    
    def okay_pressed(self):
        row = self.row
        
        # add fields to dbmodel from form fields
        for field in self.fields:
            setattr(row, field.col_db, field.get_val())

        m = el.model_dict(model=row)
        m = f.convert_dict_db_view(title=self.title, m=m)
        self.table.insertRows(m=m)

        # call row add all to db
        # add row to db

class AddEvent(AddRow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.FCNumber = None
        self.row.UID = self.create_uid()
        layout = self.vLayout
        df = db.get_df_unit()

        # Checkboxes
        self.cbFC = QCheckBox('FC')
        self.cbFC.stateChanged.connect(self.create_fc)
        self.cbEventFolder = QCheckBox('Create Event Folder')
        self.cbEventFolder.setChecked(True)

        self.add_input(field=InputField(text='MineSite', default=minesite), items=f.config['MineSite'])
        self.add_input(field=InputField(text='Unit'), items=list(df[df.MineSite==minesite].Unit))
        self.add_input(field=InputField(text='SMR', dtype='int'))
        self.add_input(field=InputField(text='Date', dtype='date', col_db='DateAdded'))

        self.formLayout.addRow('', self.cbFC)
        self.formLayout.addRow('', self.cbEventFolder)

        self.add_input(field=InputField(text='Title', dtype='textbox'))
        self.add_input(field=InputField(text='Warranty Status', col_db='WarrantyYN'), items=f.config['WarrantyStatus'])
        self.add_input(field=InputField(text='Work Order', col_db='WorkOrder'))
        self.add_input(field=InputField(text='WO Customer', col_db='SuncorWO'))
        self.add_input(field=InputField(text='PO Customer', col_db='SuncorPO'))

        self.show()
    
    def create_uid(self):
        return str(time.time()).replace('.','')[:12]
    
    def link_fc(self):
        unit = self.fUnit.get_val()
        row = el.Row(keys=dict(FCNumber=self.FCNumber, Unit=unit), dbtable=dbm.FactoryCampaign)
        row.update(field='UID', val=self.uid)

    def create_fc(self):
        unit = self.fUnit.get_val()

        if self.cbFC.isChecked():
            # TODO: This can eventually go into its own function
            df = db.get_df_fc(minesite=minesite)
            df = df[df.Unit==unit]
            prefix = 'FC '
            df['Title'] = df.FCNumber + ' - ' + df.Subject

            ok, val = inputbox(msg='Select FC:', dtype='choice', items=list(df.Title), editable=True)
            if ok:
                self.fTitle.set_val(prefix + val)
                self.FCNumber = val.split(' - ')[0]
                
            else:
                self.cbFC.setChecked(False)
    
    def okay_pressed(self):
        super().okay_pressed()
        if self.cbFC.isChecked():
            # self.link_fc()
            pass
        
        if self.cbEventFolder.isChecked():
            pass

class AddUnit(AddRow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        df = db.get_df_unit()

        self.add_input(field=InputField(text='Unit'), items=list(df[df.MineSite==minesite].Unit))
        self.add_input(field=InputField(text='Serial'))
        self.add_input(field=InputField(text='Model'), items=list(df.Model.unique()))
        self.add_input(field=InputField(text='MineSite', default=minesite), items=f.config['MineSite'])
        self.add_input(field=InputField(text='Customer', default=customer), items=list(df.Customer.unique()))
        self.add_input(field=InputField(text='Engine Serial', col_db='EngineSerial'))
        self.add_input(field=InputField(text='Delivery Date', dtype='date', col_db='DeliveryDate'))

        self.show()
    
def show_add_row():
    app = get_qt_app()
    addrow = AddEvent()
    # addrow = AddUnit()
    return addrow.exec_()

class MsgBox_Advanced(QDialog):
    def __init__(self, msg='', title='', yesno=False, statusmsg=None, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.setWindowTitle(title)
        self.setMinimumSize(minsize)
        self.setMaximumWidth(1000)
        self.setStyleSheet('QLabel {font: 14pt Courier New}')

        layout = QVBoxLayout(self)

        label = QLabel(msg, self) 
        label.setAlignment(Qt.AlignLeft)
        label.setWordWrap(True)
        layout.addWidget(label)
        
        if not yesno:
            btn = QPushButton('Okay', self)
            btn.setMaximumWidth(100)
        else:
            btn = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No, self)
            btn.accepted.connect(self.accept)
            btn.rejected.connect(self.reject)
        
        btn.clicked.connect(self.close)

        statusbar = QLabel(statusmsg, self) 
        statusbar.setAlignment(Qt.AlignLeft)
        
        hLayout = QHBoxLayout(self)
        hLayout.addWidget(statusbar)
        hLayout.addWidget(btn, alignment=Qt.AlignRight)
        layout.addLayout(hLayout)

def msgbox(msg='', yesno=False, statusmsg=None):
    app = get_qt_app()
    dlg = MsgBox_Advanced(msg=msg, title=title, yesno=yesno, statusmsg=statusmsg)
    return dlg.exec_()

def msg_simple(msg='', icon=None, infotext=None):
    app = get_qt_app()
    dlg = QMessageBox()
    dlg.setText(msg)
    dlg.setWindowTitle(title)
    # dlg.setStyleSheet(minsize_ss)
    
    if icon == 'Critical':
        dlg.setIcon(QMessageBox.Critical)
    elif icon == 'Warning':
        dlg.setIcon(QMessageBox.Warning)

    if infotext: dlg.setInformativeText(infotext)

    return dlg.exec_()

def inputbox(msg='Enter value:', dtype='text', items=None, editable=False):
    app = get_qt_app()
    dlg = QInputDialog()
    dlg.resize(minsize)
    dlg.setWindowTitle(title)
    dlg.setLabelText(msg)

    if dtype == 'text':
        dlg.setInputMode(QInputDialog.TextInput)
    elif dtype == 'choice':
        dlg.setComboBoxItems(items)
        dlg.setFont(QFont('Courier New'))
        dlg.setComboBoxEditable(editable)
        
    elif dtype == 'int':
        dlg.setInputMode(QInputDialog.IntInput)
        dlg.setIntMaximum(10)
        dlg.setIntMinimum(0)

    ok = dlg.exec_()
    if dtype in ('text', 'choice'):
        val = dlg.textValue()
    elif dtype == 'int':
        val = dlg.intValue()

    return ok, val

class Table(QAbstractTableModel):
    def __init__(self, df, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.parent = parent
        self.title = self.parent.title
        self.tablename = f.config['TableName'][self.title] # name of db model
        self.dbtable = getattr(dbm, self.tablename) # db model definition NOT instance
        
        self.df = df
        self._cols = df.columns
        self.r, self.c = df.shape[0], df.shape[1]
        self.disabled_cols = () # TODO: pass these in

    def insertRows(self, m, parent=None):
        rows = self.rowCount()
        self.beginInsertRows(QtCore.QModelIndex(), rows, rows) # parent, first, last
        self.df = self.df.append(m, ignore_index=True)
        self.endInsertRows()

    def removeRow(self, int, parent=None):
        return super().removeRow(self, int, parent=parent)

    def rowCount(self, index=QtCore.QModelIndex()):
        return self.df.shape[0]

    def columnCount(self, index=QtCore.QModelIndex()):
        return self.df.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        # TableView asks the model for data to display or edit
        df = self.df

        if index.isValid():
            row, col = self.getRowCol(index)
            val = df.iloc[row, col]

            if role in (Qt.DisplayRole, Qt.EditRole):
                if df.dtypes[col] == 'datetime64[ns]':
                    return val

                if not pd.isnull(val):
                    return str(val)
                else:
                    return ''

        # else:
        return None

    def getColIndex(self, header):
        return self.df.columns.get_loc(header)
    
    def getRowCol(self, index):
        return index.row(), index.column()

    def update_db(self, index, val):
        col = index.column()
        df = self.df
        header = df.columns[col] # view header

        row, col = index.row(), index.column()
        # print(row, df.iloc[row, col], df.iloc[row, 0], df.index[row])

        e = el.Row(tbl=self, i=index.row())
        e.update(header=header, val=val)

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

        if not index.column() in self.disabled_cols:
            ans |= Qt.ItemIsEditable
        
        return ans

class TextEditor(QTextEdit):
    returnPressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setTabChangesFocus(True)
        # self.textChanged.connect(self.textHasChanged) # need to make this func

    def keyPressEvent(self, event):       
        modifiers = QApplication.keyboardModifiers()
        
        if (modifiers != Qt.ShiftModifier and 
            event.key() in (Qt.Key_Return, Qt.Key_Enter)):
            # print(event.key())
            self.returnPressed.emit()
            return

        super(TextEditor, self).keyPressEvent(event)
        
class EditorDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        QStyledItemDelegate.__init__(self, parent=parent)
        self.parent = parent
        self.index = None
    
    def createEditor(self, parent, option, index):
        self.index = index
        editor = TextEditor(parent=parent)
        editor.returnPressed.connect(self.commitAndCloseEditor)
        return editor          

    def setEditorData(self, editor, index):
        val = index.model().data(index)

        if isinstance(editor, QTextEdit):
            editor.setText(val)
            editor.moveCursor(QtGui.QTextCursor.End)

    def setModelData(self, editor, model, index):
        # TODO: Check if text has changed, don't commit
        print('Editor delegate: seting model data')
        model.setData(index=index, val=editor.toPlainText(), role=Qt.EditRole)

    def commitAndCloseEditor(self):
        editor = self.sender()
        self.commitData.emit(editor)
        self.parent.view.resizeRowToContents(self.index.row())
        self.closeEditor.emit(editor, QStyledItemDelegate.NoHint)

class AlignDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super(AlignDelegate, self).initStyleOption(option, index)
        option.displayAlignment = Qt.AlignCenter

class DateColumnDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(DateColumnDelegate, self).__init__(parent=parent)
        self.format = 'yyyy-MM-dd'
        # self.format = '%Y-%m-%d'
        # TODO: Escape key back out of both menus

    def initStyleOption(self, option, index):
        super(DateColumnDelegate, self).initStyleOption(option, index)
        option.displayAlignment = Qt.AlignCenter

    def old_sizeHint(self, option, index):
        return
        size = super(DateColumnDelegate, self).sizeHint(option, index)
        size.setWidth(40)
        print(size.height(), size.width())
        return size

    def displayText(self, value, locale):
        dtformat = '%Y-%m-%d'
        if isinstance(value, date) and not pd.isnull(value):
            return value.strftime(dtformat)
        else:
            return ''
        
        # if not pd.isnull(value):
        #     return QDate(value).toString(self.format)
        # else:
        #     return ''

    def createEditor(self, parent, option, index):
        editor = QDateEdit(parent)
        editor.dateChanged.connect(self.commitAndCloseEditor)
        editor.setDisplayFormat(self.format)
        editor.setCalendarPopup(True)
        return editor

    def setEditorData(self, editor, index):
        val = index.model().data(index, Qt.EditRole)

        if pd.isnull(val):
            # val = QDateTime.currentDateTime().toPyDateTime()
            val = date.now().date()

        editor.setDate(val)

    def setModelData(self, editor, model, index):
        dt = QDateTime(editor.date()).toPyDateTime()
        model.setData(index, dt)

    def commitAndCloseEditor(self):
        editor = self.sender()
        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QStyledItemDelegate.NoHint)


class TableWidget(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.parent = parent
        self.title = self.parent.title

        vLayout = QVBoxLayout(self)
        self.btnbox = QHBoxLayout()
        self.btnbox.setAlignment(Qt.AlignLeft)

        # TODO: Different tabs will need different buttons
        self.add_button(name='Refresh', func=self.refresh)
        self.add_button(name='Add New', func=self.add_row)

        view = QTableView(self)
        view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        view.setSelectionBehavior(QTableView.SelectRows)
        view.setWordWrap(True)
        view.horizontalHeader().setDefaultAlignment(Qt.AlignCenter | Qt.Alignment(Qt.TextWordWrap))
        view.setSortingEnabled(True)
        view.horizontalHeader().sortIndicatorChanged.connect(view.resizeRowsToContents)
        view.setStyleSheet(' \
            QTableView::item:selected:active {color: #000000;background-color: #ffff64;} \
            QTableView::item:selected:hover {color: #000000;background-color: #cccc4e;} \
            QTableView::item {border: 0px; padding: 2px;}')

        vLayout.addLayout(self.btnbox)
        vLayout.addWidget(view)
        self.view = view
        self.set_default_headers()

    def set_default_headers(self):
        cols = f.get_default_headers(title=self.title)
        df = pd.DataFrame(columns=cols)
        self.display_data(df=df)

    def add_button(self, name, func):
        btn = QPushButton(name, self)
        btn.setMaximumWidth(60)
        btn.clicked.connect(func)
        self.btnbox.addWidget(btn)
   
    def add_row(self):
        try:
            dlg = AddEvent(parent=self)
            dlg.exec_()
        except:
            pass
   
    def refresh(self):
        # TODO: This will need to accept filter from refresh menu
        title = self.title

        fltr = el.Filter(title=title)
        # TODO: get MineSite from somewhere
        fltr.add(field='minesite', val='forthills')
        
        df = el.get_df(title=title, fltr=fltr, defaults=True)
        self.display_data(df=df)

    def set_date_delegates(self):
        view = self.view
        date_delegate = DateColumnDelegate(view)

        for i, val in enumerate(view.model().df.dtypes):
            if val == 'datetime64[ns]':
                view.setItemDelegateForColumn(i, date_delegate)
                view.setColumnWidth(i, 90) # TODO: this should be in the delegate!

    def center_columns(self, cols):
        view = self.view
        model = view.model()
        align_delegate = AlignDelegate(view)

        for c in cols:
            if c in model.df.columns:
                view.setItemDelegateForColumn(model.getColIndex(c), align_delegate)

    def set_column_width(self, cols, width):
        view = self.view
        model = view.model()
        if not isinstance(cols, list): cols = [cols]

        for c in cols:
            if c in model.df.columns:
                view.setColumnWidth(model.getColIndex(c), width)
            
    def display_data(self, df):
        view = self.view
        title = self.title
        model = Table(df=df, parent=self)
        view.setModel(model)
        view.setItemDelegate(EditorDelegate(parent=self))
        view.resizeColumnsToContents()

        cols = ['Passover', 'Unit', 'Status', 'Wrnty', 'Work Order', 'Seg', 'Customer WO', 'Customer PO', 'Serial', 'Side']
        # self.center_columns(cols=cols)
        
        if title in ('Event Log', 'Work Orders', 'TSI', 'Component CO'):
            view.hideColumn(model.getColIndex('UID'))

        # resize columns
        self.set_column_width(cols=['Title', 'Part Number'], width=150)

        if title == 'Event Log':
            view.setColumnWidth(model.getColIndex('Passover'), 50)
            view.setColumnWidth(model.getColIndex('Description'), 800)
        elif title == 'Work Orders':
            self.set_column_width(cols=['Work Order', 'Customer WO', 'Customer PO'], width=80)
            self.set_column_width(cols=['Comp CO', 'DLS'], width=40)
            view.setColumnWidth(model.getColIndex('Comments'), 400)
        elif title == 'Unit Info':
            pass
        elif title == 'TSI':
            view.setColumnWidth(model.getColIndex('Details'), 400)

        self.set_date_delegates()
        view.resizeRowsToContents()

# Main Window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(title)
        self.setMinimumSize(QSize(800, 1000))
        # width = 1600
        # self.setGeometry(-1 * width, 30, width, 1000)
        bar = self.menuBar()
        file = bar.addMenu('File')
        file.addAction('New item')

        self.main_widget = MainWidget(self)
        self.setCentralWidget(self.main_widget)

class MainWidget(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        
        # Initialize tab screen
        self.tabs = QTabWidget()
        self.add_tab(title='Event Log')
        self.add_tab(title='Work Orders')
        self.add_tab(title='Component CO')
        self.add_tab(title='TSI')
        self.add_tab(title='Unit Info')
        
        # Add tabs to widget
        self.layout.addWidget(self.tabs)
    
    def add_tab(self, title):
        tab = QWidget(parent=self.tabs)
        tab.title = title
        tab.table_widget = TableWidget(parent=tab)
        tab.layout = QVBoxLayout(tab)
        tab.layout.addWidget(tab.table_widget)
        self.tabs.addTab(tab, title)


def launch():
    app = get_qt_app()
    app.setStyle('Fusion')
    w = MainWindow()

    monitor_num = 1 if f.is_win() else 0

    # TODO: use QSetting to remember prev screen geometry
    monitor = QDesktopWidget().screenGeometry(monitor_num)
    w.move(monitor.left(), monitor.top())
    w.showMaximized()
    w.show()
    w.main_widget.tabs.currentWidget().table_widget.refresh()
    return app.exec_()

def get_qt_app():
    app = QApplication.instance()
    
    if app is None:
        app = QApplication([sys.executable])
        
    app.setWindowIcon(QIcon(str(f.datafolder / 'images/SMS Icon.png')))
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    return app

