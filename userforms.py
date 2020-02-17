import sys
from PyQt5 import QtCore
from PyQt5.QtCore import QTimer, QSize, Qt
from PyQt5.QtWidgets import QWidget, QMessageBox, QApplication, QPushButton, QDesktopWidget, QGridLayout, QLabel, QDialog, QLineEdit, QVBoxLayout, QDialogButtonBox

class App(QWidget):
    def __init__(self, msg=''):
        super().__init__()
        self.msg = msg
        self.initUI()
        
    def initUI(self):
        print('launching UI')           
        self.setMinimumSize(QSize(250, 150))
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

class MsgBox_Advanced(QDialog):
    def __init__(self, msg='', title=''):
        super().__init__()
        self.setWindowTitle(title)
        self.setMinimumSize(QSize(200, 100))
        self.setMaximumWidth(600)
        self.btn = QDialogButtonBox(QDialogButtonBox.Ok)
        self.btn.clicked.connect(self.close)

        grid = QGridLayout(self)
        grid.setSpacing(20)

        label = QLabel(msg, self) 
        label.setAlignment(Qt.AlignLeft)
        label.setWordWrap(True)
        grid.addWidget(label, 0, 0)
        
        btn = QPushButton('Okay', self)
        btn.setMaximumWidth(100)
        btn.clicked.connect(self.close)
        grid.addWidget(btn, 1, 0, alignment=Qt.AlignRight)

def msgbox(msg='', title='SMS Event Log'):
    app = get_qt_app()
    dlg = MsgBox_Advanced(msg=msg, title=title)
    dlg.exec_()

def show_qt_dialog():
    app = get_qt_app()
    dlg = Form()
    dlg.exec_()

    if dlg.result():
        return dlg.edit.text()


def messagebox2(msg=''):
    app = QApplication(sys.argv)
    ex = App(msg=msg)
    # ex.setWindowFlags(ex.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

    return app.exec_()

def messagebox(msg=''):
    app = get_qt_app()
    msgBox = QMessageBox()
    msgBox.setText(msg)
    # msgBox.setInformativeText('Detail text')
    
    msgBox.setMinimumSize(QSize(250, 150))
    msgBox.setWindowTitle('SMS Event Log')
    
    return msgBox.exec_()

def get_qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([sys.executable])
    return app