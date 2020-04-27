from .__init__ import *
from . import gui as ui

log = logging.getLogger(__name__)


class InputField():
    def __init__(self, text, col_db=None, box=None, dtype='text', default=None, table=None):
        self.text = text
        if col_db is None: col_db = text.replace(' ', '')
        self.col_db = col_db
        self.box = box
        self.dtype = dtype
        self.default = default
        self.table = table # just for holding and passing to Filter()
    
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

class InputForm(QDialog):
    def __init__(self, parent=None, title=''):
        super().__init__(parent=parent)
        self.parent = parent
        self.mainwindow = ui.get_mainwindow()
        self.setWindowTitle(title)
        self.vLayout = QVBoxLayout(self)
        self.formLayout = QFormLayout()
        self.formLayout.setLabelAlignment(Qt.AlignLeft)
        self.formLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.vLayout.addLayout(self.formLayout)
        self.fields = []
        self.items = None
        self.add_okay_cancel(layout=self.vLayout)
        
    def show(self):
        self.setFixedSize(self.sizeHint())

    def add_okay_cancel(self, layout):
        # add an okay/cancel btn box to bottom of QDialog's layout (eg self.vLayout)
        # parent = layout.parent()

        btnbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btnbox.accepted.connect(self.accept)
        btnbox.rejected.connect(self.reject)

        layout.addWidget(btnbox, alignment=Qt.AlignBottom | Qt.AlignCenter)
        self.btnbox = btnbox

    def add_input(self, field, items=None, layout=None, checkbox=False, cb_enabled=True, index=None):
        # Add input field to form
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
        
        boxLayout = QHBoxLayout()
        boxLayout.addWidget(box)
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # add checkbox to form line to enable/disable field
        if checkbox:
            cb = QCheckBox(self)
            cb.setChecked(cb_enabled)
            box.setEnabled(cb_enabled)
            cb.box = box # attach box to toggle later
            cb.stateChanged.connect(self.toggle_input)
            boxLayout.addWidget(cb)
            field.cb = cb
        else:
            # add spacer
            # boxLayout.addSpacerItem(QSpacerItem(24,24,hPolicy=QSizePolicy.Maximum))
            boxLayout.addSpacing(30)
        
        setattr(self, 'f{}'.format(field.text.replace(' ', '')), field)
        field.box = box
        field.set_default()
        self.fields.append(field)

        if layout is None:
            layout = self.formLayout

        label = QLabel(f'{text}:')

        if index is None:
            layout.addRow(label, boxLayout)
        else:
            layout.insertRow(index, label, boxLayout)

    def accept(self):
        try:
            super().accept()
            self.items = self.get_items()
        except:
            msg = 'Couldn\'t accept form.'
            f.send_error(msg)
            log.error(msg)

    def get_items(self):
        # return dict of all field items: values
        m = {}
        for field in self.fields:
            m[field.text] = field.get_val()
        
        return m
    
    def add_items_to_filter(self, fltr):
        # loop params, add all to parent filter
        for field in self.fields:
            if field.box.isEnabled():
                print(f'adding input | field={field.col_db}, table={field.table}')
                fltr.add(field=field.col_db, val=field.get_val(), table=field.table)

    def toggle_input(self, state):
        # toggle input field enabled/disabled based on checkbox
        source = self.sender()
        box = source.box

        if state == Qt.Checked:
            box.setEnabled(True)
            box.setFocus()
        else:
            box.setEnabled(False)

class InputUserName(InputForm):
    def __init__(self, parent=None):
        super().__init__(parent=parent, title='Enter User Name')
        layout = self.vLayout
        layout.insertWidget(0, QLabel('Welcome to the SMS Event Log! \
            \nPlease enter your first and last name to begin:\n'))

        self.add_input(field=InputField(text='First'))
        self.add_input(field=InputField(text='Last'))
        self.show()

class AddRow(InputForm):
    def __init__(self, parent=None):
        super().__init__(parent=parent, title='Add Item')

        if not parent is None:
            self.table = parent.view.model()
            self.tablename = self.table.tablename
            self.title = self.table.title
        else:
            # Temp vals
            self.tablename = 'EventLog'
            self.title = 'Event Log'
        
        self.row = getattr(dbm, self.tablename)()
    
    def accept(self):
        super().accept()
        row = self.row
        
        # add fields to dbmodel from form fields
        for field in self.fields:
            setattr(row, field.col_db, field.get_val())

        # convert row model to dict of values and append to current table
        m = f.model_dict(model=row)
        m = f.convert_dict_db_view(title=self.title, m=m)
        self.table.insertRows(m=m)

        print(int(row.UID))
        session = db.session
        session.add(row)
        session.commit()

class AddEvent(AddRow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.FCNumber = None
        row = self.row
        row.UID = self.create_uid()
        row.CreatedBy = self.mainwindow.username if not self.mainwindow is None else ''
        row.StatusEvent = 'Work In Progress'
        row.StatusWO = 'Open'

        layout = self.vLayout
        df = db.get_df_unit()
        minesite = self.mainwindow.minesite if not self.mainwindow is None else 'FortHills'

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
        # add event's UID to FC in FactoryCampaign table
        unit = self.fUnit.get_val()
        row = el.Row(keys=dict(FCNumber=self.FCNumber, Unit=unit), dbtable=dbm.FactoryCampaign)
        row.update(vals={'UID': self.uid})

    def create_fc(self):
        unit = self.fUnit.get_val()

        if self.cbFC.isChecked():
            # TODO: This can eventually go into its own function
            df = db.get_df_fc(minesite=self.mainwindow.minesite)
            df = df[df.Unit==unit]
            prefix = 'FC '
            df['Title'] = df.FCNumber + ' - ' + df.Subject

            ok, val = inputbox(msg='Select FC:', dtype='choice', items=list(df.Title), editable=True)
            if ok:
                self.fTitle.set_val(prefix + val)
                self.FCNumber = val.split(' - ')[0]
                
            else:
                self.cbFC.setChecked(False)
    
    def accept(self):
        super().accept()
        # TODO: add model/serial to model before adding to table row
        # TODO: Need to link FC!
        if self.cbFC.isChecked():
            # self.link_fc()
            pass
        
        if self.cbEventFolder.isChecked():
            # TODO: Create event folder
            pass

class AddUnit(AddRow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        df = db.get_df_unit()
        minesite = self.mainwindow.minesite
        customer = self.mainwindow.customer

        self.add_input(field=InputField(text='Unit'), items=list(df[df.MineSite==minesite].Unit))
        self.add_input(field=InputField(text='Serial'))
        self.add_input(field=InputField(text='Model'), items=list(df.Model.unique()))
        self.add_input(field=InputField(text='MineSite', default=minesite), items=f.config['MineSite'])
        self.add_input(field=InputField(text='Customer', default=customer), items=list(df.Customer.unique()))
        self.add_input(field=InputField(text='Engine Serial', col_db='EngineSerial'))
        self.add_input(field=InputField(text='Delivery Date', dtype='date', col_db='DeliveryDate'))

        self.show()
    
class MsgBox_Advanced(QDialog):
    def __init__(self, msg='', title='', yesno=False, statusmsg=None, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.setWindowTitle(title)
        self.setMinimumSize(ui.minsize)
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
        
        hLayout = QHBoxLayout()
        hLayout.addWidget(statusbar)
        hLayout.addWidget(btn, alignment=Qt.AlignRight)
        layout.addLayout(hLayout)

def msgbox(msg='', yesno=False, statusmsg=None):
    app = ui.get_qt_app()
    dlg = MsgBox_Advanced(msg=msg, title=ui.title, yesno=yesno, statusmsg=statusmsg)
    # ui.disable_window_animations_mac(dlg)
    return dlg.exec_()

def msg_simple(msg='', icon='', infotext=None):
    app = ui.get_qt_app()
    dlg = QMessageBox()
    # ui.disable_window_animations_mac(dlg)
    dlg.setText(msg)
    dlg.setWindowTitle(ui.title)
    # dlg.setStyleSheet(minsize_ss)

    icon = icon.lower()
    
    if icon == 'critical':
        dlg.setIcon(QMessageBox.Critical)
    elif icon == 'warning':
        dlg.setIcon(QMessageBox.Warning)

    if infotext: dlg.setInformativeText(infotext)

    return dlg.exec_()

def inputbox(msg='Enter value:', dtype='text', items=None, editable=False):
    app = ui.get_qt_app()
    dlg = QInputDialog()
    dlg.resize(ui.minsize)
    dlg.setWindowTitle(ui.title)
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

def get_filepath_from_dialog(p_start):
    app = ui.get_qt_app()
    dlg = QFileDialog()
    ui.disable_window_animations_mac(dlg)

    s = dlg.getExistingDirectory(
        directory=str(p_start),
        options=QFileDialog.ShowDirsOnly | QFileDialog.DontUseNativeDialog)

    if s:
        return Path(s)
    return None

def show_item(name, parent=None):
    # show message dialog by name eg ui.show_item('InputUserName')
    app = ui.get_qt_app()
    dlg = getattr(sys.modules[__name__], name)(parent=parent)
    return dlg.exec_()