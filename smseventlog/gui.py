import sys
from datetime import datetime as date
from datetime import timedelta as delta
import dbmodel as dbm

import numpy as np
import pandas as pd
import qdarkstyle
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import (QAbstractTableModel, QDate, QDateTime, QFile, QSize, Qt,
                          QTextStream, QTimer, pyqtSignal)
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QDateEdit, QDesktopWidget, QDialog,
                             QDialogButtonBox, QGridLayout, QHBoxLayout,
                             QInputDialog, QLabel, QLineEdit, QMainWindow,
                             QMessageBox, QPushButton, QStyledItemDelegate,
                             QTableView, QTabWidget, QTextEdit, QVBoxLayout,
                             QWidget)

import eventlog as el
import functions as f

global title, minsize, minsize_ss
title = 'SMS Event Log'
minsize = QSize(200, 100)
minsize_ss = 'QLabel{min-width: 100px}'

class MsgBox_Advanced(QDialog):
    # TODO: accept parent?
    def __init__(self, msg='', title='', yesno=False, statusmsg=None):
        super().__init__()
        self.setWindowTitle(title)
        self.setMinimumSize(minsize)
        self.setMaximumWidth(1000)
        # self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet('QLabel {font: 9pt Courier New}')

        grid = QGridLayout(self)
        grid.setSpacing(20)

        label = QLabel(msg, self) 
        label.setAlignment(Qt.AlignLeft)
        label.setWordWrap(True)
        grid.addWidget(label, 0, 0, -1, 0)
        
        if not yesno:
            btn = QPushButton('Okay', self)
            btn.setMaximumWidth(100)
        else:
            btn = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No, self)
            btn.accepted.connect(self.accept)
            btn.rejected.connect(self.reject)
        
        btn.clicked.connect(self.close)
        grid.addWidget(btn, 1, 1, alignment=Qt.AlignRight)

        if statusmsg:
            statusbar = QLabel(statusmsg, self) 
            statusbar.setAlignment(Qt.AlignLeft)
            grid.addWidget(statusbar, 1, 0)

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

def inputbox(msg='Enter value:', inputmode='Text', items=None):
    app = get_qt_app()
    dlg = QInputDialog()
    dlg.resize(minsize)
    dlg.setWindowTitle(title)
    dlg.setLabelText(msg)

    if inputmode == 'Text':
        dlg.setInputMode(QInputDialog.TextInput)
    elif inputmode == 'Choice':
        dlg.setComboBoxItems(items)
    elif inputmode == 'Int':
        dlg.setInputMode(QInputDialog.IntInput)
        dlg.setIntMaximum(10)
        dlg.setIntMinimum(0)

    ok = dlg.exec_()
    if inputmode in ('Text', 'Choice'):
        val = dlg.textValue()
    elif inputmode == 'Int':
        val = dlg.intValue()

    return ok, val

# FEATURES NEEDED
# Trigger event on cell edit > setData (if data changed)
# Conditional Formatting
# copy selected cells
# Mark columns as non editable
# new line within cell
# line and active cell different colours

# Dark theme
# launch full screen
# Enforce data types
# tableview header color > QHeaderView
# Tab colors
# Keyboard shortcuts > ctrl + down, right
# TODO: cell dropdown menu
# TODO: column bold
# TODO: Make load rows form
# TODO: Add new rows
# TODO: Filter rows
# TODO:load tables on tab first selection?

# FUTURE
# Interact with outlook
# Select certain rows to email

# Update Control Flow
# User edits cell > index passed to model setData()
# setData needs to create an object with the table's key, and current value
# need to map index to field name
# object calls own method to updte in db?
    # e = EventLog(UID=123456788, MineSite='FortHills')
    # Pass the whole row, which has ID field
    # t = EventLog
    # stmt = update(t).where(t.UID==e.UID).values(MineSite=e.MineSite)
    # print(stmt)
    # result = session.execute(stmt)
    # session.commit()

# def insertRow(self, int, parent=QModelIndex()):
#     return super().insertRow(self, int, parent=parent)

# def removeRow(self, int, parent=QModelIndex()):
#     return super().removeRow(self, int, parent=parent)

class Table(QAbstractTableModel):
    def __init__(self, df, parent=None, is_df=True):
        QAbstractTableModel.__init__(self, parent)
        self.parent = parent
        self.is_df = is_df
        self.title = self.parent.title
        self.tablename = f.config['TableName'][self.title] # name of db model
        self.table = getattr(dbm, self.tablename) # db model

        if is_df:
            self.df = df
        else:
            self.df = np.array(df.fillna(value=''))

        self._cols = df.columns
        self.r, self.c = np.shape(self.df)
        self.disabled_cols = () # TODO: pass these in

    def rowCount(self, parent=None):
        return self.r

    def columnCount(self, parent=None):
        return self.c

    def data(self, index, role=Qt.DisplayRole):
        # TableView asks the model for data to display or edit
        if index.isValid():
            if role in (Qt.DisplayRole, Qt.EditRole):
                return self.getData(index)

        return None

    def getColIndex(self, header):
        return self.df.columns.get_loc(header)
    
    def getRowCol(self, index):
        return index.row(), index.column()

    def getData(self, index, stronly=True):
        row, col = self.getRowCol(index)
        data = self.df
        
        if self.is_df:
            val = data.iloc[row, col]
        else:
            val = data[row, col]

        if self.df.dtypes[col] == 'datetime64[ns]':
            return val

        if stronly:
            if not val is None:
                return str(val)
            else:
                return ''
        else:
            return val

    def update_db(self, index, val):
        col = index.column()
        header = self.df.columns[col] # view header

        df = self.df
        row, col = index.row(), index.column()
        # print(row, df.iloc[row, col], df.iloc[row, 0], df.index[row])

        e = el.Row(tbl=self, i=index.row())
        e.update(header=header, val=val)

    def setData(self, index, val, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False
        
        row, col = self.getRowCol(index)
        data = self.df

        if self.is_df:
            data.iloc[row, col] = val
        else:
            data[row][col] = val

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

        if self.is_df:
            self.df.sort_values( 
                self._cols[col],
                ascending=order == Qt.AscendingOrder, inplace=True)
        else:
            ind = self.df[:, col].argsort() # returns index of sort
            o = -1 if order == 1 else 1 # reverse the order if necessary
            self.df = self.df[ind][::o]

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
        val = str(index.model().getData(index))

        if isinstance(editor, QTextEdit):
            editor.setText(val)
            editor.moveCursor(QtGui.QTextCursor.End)

    def setModelData(self, editor, model, index):
        # TODO: Check if text has changed, don't commit
        print('seting model data')
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
        super(DateColumnDelegate, self).__init__(parent)
        self.format = 'yyyy-MM-dd'
        # TODO: Escape key back out of both menus

    def initStyleOption(self, option, index):
        super(DateColumnDelegate, self).initStyleOption(option, index)
        option.displayAlignment = Qt.AlignCenter

    # def sizeHint(self, option, index):
    #     size = super(DateColumnDelegate, self).sizeHint(option, index)
    #     size.setWidth(40)
    #     print(size.height(), size.width())
    #     return size

    def displayText(self, value, locale):
        if not pd.isnull(value):
            return QDate(value).toString(self.format)
        else:
            return ''

    def createEditor(self, parent, option, index):
        editor = QDateEdit(parent)
        editor.dateChanged.connect(self.commitAndCloseEditor)
        editor.setDisplayFormat(self.format)
        editor.setCalendarPopup(True)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.DisplayRole)

        if pd.isnull(value):
            value = QDateTime.currentDateTime().toPyDateTime()

        editor.setDate(value)

    def setModelData(self, editor, model, index):
        date = QDateTime(editor.date()).toPyDateTime()
        model.setData(index, date)

    def commitAndCloseEditor(self):
        editor = self.sender()
        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QStyledItemDelegate.NoHint)

class TableWidget(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent=None)
        self.parent = parent
        self.title = self.parent.title

        vLayout = QVBoxLayout(self)
        self.btnbox = QHBoxLayout()
        self.btnbox.setAlignment(Qt.AlignLeft)

        # TODO: Different tabs will need different buttons
        self.add_button(name='Refresh', func=self.refresh)

        view = QTableView(self)
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
   
    def refresh(self):
        # TODO: This will need to accept filter from refresh menu
        # i = self.parent.tabs.currentIndex()
        # title = self.parent.tabs.tabText(i)
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
                view.setColumnWidth(i, 80) # TODO: this should be in the delegate!

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
        model = Table(df=df, parent=self, is_df=True)
        view.setModel(model)
        view.setItemDelegate(EditorDelegate(parent=self))
        view.resizeColumnsToContents()

        cols = ['Passover', 'Unit', 'Status', 'Wrnty', 'Work Order', 'Seg', 'Customer WO', 'Customer PO', 'Serial', 'Side']
        self.center_columns(cols=cols)
        
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
        self.setLayout(self.layout)
    
    def add_tab(self, title):
        tab = QWidget(parent=self.tabs)
        tab.title = title
        tab.table_widget = TableWidget(parent=tab)
        tab.layout = QVBoxLayout(self)
        tab.layout.addWidget(tab.table_widget)
        tab.setLayout(tab.layout)
        self.tabs.addTab(tab, title)


def launch():
    app = get_qt_app()
    app.setStyle('Fusion')
    w = MainWindow()

    monitor_num = 1 if f.is_win() else 0
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
        
    app.setWindowIcon(QIcon(str(f.topfolder / 'data/images/SMS Icon.png')))
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    return app


