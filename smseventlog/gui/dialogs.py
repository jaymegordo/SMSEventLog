from .__init__ import *
from . import gui as ui

log = logging.getLogger(__name__)

class InputField():
    def __init__(self, text, col_db=None, box=None, dtype='text', default=None, table=None, opr=None):
        if col_db is None: col_db = text.replace(' ', '')
        f.set_self(self, vars())
    
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
            self.set_val(val=self.default)

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

    def accept_(self):
        # always access the QT base accept
        return super().accept()

    def accept(self):
        super().accept()
        self.items = self.get_items()

    def get_items(self):
        # return dict of all field items: values
        m = {}
        for field in self.fields:
            m[field.text] = field.get_val()
        
        return m
    
    def add_items_to_filter(self):
        # loop params, add all to parent filter
        fltr = self.parent.query.fltr
        for field in self.fields:
            if field.box.isEnabled():
                print(f'adding input | field={field.col_db}, table={field.table}')
                fltr.add(field=field.col_db, val=field.get_val(), table=field.table, opr=field.opr)

    def toggle_input(self, state):
        # toggle input field enabled/disabled based on checkbox
        source = self.sender()
        box = source.box
        # TODO need to subclass QCombobox and reload items on toggle? signal/slot somehow?

        if state == Qt.Checked:
            box.setEnabled(True)
            box.setFocus()

            if isinstance(box, (QLineEdit, QTextEdit)):
                box.selectAll()
            elif isinstance(box, QComboBox):
                box.lineEdit().selectAll()

        else:
            box.setEnabled(False)

    def insert_linesep(self, i=0, layout_type='form'):
        line_sep = QFrame()
        line_sep.setFrameShape(QFrame.HLine)
        line_sep.setFrameShadow(QFrame.Raised)

        if layout_type == 'form':
            self.formLayout.insertRow(i, line_sep)
        else:
            self.vLayout.insertWidget(i, line_sep)

class AddRow(InputForm):
    def __init__(self, parent=None):
        super().__init__(parent=parent, title='Add Item')
        m = {} # need dict for extra cols not in dbm table model

        if not parent is None:
            table_model = parent.view.model()
            # tablename = parent.dbtable
            title = parent.title
            row = parent.dbtable()
        else:
            # Temp vals
            tablename = 'EventLog'
            title = 'Event Log'
            row = getattr(dbm, tablename)
        
        f.set_self(self, vars())
    
    def accept(self):
        super().accept()
        row, m = self.row, self.m
        
        # add fields to dbmodel from form fields
        for field in self.fields:
            setattr(row, field.col_db, field.get_val())
            
        # convert row model to dict of values and append to current table
        m.update(f.model_dict(model=row))
        m = f.convert_dict_db_view(title=self.title, m=m)
        self.table_model.insertRows(m=m)

        # TODO: probably merge this with Row class? > update all?
        print(int(row.UID))
        session = db.session
        session.add(row)
        session.commit()

class AddEvent(AddRow):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        FCNumber = None
        row = self.row
        row.UID = self.create_uid()
        row.CreatedBy = self.mainwindow.username if not self.mainwindow is None else ''
        row.StatusEvent = 'Work In Progress'
        row.StatusWO = 'Open'

        layout = self.vLayout
        df = db.get_df_unit()
        minesite = self.mainwindow.minesite if not self.mainwindow is None else 'FortHills'

        # Checkboxes
        cbFC = QCheckBox('FC')
        cbFC.stateChanged.connect(self.create_fc)
        cbEventFolder = QCheckBox('Create Event Folder')
        cbEventFolder.setChecked(True)

        self.add_input(field=InputField(text='MineSite', default=minesite), items=f.config['MineSite'])
        self.add_input(field=InputField(text='Unit'), items=list(df[df.MineSite==minesite].Unit))
        self.add_input(field=InputField(text='SMR', dtype='int'))
        self.add_input(field=InputField(text='Date', dtype='date', col_db='DateAdded'))

        self.formLayout.addRow('', cbFC)
        self.formLayout.addRow('', cbEventFolder)

        self.add_input(field=InputField(text='Title', dtype='textbox'))
        self.add_input(field=InputField(text='Warranty Status', col_db='WarrantyYN'), items=f.config['Lists']['WarrantyType'])
        self.add_input(field=InputField(text='Work Order', col_db='WorkOrder'))
        self.add_input(field=InputField(text='WO Customer', col_db='SuncorWO'))
        self.add_input(field=InputField(text='PO Customer', col_db='SuncorPO'))

        f.set_self(self, vars())
        self.show()
    
    def create_uid(self):
        return str(time.time()).replace('.','')[:12]
    
    def link_fc(self):
        # add event's UID to FC in FactoryCampaign table
        unit = self.row.Unit
        row = el.Row(keys=dict(FCNumber=self.FCNumber, Unit=unit), dbtable=dbm.FactoryCampaign)
        row.update(vals={'UID': self.uid})

    def create_fc(self):
        unit = self.row.Unit

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
        row, m = self.row, self.m
        unit = self.fUnit.get_val()
        m['Model'] = db.get_unit_val(unit=unit, field='Model') # add these values to display in table
        m['Serial'] = db.get_unit_val(unit=unit, field='Serial')
        el.print_model(model=row)

        super().accept()

        if self.cbFC.isChecked():
            self.link_fc()
        
        if self.cbEventFolder.isChecked():
            ef = fl.EventFolder(e=row)
            ef.create_folder(ask_show=True)

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

class InputUserName(InputForm):
    def __init__(self, parent=None):
        super().__init__(parent=parent, title='Enter User Name')
        layout = self.vLayout
        layout.insertWidget(0, QLabel('Welcome to the SMS Event Log! \
            \nPlease enter your first and last name to begin:\n'))

        self.add_input(field=InputField(text='First'))
        self.add_input(field=InputField(text='Last'))
        self.show()
    
class TSIUserName(InputForm):
    def __init__(self, parent=None):
        super().__init__(parent=parent, title='Enter Password')
        # self.setMaximumWidth(200)
        layout = self.vLayout
        layout.insertWidget(0, QLabel('To use the automated TSI system,\nplease enter your username and password for www.komatsuamerica.net:\n'))

        self.add_input(field=InputField(text='Username'))
        self.add_input(field=InputField(text='Password'))
        self.show()

    def check_val(self, val_name):
        # check username and password
        val = self.items[val_name].strip()
        ans = val if len(val) > 0 else False
        return ans

    def accept(self):
        # check username and password, if good save to mainwindow's QSettings
        self.items = self.get_items()
        username, password = self.check_val('Username'), self.check_val('Password')

        if not (username or password):
            msg = 'Bad username or password!'
            msg_simple(msg=msg, icon='critical')
            return False
        else:
            return super().accept()

class ChangeMinesite(InputForm):
    def __init__(self, parent=None, title='Change MineSite'):
        super().__init__(parent=parent, title=title)
        lst = db.get_list_minesite()
        self.add_input(field=InputField('MineSite', default=ui.get_minesite()), items=lst)

        self.fMineSite.box.setFocus()
        self.show()

    def accept(self):
        super().accept()
        if not self.parent is None:
            self.parent.minesite = self.fMineSite.get_val()

class ComponentCO(InputForm):
    def __init__(self, parent=None, title='Select Component'):
        super().__init__(parent=parent, title=title)
        # TODO model > equipclass

        df = db.get_df_component()
        lst = f.clean_series(s=df.Combined)
        self.add_input(field=InputField('Component'), items=lst)

        f.set_self(self, vars())

    def accept(self):
        super().accept()
        df = self.df
        val = self.fComponent.get_val()
        print(val)
        floc = df[df.Combined==val].Floc.values[0]
        print(floc)

        if not self.parent is None:
            row = self.parent.view.row_from_activerow()
            row.update(vals=dict(Floc=floc, ComponentCO=True))

class BiggerBox(QMessageBox):
    # Qmessagebox that resizes x% bigger than the default
    def __init__(self, resize_pct=1.5, *args, **kwargs):            
        super().__init__(*args, **kwargs)
        self.setSizeGripEnabled(True)
        self.initial_resize = False
        self.resize_pct = resize_pct

    def resizeEvent(self, event):
        result = super().resizeEvent(event)
        if self.initial_resize: return result

        # for label in self.findChildren(QLabel):
        #     size_hint = label.sizeHint()
        #     label.setFixedSize(QSize(size_hint.width() * self.resize_pct, size_hint.height()))

        details_box = self.findChild(QTextEdit)
        if not details_box is None:
            size_hint = details_box.sizeHint()
            new_size = QSize(600, size_hint.height())
            details_box.setFixedSize(new_size)

        self.initial_resize = True
        return result

class MsgBox_Advanced(QDialog):
    def __init__(self, msg='', title='', yesno=False, statusmsg=None, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.setWindowTitle(title)
        self.setMinimumSize(ui.minsize)
        self.setMaximumWidth(1000)

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

class ErrMsg(QMessageBox):
    def __init__(self, msg='', details='', parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Error')
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFixedSize(400, 400)
        self.content = QWidget()
        # self.content.setFixedSize(QSize(400, 400))
        scroll.setWidget(self.content)
        lay = QVBoxLayout(self.content)

        lay.addWidget(QLabel(details, self))
        self.layout().addWidget(scroll, 0, 0, 1, self.layout().columnCount())
        # self.layout().addWidget(QLabel(msg, self), 0, 0, 1, 1)
      
        # self.layout().addWidget(scroll)

class ErrMsg2(QDialog):
    def __init__(self, msg='', details='', parent=None):
        super().__init__(parent=parent)

        self.setWindowTitle('Error')
        vLayout = QVBoxLayout(self)

        label = QLabel(msg, self)
        vLayout.addWidget(label)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFixedSize(QSize(400, 400))
        label = QLabel(details, self)
        scroll.setWidget(label)
        vLayout.addWidget(scroll)

        btn = QPushButton('Okay', self)
        btn.setMaximumWidth(100)
        btn.clicked.connect(self.close)
        vLayout.addWidget(btn)


def msgbox(msg='', yesno=False, statusmsg=None):
    app = check_app()
    dlg = MsgBox_Advanced(msg=msg, title=ui.title, yesno=yesno, statusmsg=statusmsg)
    return dlg.exec_()

def msg_simple(msg='', icon='', infotext=None):
    app = check_app()
    dlg = QMessageBox()
    dlg.setText(msg)
    dlg.setWindowTitle(ui.title)

    icon = icon.lower()
    
    if icon == 'critical':
        dlg.setIcon(QMessageBox.Critical)
    elif icon == 'warning':
        dlg.setIcon(QMessageBox.Warning)

    if infotext: dlg.setInformativeText(infotext)

    return dlg.exec_()

def inputbox(msg='Enter value:', dtype='text', items=None, editable=False):
    app = check_app()
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
    app = check_app()
    dlg = QFileDialog()
    ui.disable_window_animations_mac(dlg)

    s = dlg.getExistingDirectory(
        directory=str(p_start),
        options=QFileDialog.ShowDirsOnly | QFileDialog.DontUseNativeDialog)

    if s:
        return Path(s)
    return None

def show_item(name, parent=None, *args, **kw):
    # show message dialog by name eg ui.show_item('InputUserName')
    app = check_app()
    dlg = getattr(sys.modules[__name__], name)(parent=parent, *args, **kw)
    return dlg.exec_()

def check_app():
    # just need to make sure app is set before showing dialogs
    from . import startup
    app = startup.get_qt_app()
    return app