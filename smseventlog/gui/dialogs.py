import inspect

from PyQt5.QtWidgets import QFileSystemModel, QTreeView

from . import _global as gbl
from .__init__ import *
from . import formfields as ff

log = logging.getLogger(__name__)
# TODO reload ff.Combobox items on toggle - signal/slot somehow?

class InputField():
    def __init__(self, text, col_db=None, box=None, dtype='text', default=None, table=None, opr=None, enforce=False):
        if col_db is None: col_db = text.replace(' ', '')
        boxLayout = None
        f.set_self(vars())
    
    @property
    def val(self):
        return self.box.val

    @val.setter
    def val(self, val):
        self.box.val = val
    
    def set_default(self):
        if not self.box is None and not self.default is None:
            self.val = self.default

class InputForm(QDialog):
    def __init__(self, parent=None, window_title=''):
        super().__init__(parent=parent)
        mainwindow = gbl.get_mainwindow()
        settings = gbl.get_settings()
        name = self.__class__.__name__
        _names_to_avoid = ('minesite_qcombobox') # always want to use 'current' minesite
        self.setWindowTitle(window_title)
        vLayout = QVBoxLayout(self)
        formLayout = QFormLayout()
        formLayout.setLabelAlignment(Qt.AlignLeft)
        formLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        vLayout.addLayout(formLayout)
        fields = []
        items = None
        enforce_all = False

        add_okay_cancel(dlg=self, layout=vLayout)
        f.set_self(vars())
        
    def show(self):
        self.setFixedSize(self.sizeHint())

    def add_input(self, field, items=None, layout=None, checkbox=False, cb_enabled=True, index=None, btn=None):
        # Add input field to form
        text, dtype = field.text, field.dtype

        if not items is None or dtype == 'combobox':
            box = ff.ComboBox(items=items)
        elif dtype == 'text':
            box = ff.LineEdit()
        elif dtype == 'textbox':
            box = ff.TextEdit()
            box.setMaximumSize(box.sizeHint().width(), 60)
        elif dtype == 'int':
            box = ff.SpinBox(range=(0, 200000))
        elif dtype == 'date':
            box = ff.DateEdit()
        
        boxLayout = QHBoxLayout()
        boxLayout.addWidget(box)
        field.boxLayout = boxLayout
        box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        box.set_name(name=text)
        
        # add checkbox to form line to enable/disable field
        if checkbox:
            cb = ff.CheckBox(checked=cb_enabled)
            box.setEnabled(cb_enabled)
            cb.box = box # attach box to toggle later
            cb.stateChanged.connect(self.toggle_input)
            boxLayout.addWidget(cb)
            field.cb = cb
            cb.set_name(name=text)
        elif btn:
            boxLayout.addWidget(btn)
            btn.box = box
        else:
            # add spacer
            boxLayout.addSpacing(30)
        
        setattr(self, 'f{}'.format(field.text.replace(' ', '')), field)
        field.box = box
        box.field = field
        field.set_default()
        self.fields.append(field)

        if layout is None:
            layout = self.formLayout

        label = QLabel(f'{text}:')

        if index is None:
            layout.addRow(label, boxLayout)
        else:
            layout.insertRow(index, label, boxLayout)
        
        return field

    def accept_(self):
        # always access the QT base accept
        return super().accept()

    def accept(self):
        if not self.check_enforce_items():
            return

        self.items = self.get_items()
        self._save_settings()
        super().accept()
    
    def check_enforce_items(self):
        # loop all enforceable fields, make sure vals arent blank/default
        if self.enforce_all:
            fields = self.fields
        else:
            fields = list(filter(
                lambda field: field.enforce==True and isinstance(field.box.val, str), self.fields))

        for field in fields:
            if len(field.val) == 0:
                msg = f'"{field.text}" cannot be blank.'
                dlg = msg_simple(msg=msg, icon='warning')
                return False
        
        return True

    def get_items(self):
        # return dict of all field items: values
        m = {}
        for field in self.fields:
            m[field.text] = field.val
        
        return m
    
    def add_items_to_filter(self):
        # loop params, add all to parent filter
        fltr = self.parent.query.fltr
        for field in self.fields:
            if field.box.isEnabled():
                print(f'adding input | field={field.col_db}, table={field.table}')
                fltr.add(field=field.col_db, val=field.val, table=field.table, opr=field.opr)

    def toggle_input(self, state):
        # toggle input field enabled/disabled based on checkbox
        source = self.sender()
        box = source.box

        if state == Qt.Checked:
            box.setEnabled(True)
            box.select_all()
        else:
            box.setEnabled(False)

    def insert_linesep(self, i=0, layout_type='form'):
        line_sep = create_linesep(self)

        if layout_type == 'form':
            self.formLayout.insertRow(i, line_sep)

        else:
            self.vLayout.insertWidget(i, line_sep)

    @classmethod
    def _get_handled_types(cls):
        return QComboBox, QLineEdit, QTextEdit, QCheckBox, QRadioButton, QSpinBox, QSlider, QDateEdit

    @classmethod
    def _is_handled_type(cls, widget):
        return any(isinstance(widget, t) for t in cls._get_handled_types())

    def _save_settings(self):
        # save ui controls and values to QSettings
        for obj in self.children():
            if self._is_handled_type(obj):
                val = obj.val

                if not val is None:
                    self.settings.setValue(f'{self.name}_{obj.objectName()}', val)

    def _restore_settings(self):
        # set saved value back to ui control
        for obj in self.children():
            name, val = obj.objectName(), None

            if (self._is_handled_type(obj) and
                not name in self._names_to_avoid and
                not len(name) == 0):
                
                val = self.settings.value(f'{self.name}_{name}')
                if not val is None:
                    obj.val = val

    def update_statusbar(self, msg):
        if not self.mainwindow is None:
            self.mainwindow.update_statusbar(msg=msg)

class AddRow(InputForm):
    def __init__(self, parent=None, window_title='Add Item'):
        super().__init__(parent=parent, window_title=window_title)
        m = {} # need dict for extra cols not in dbm table model (eg UnitID)
        queue = []
        row = self.create_row() # kinda sketch, row is actually e, not dbt.Row
        
        f.set_self(vars())
    
    def create_row(self):
        parent = self.parent
        if not parent is None:
            table_model = parent.view.model()
            title = parent.title
            dbtable = parent.dbtable
        else:
            # Temp testing vals
            table_model = None
            title = 'Event Log'
            tablename = 'EventLog'
            dbtable = getattr(dbm, tablename)

        f.set_self(vars())
        return dbtable()
    
    def add_row_table(self, row, m=None):
        # convert row model to dict of values and append to current table
        if m is None:
            m = self.m

        m.update(f.model_dict(model=row))
        m = f.convert_dict_db_view(title=self.title, m=m, output='view')
        
        if not self.table_model is None:
            self.table_model.insertRows(m=m)
    
    def add_row_db(self, row):
        # TODO probably merge this with Row class? > update all? BULK update (with 2 component rows)
        dbt.print_model(model=row)
        db.add_row(row=row)
    
    def add_row_queue(self, row):
        # add row (model) to queue
        self.queue.append(row)
    
    def flush_queue(self):
        # bulk update all rows in self.queue to db
        update_items = [f.model_dict(row) for row in self.queue] # list of dicts

        txn = dbt.DBTransaction(table_model=self.table_model, dbtable=self.dbtable, title=self.title) \
            .add_items(update_items=update_items) \
            .update_all(operation_type='insert')
    
    def set_row_attrs(self, row, exclude=None):
        # copy values to dbmodel from current dialog field values
        if exclude is None:
            exclude = []
        elif not isinstance(exclude, list):
            exclude = [exclude]

        for field in self.fields:
            if not field.text in exclude:
                setattr(row, field.col_db, field.val)
           
    def accept_2(self):
        # not sure if need this yet
        return super().accept()
    
    def accept(self):
        super().accept()
        row = self.row
        self.set_row_attrs(row=row)
        self.add_row_db(row=row)
        self.add_row_table(row=row)

        self.parent.view.resizeRowsToContents()

class AddEmail(AddRow):
    def __init__(self, parent=None):
        super().__init__(parent=parent, window_title='Add Email')

class AddEvent(AddRow):
    def __init__(self, parent=None):
        super().__init__(parent=parent, window_title='Add Event')
        FCNumber = None
        IPF = InputField

        layout = self.vLayout
        df = db.get_df_unit()
        minesite = self.mainwindow.minesite if not self.mainwindow is None else 'FortHills'

        # Checkboxes
        cb_eventfolder = ff.CheckBox('Create Event Folder', checked=True)
        cb_tsi = ff.CheckBox('Create TSI')
        cb_fc = ff.CheckBox('Link FC')
        cb_fc.stateChanged.connect(self.create_fc)

        self.add_input(field=IPF(text='MineSite', default=minesite), items=f.config['MineSite'])
        self.add_input(field=IPF(text='Unit'), items=list(df[df.MineSite==minesite].Unit))
        self.add_input(field=IPF(text='Date', dtype='date', col_db='DateAdded'))

        # Add btn to check smr 
        btn = self.create_button('get')
        btn.clicked.connect(self.get_smr)
        self.add_input(field=IPF(text='SMR', dtype='int'), btn=btn)


        self.formLayout.addRow('', cb_eventfolder)
        self.formLayout.addRow('', cb_tsi)
        self.formLayout.addRow('', cb_fc)

        self.add_input(field=IPF(text='Title', dtype='textbox'))
        self.add_input(field=IPF(text='Failure Cause', dtype='textbox'))

        self.add_input(field=IPF(text='Warranty Status', col_db='WarrantyYN'), items=f.config['Lists']['WarrantyType'])
        self.add_input(field=IPF(text='Work Order', col_db='WorkOrder'))
        self.add_input(field=IPF(text='WO Customer', col_db='SuncorWO'))
        self.add_input(field=IPF(text='PO Customer', col_db='SuncorPO'))

        self.add_component_fields()

        self.fUnit.box.select_all()
        f.set_self(vars())
        self.show()
    
    def create_row(self):
        row = super().create_row()
        row.UID = self.create_uid()
        row.CreatedBy = self.mainwindow.username if not self.mainwindow is None else ''
        row.StatusEvent = 'Work In Progress'
        row.StatusWO = 'Open'
        row.Seg = 1
        row.Pictures = 0
        return row

    def create_button(self, name):
        btn = QPushButton(name, self)
        btn.setFixedSize(QSize(24, btn.sizeHint().height()))
        return btn
    
    def add_component_fields(self):
        # Add fields to select component/component SMR 1 + 2
        IPF = InputField

        def _add_component(text):
            field = self.add_input(field=IPF(text=text, dtype='combobox', col_db='Floc'), checkbox=True, cb_enabled=False)
            field.cb.stateChanged.connect(self.load_components)
            return field
        
        def _add_smr(text):
            btn = self.create_button('get')
            btn.clicked.connect(self.get_component_smr)
            field = self.add_input(field=IPF(text=text, dtype='int', col_db='ComponentSMR'), btn=btn)
            field.box.setEnabled(False)
            return field

        add_linesep(self.formLayout)

        for suff in ('', ' 2'):
            field_comp = _add_component(f'Component CO{suff}')
            field_smr = _add_smr(f'Component SMR{suff}')

            field_comp.box_smr = field_smr.box # lol v messy
            field_smr.box_comp = field_comp.box

        add_linesep(self.formLayout)
    
    @property
    def df_comp(self):
        if not hasattr(self, '_df_comp') or self._df_comp is None:
            self._df_comp = db.get_df_component()
        return self._df_comp
        
    def get_floc(self, component_combined):
        df = self.df_comp
        return df[df.Combined==component_combined].Floc.values[0]
   
    def load_components(self, state):
        # Reload components to current unit when component co toggled
        # Also toggle smr boxes
        source = self.sender() # source is checkbox
        box = source.box
        box_smr = box.field.box_smr

        if state == Qt.Checked:
            df = self.df_comp
            unit = self.fUnit.val
            equip_class = db.get_unit_val(unit=unit, field='EquipClass')
            s = df[df.EquipClass==equip_class].Combined
            lst = f.clean_series(s)
            box.addItems(lst)
            box.lineEdit().selectAll()
            box_smr.setEnabled(True)
        else:
            box_smr.setEnabled(False)

    def get_component_smr(self):
        source = self.sender()
        box = source.box # box is linked to btn through add_input

        df = self.df_comp
        unit, smr, date = self.fUnit.val, self.fSMR.val, self.fDate.val
        component = box.field.box_comp.val

        # get last CO from EL by floc
        floc = self.get_floc(component_combined=component)
        smr_last = db.get_smr_prev_co(unit=unit, floc=floc, date=date)

        if not smr_last is None:
            box.val = smr_last
        else:
            box.val = smr
            m = dict(Unit=unit, component=component)
            msg = f'No previous component changeouts found for:\n{f.pretty_dict(m)}\n\nSetting Component SMR to current unit SMR: {smr}'
            msg_simple(msg=msg, icon='warning')

    def get_smr(self):
        # NOTE could select all nearby dates in db and show to user
        unit, date = self.fUnit.val, self.fDate.val
        smr = db.get_smr(unit=unit, date=date)

        if not smr is None:
            self.fSMR.val = smr
        else:
            msg = f'No SMR found for\n\nUnit: {unit}\nDate: {date}'
            msg_simple(msg=msg, icon='warning')
    
    def create_uid(self):
        return str(time.time()).replace('.','')[:12]
    
    def link_fc(self):
        # add event's UID to FC in FactoryCampaign table
        unit = self.row.Unit
        row = dbt.Row(keys=dict(FCNumber=self.FCNumber, Unit=unit), dbtable=dbm.FactoryCampaign)
        row.update(vals=dict(UID=self.uid))

    def create_fc(self):
        unit = self.fUnit.val

        if self.cb_fc.isChecked():
            # TODO: This can eventually go into its own function
            df = db.get_df_fc()
            df = df[df.Unit==unit]
            prefix = 'FC '
            df['Title'] = df.FCNumber + ' - ' + df.Subject

            ok, val = inputbox(msg='Select FC:', dtype='choice', items=list(df.Title), editable=True)
            if ok:
                self.fTitle.val = prefix + val
                self.FCNumber = val.split(' - ')[0]
                
            else:
                self.cb_fc.setChecked(False)
             
    def accept(self):
        row, m = self.row, self.m
        unit = self.fUnit.val
        rows = []
        self.add_row_queue(row=row) # need to update at least row1

        # add these values to display in table
        m['Model'] = db.get_unit_val(unit=unit, field='Model')
        m['Serial'] = db.get_unit_val(unit=unit, field='Serial')
        
        # Make sure title is good
        self.fTitle.val = f.nice_title(self.fTitle.val)

        # create TSI row (row 1 only)
        if self.cb_tsi.isChecked():
            row.StatusTSI = 'Open'
            
            if not self.mainwindow is None:
                row.TSIAuthor = self.mainwindow.get_username()

        self.set_row_attrs(row=row, exclude=['Component CO 2', 'Component SMR 2'])

        # Component CO 1
        if self.fComponentCO.cb.isChecked():
            row.ComponentCO = True
            row.Floc = self.get_floc(component_combined=self.fComponentCO.box.val)
        
        self.add_row_table(row=row)

        # Component CO 2 > duplicate self.row
        if self.fComponentCO2.cb.isChecked():
            row2 = self.create_row()
            self.set_row_attrs(row=row2)

            component = self.fComponentCO2.box.val
            row2.Floc = self.get_floc(component_combined=component)
            row2.Title = f'{component} - CO'
            row2.ComponentSMR = self.fComponentSMR2.box.val
            row2.ComponentCO = True
            row2.GroupCO = True
            self.row2 = row2
            self.add_row_queue(row=row2)
            self.add_row_table(row=row2)

            row.GrouCO = True
          
        self.flush_queue()
        self.accept_()
        self.parent.view.resizeRowsToContents()

        if self.cb_fc.isChecked():
            self.link_fc()
        
        if self.cb_eventfolder.isChecked():
            from . import eventfolders as efl
            ef = efl.get_eventfolder(minesite=row.MineSite).from_model(e=row)
            ef.create_folder(ask_show=True)

class AddUnit(AddRow):
    def __init__(self, parent=None):
        super().__init__(parent=parent, window_title='Add Unit')
        df = db.get_df_unit()
        minesite = gbl.get_minesite()
        self.tablename = 'UnitID'

        self.add_input(field=InputField(text='Unit'))
        self.add_input(field=InputField(text='Serial'))
        self.add_input(field=InputField(text='Model'), items=list(df.Model.unique()))
        self.add_input(field=InputField(text='MineSite', default=minesite), items=f.config['MineSite'])
        self.add_input(field=InputField(text='Customer'), items=list(df.Customer.unique()))
        self.add_input(field=InputField(text='Engine Serial', col_db='EngineSerial'))
        self.add_input(field=InputField(text='Delivery Date', dtype='date', col_db='DeliveryDate'))

        self.show()
       
    def accept(self):
        # when model is set, check if model_base exists. If not prompt to create one
        model, unit = self.fModel.val, self.fUnit.val
        modelbase = db.get_modelbase(model=model)
        
        if modelbase is None:
            dlg = CreateModelbase(model=model, parent=self)
            ans = dlg.exec_()
            if not ans: return
            
        super().accept()
        # self.set_row_attrs(row=self.row)
        dbt.print_model(self.row)
        self.update_statusbar(f'New unit added to database: {model}, {unit}')

class CreateModelbase(AddRow):
    def __init__(self, model, parent=None):
        super().__init__(parent=parent, window_title='Create ModelBase')

        lst = [] # get list of equiptypes
        df = db.get_df_equiptype()
        lst = f.clean_series(df.EquipClass)

        text = f'No ModelBase found for: "{model}". Select an EquipClass and create a ModelBase.\n\n' \
            '(This is used for grouping models into a base folder structure. Eg "980E-4" > "980E")\n'
        label = QLabel(text)
        label.setMaximumWidth(300)
        label.setWordWrap(True)
        self.vLayout.insertWidget(0, label)

        self.add_input(field=InputField(text='Equip Class'), items=lst)
        self.add_input(field=InputField(text='Model Base'))

        self.setMinimumSize(self.sizeHint())
        f.set_self(vars())
    
    def set_row_attrs(self, row, exclude=None):
        row.Model = self.model
        super().set_row_attrs(row=row, exclude=exclude)
    
    def accept(self):
        # check model base isn't blank
        model_base = self.fModelBase.val
        if model_base.strip() == '':
            msg_simple(msg='Model Base cannot be blank!', icon='warning')
            return
        
        row = self.row
        row.Model = self.model
        self.set_row_attrs(row=row)
        self.add_row_db(row=row)

        self.accept_2()

    def create_row(self):
        # not linked to a parent table, just return a row instance of EquipType table
        return dbm.EquipType()

class InputUserName(InputForm):
    def __init__(self, parent=None):
        super().__init__(parent=parent, window_title='Enter User Name')
        self.enforce_all = True
        layout = self.vLayout
        layout.insertWidget(0, QLabel('Welcome to the SMS Event Log! \
            \nPlease enter your first/last name and work email to begin:\n'))

        self.add_input(field=InputField(text='First'))
        self.add_input(field=InputField(text='Last'))
        self.add_input(field=InputField(text='Email'))

        self.show()
    
    def accept(self):
        self.username = '{} {}'.format(self.fFirst.val, self.fLast.val).title()
        self.email = self.fEmail.val.lower()
        super().accept()
    
class TSIUserName(InputForm):
    def __init__(self, parent=None):
        super().__init__(parent=parent, window_title='Enter Password')
        self.enforce_all = True
        layout = self.vLayout
        layout.insertWidget(0, QLabel('To use the automated TSI system,\
            \nplease enter your username and password for www.komatsuamerica.net:\n'))

        self.add_input(field=InputField(text='Username'))
        self.add_input(field=InputField(text='Password'))

class ChangeMinesite(InputForm):
    def __init__(self, parent=None, window_title='Change MineSite'):
        super().__init__(parent=parent, window_title=window_title)
        lst = db.get_list_minesite()
        self.add_input(field=InputField('MineSite', default=gbl.get_minesite()), items=lst) \
            .box.select_all()

        self.show()

    def accept(self):
        super().accept()
        if not self.parent is None:
            self.parent.minesite = self.fMineSite.val

class ComponentCO(InputForm):
    def __init__(self, parent=None, window_title='Select Component'):
        super().__init__(parent=parent, window_title=window_title)

        df = db.get_df_component().copy()
        lst = f.clean_series(s=df.Combined)
        self.add_input(field=InputField('Component'), items=lst) \
            .box.select_all()
        
        f.set_self(vars())
        
    def accept(self):
        df, table_widget = self.df, self.parent
        val = self.fComponent.val
        floc = df[df.Combined==val].Floc.values[0]

        if not table_widget is None:           
            # only need to update floc in database
            row = table_widget.row
            row.update(vals=dict(Floc=floc, ComponentCO=True))
            table_widget.update_statusbar(msg=f'Component updated: {val}')
        
        super().accept()

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
            new_size = QSize(600, 800)
            details_box.setFixedSize(new_size)

        self.initial_resize = True
        return result

class MsgBox_Advanced(QDialog):
    def __init__(self, msg='', window_title='', yesno=False, statusmsg=None, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.setWindowTitle(window_title)
        self.setMinimumSize(gbl.minsize)
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

class DetailsView(QDialog):
    def __init__(self, parent=None, df=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setWindowTitle('Details View')
        self.setMinimumSize(QSize(800, 1000))
        tbl = self.create_table(df=df)
        vLayout = QVBoxLayout(self)
        vLayout.addWidget(tbl)

        # update box
        textedit = QTextEdit()

        add_okay_cancel(dlg=self, layout=vLayout)
        
        f.set_self(vars())

    def create_table(self, df):
        tbl = QTableWidget()
        # tbl.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        tbl.setFixedSize(QSize(800, 1000))
        tbl.setColumnWidth(0, 200)

        tbl.setRowCount(df.shape[0])
        tbl.setColumnCount(df.shape[1])
        tbl.setHorizontalHeaderLabels(list(df.columns))
        tbl.setVerticalHeaderLabels(list(df.index))
        tbl.horizontalHeader().setStretchLastSection(True)

        df_array = df.values
        for row in range(df.shape[0]):
            for col in range(df.shape[1]):
                val = df_array[row,col]
                val = str(val) if not val is None else ''
                tbl.setItem(row, col, QTableWidgetItem(val))
        
        tbl.resizeRowsToContents()

        tbl.cellChanged.connect(self.onCellChanged)
        return tbl

    @pyqtSlot(int, int)
    def onCellChanged(self, irow, icol):
        df, parent = self.df, self.parent
        val = self.tbl.item(irow, icol).text()
        row, col = df.index[irow], df.columns[icol]

        # update database
        dbtable = parent.get_dbtable(header=row) # transposed table
        db_row = dbt.Row(df=df, col='Value', dbtable=dbtable, title=parent.title)

        if f.isnum(val): val = float(val)

        db_row.update_single(val=val, header=row)

class FailureReport(QDialog):
    """
    Dialog to select pictures, and set cause/correction text to create pdf failure report.
    """
    def __init__(self, parent=None, p_start=None, text=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Create TSI Report')
        self.setMinimumSize(QSize(800, 800))
        self.setSizeGripEnabled(True)
        vLayout = QVBoxLayout(self)
        
        text_fields = {}
        if text is None: text = {} # default text for text fields
        if p_start is None: p_start = Path.home() / 'Desktop'
        
        dlg = QFileDialogPreview(directory=str(p_start), options=QFileDialog.DontUseNativeDialog, standalone=False)
        vLayout.addWidget(dlg)
        add_linesep(vLayout)

        f.set_self(vars())
        names = ['complaint', 'cause', 'correction', 'details']
        self.add_textbox(names=names)
        add_linesep(vLayout)

        add_okay_cancel(dlg=self, layout=vLayout)

        # TODO OilSamples, Faults, PLM?
    
    def add_textbox(self, names):
        def _add_textbox(name):
            layout = QVBoxLayout()
            layout.addWidget(QLabel(f'{name.title()}:'))
            
            textbox = QTextEdit()
            textbox.setText(self.text.get(name, ''))

            setattr(self, name, textbox)
            self.text_fields[name] = textbox
            layout.addWidget(textbox)
            self.vLayout.addLayout(layout)
       
        if not isinstance(names, list): names = [names]
        for name in names:
            _add_textbox(name)
       
    def accept(self):
        self.pics = self.dlg.selectedFiles()

        # convert dict of textbox objects to their plaintext (could also use html)
        for name, textbox in self.text_fields.items():
            self.text[name] = textbox.toPlainText()

        super().accept()

class QFileDialogPreview(QFileDialog):
    """
    Create QFileDialog with image preview
    """
    def __init__(self, parent=None, caption='', directory=None, filter=None, standalone=True, **kw):
        super().__init__(parent, caption, directory, filter, **kw)

        box = QVBoxLayout()
        if not standalone: self.disable_buttons()
 
        self.setFixedSize(self.width() + 400, self.height())
        self.setFileMode(QFileDialog.ExistingFiles)
        self.setViewMode(QFileDialog.Detail)
        self.setWindowFlags(self.windowFlags() & ~Qt.Dialog) # needed to use inside other dialog
        self.setSizeGripEnabled(False)
 
        mpPreview = QLabel("Preview", self)
        mpPreview.setFixedSize(400, 400)
        mpPreview.setAlignment(Qt.AlignCenter)
        mpPreview.setObjectName("labelPreview")
        box.addWidget(mpPreview)
 
        box.addStretch()
 
        self.layout().addLayout(box, 1, 3, 1, 1)
 
        self.currentChanged.connect(self.onChange)
        self.fileSelected.connect(self.onFileSelected)
        self.filesSelected.connect(self.onFilesSelected)

        # used to change picture on hover changed, to messy, dont need
        # for view in self.findChildren(QTreeView):
        #     if isinstance(view.model(), QFileSystemModel):
        #         tree_view = view
        #         break

        # tree_view.setMouseTracking(True)
        # tree_view.entered.connect(self.onChange)

        self._fileSelected = None
        self._filesSelected = None
        f.set_self(vars())

    def disable_buttons(self):
        # remove okay/cancel buttons from dialog, when showing in another dialog
        btn_box = self.findChild(QDialogButtonBox)
        if btn_box:
            self.layout().removeWidget(btn_box)
            btn_box.hide()
 
    def onChange(self, *args):
        if not args:
            return
        else:
            arg = args[0]

        if isinstance(arg, QModelIndex):
            index = arg
            if not index.column() == 0:
                index = index.siblingAtColumn(0)
            path = str(Path(self.directory) / index.data())
        else:
            path = arg

        pixmap = QPixmap(path)
        mpPreview = self.mpPreview
 
        if(pixmap.isNull()):
            mpPreview.setText("Preview")
        else:
            mpPreview.setPixmap(pixmap.scaled(mpPreview.width(), mpPreview.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def accept(self):
        # prevent window from being closed when part of a form
        if self.standalone:
            super().accept()

    def onFileSelected(self, file):
        self._fileSelected = file
 
    def onFilesSelected(self, files):
        self._filesSelected = files
 
    def getFileSelected(self):
        return self._fileSelected
 
    def getFilesSelected(self):
        return self._filesSelected


def msgbox(msg='', yesno=False, statusmsg=None):
    app = check_app()
    dlg = MsgBox_Advanced(msg=msg, window_title=gbl.title, yesno=yesno, statusmsg=statusmsg)
    return dlg.exec_()

def msg_simple(msg='', icon='', infotext=None):
    app = check_app()
    dlg = QMessageBox()
    dlg.setText(msg)
    dlg.setWindowTitle(gbl.title)

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
    dlg.resize(gbl.minsize)
    dlg.setWindowTitle(gbl.title)
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

def about():
    msg = f'SMS Event Log\n\nVersion: {VERSION}'
    return msg_simple(msg=msg)

def set_multiselect(dlg):
    # allow selecting multiple directories for QFileDialog. # NOTE not currently used
    from PyQt5.QtWidgets import (QFileSystemModel, QAbstractItemView, QTreeView, QListView)

    # set multiselect
    for view in dlg.findChildren((QListView, QTreeView)):
        if isinstance(view.model(), QFileSystemModel):
            view.setSelectionMode(QAbstractItemView.MultiSelection)

def get_filepath_from_dialog(p_start):
    app = check_app()

    s = QFileDialog.getExistingDirectory(
        directory=str(p_start),
        options=QFileDialog.ShowDirsOnly | QFileDialog.DontUseNativeDialog)

    if s:
        return Path(s)
    return None

def save_file(p_start=None, name=None):
    # TODO save last folder location to QSettings?
    if p_start is None: 
        p_start = Path.home() / 'Desktop'
    
    p = p_start / f'{name}.xlsx'

    app = check_app()
    s = QFileDialog.getSaveFileName(caption='Save File', directory=str(p), filter='*.xlsx', options=QFileDialog.DontUseNativeDialog)
    
    if s[0]:
        return Path(s[0])
    return None

def add_okay_cancel(dlg, layout):
    # add an okay/cancel btn box to bottom of QDialog's layout (eg self.vLayout)
    # parent = layout.parent()

    btnbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    btnbox.accepted.connect(dlg.accept)
    btnbox.rejected.connect(dlg.reject)

    layout.addWidget(btnbox, alignment=Qt.AlignBottom | Qt.AlignCenter)
    dlg.btnbox = btnbox

def create_linesep(parent=None):
    line_sep = QFrame(parent=parent)
    line_sep.setObjectName('line_sep')
    line_sep.setFrameShape(QFrame.HLine)
    line_sep.setFrameShadow(QFrame.Raised)
    # line_sep.setStyleSheet('QFrame[frameShape="4"]#line_sep {color: red; padding: 20px; padding-top: 20px; padding-bottom: 20px}')
    return line_sep

def add_linesep(layout, i=None):
    # doesn't work well with formLayout
    type_ = 'Row' if isinstance(layout, QFormLayout) else 'Widget'

    add_func = f'add{type_}'
    insert_func = f'insert{type_}'
    
    line_sep = create_linesep()

    if i is None:
        getattr(layout, add_func)(line_sep)
    else:
        getattr(layout, insert_func)(i, line_sep)

def print_children(obj, depth=0, maxdepth=3):
    tab = '\t'
    # if hasattr(obj, 'findChildren'):
    if depth > maxdepth: return

    for o in obj.children():
        type_ = str(type(o)).split('.')[-1]
        print(f'{tab * (depth + 1)}name: {o.objectName()} | type: {type_}')

        print_children(obj=o, depth=depth + 1, maxdepth=maxdepth)

def show_item(name, parent=None, *args, **kw):
    # show message dialog by name eg gbl.show_item('InputUserName')
    app = check_app()
    dlg = getattr(sys.modules[__name__], name)(parent=parent, *args, **kw)
    print(dlg.styleSheet())
    return dlg, dlg.exec_()

def check_app():
    # just need to make sure app is set before showing dialogs
    from . import startup
    app = startup.get_qt_app()
    return app
