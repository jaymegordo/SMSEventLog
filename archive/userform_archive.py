

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
