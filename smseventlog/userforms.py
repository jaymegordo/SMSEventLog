import sys

from PyQt5 import QtCore
from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QDialog,
                             QDialogButtonBox, QGridLayout, QInputDialog,
                             QLabel, QLineEdit, QMessageBox, QPushButton,
                             QVBoxLayout, QWidget)

import functions as f

global title, minsize, minsize_ss
title = 'SMS Event Log'
minsize = QSize(200, 100)
minsize_ss = 'QLabel{min-width: 100px}'

class MsgBox_Advanced(QDialog):
    def __init__(self, msg='', title='', yesno=False, statusmsg=None):
        super().__init__()
        self.setWindowTitle(title)
        self.setMinimumSize(minsize)
        self.setMaximumWidth(1000)
        # self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("QLabel {font: 9pt Courier New}")

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

def get_qt_app():
    app = QApplication.instance()
    
    if app is None:
        app = QApplication([sys.executable])
        
    app.setWindowIcon(QIcon(str(f.topfolder / 'data/images/SMS Icon.png')))

    return app




# UNUSED
class App(QWidget):
    def __init__(self, msg=''):
        super().__init__()
        self.msg = msg
        self.initUI()
        
    def initUI(self):
        print('launching UI')           
        self.setMinimumSize(minsize)
        self.setWindowTitle('SMS Event Log')

        gridLayout = QGridLayout(self)

        title = QLabel(self.msg, self) 
        title.setAlignment(QtCore.Qt.AlignCenter)
        gridLayout.addWidget(title, 0, 0)
        
        btn = QPushButton("Okay", self)
        btn.clicked.connect(self.close)
        gridLayout.addWidget(btn)
        
        self.show()
        self.activateWindow()
        # self.setWindowFlag(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

    def closeEvent(self, event):
        print('closing UI')
        # QApplication.quit()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
     
class Form(QDialog):
    def __init__(self, parent=None):
        super(Form, self).__init__(parent)
        self.setWindowTitle("My Form")

        # Add an edit box
        self.edit = QLineEdit("Enter text here..")

        # Create the Ok/Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok
                                          | QDialogButtonBox.Cancel)
        self.button_box.clicked.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Create layout and add widgets
        layout = QVBoxLayout()
        layout.addWidget(self.edit)
        layout.addWidget(self.button_box)

        # Set dialog layout
        self.setLayout(layout)

def show_qt_dialog():
    app = get_qt_app()
    dlg = Form()
    dlg.exec_()

    if dlg.result():
        return dlg.edit.text()
