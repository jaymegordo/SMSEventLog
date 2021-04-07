import inspect
import re

from PyQt5.QtWidgets import QFileSystemModel, QTreeView

from . import _global as gbl
from . import formfields as ff
from .__init__ import *

log = getlog(__name__)
# TODO reload ff.Combobox items on toggle - signal/slot somehow?

def add_items_to_filter(field, fltr):
    """Add field items to query filter
    - Can be called from dialog, or table's persistent filter"""
    if field.box.isEnabled():
        print(f'adding input | field={field.col_db}, table={field.table}')
        fltr.add(field=field.col_db, val=field.val, table=field.table, opr=field.opr)


class InputField():
    def __init__(self, text, col_db=None, box=None, dtype='text', default=None, table=None, opr=None, enforce=False, like=False):
        if col_db is None:
            col_db = text.replace(' ', '')

        boxLayout = None
        f.set_self(vars())
    
    @property
    def val(self):
        val = self.box.val
        
        # make any value 'like'
        if self.like:
            val = f'*{val}*'

        return val

    @val.setter
    def val(self, val):
        self.box.val = val
    
    def set_default(self):
        if not self.box is None and not self.default is None:
            self.val = self.default

class BaseDialog(QDialog):
    def __init__(self, parent=None, window_title=''):
        super().__init__(parent=parent)
        self.setWindowTitle(window_title)
        mainwindow = gbl.get_mainwindow()
        settings = gbl.get_settings()
        minesite = gbl.get_minesite()
        mw = mainwindow
        vLayout = QVBoxLayout(self)

        f.set_self(vars())

    def show(self):
        # NOTE should actually be max of window height/width, otherwise dialog can overflow screen
        self.setFixedSize(self.sizeHint())
        return super().show()

    def update_statusbar(self, msg, *args, **kw):
        if not self.mainwindow is None:
            self.mainwindow.update_statusbar(msg=msg, *args, **kw)

class InputForm(BaseDialog):
    def __init__(self, parent=None, window_title=''):
        super().__init__(parent=parent, window_title=window_title)
        name = self.__class__.__name__
        _names_to_avoid = ('minesite_qcombobox') # always want to use 'current' minesite
        _save_items = tuple()

        # NOTE could make formlayout reusable other places (eg oil samples in failure report)
        formLayout = QFormLayout()
        formLayout.setLabelAlignment(Qt.AlignLeft)
        formLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.vLayout.addLayout(formLayout)
        fields = []
        items = None
        enforce_all = False

        add_okay_cancel(dlg=self, layout=self.vLayout)
        f.set_self(vars())

    def add_input(self, field, items=None, layout=None, checkbox=False, cb_enabled=True, index=None, btn=None, tooltip=None, cb_spacing=None, enabled=True):
        # Add input field to form
        text, dtype = field.text, field.dtype

        if not items is None or dtype == 'combobox':
            box = ff.ComboBox(items=items)
            box.setMaximumWidth(300)
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
            cb.stateChanged.connect(self.toggle)
            if cb_spacing:
                boxLayout.addSpacing(cb_spacing)

            boxLayout.addWidget(cb)
            field.cb = cb
            cb.set_name(name=text)
        elif btn:
            # btn.setFixedSize(btn.size)
            boxLayout.addWidget(btn)
            btn.box = box
        else:
        #     # add spacer
            box.setEnabled(enabled)
        
        setattr(self, 'f{}'.format(field.text.replace(' ', '')), field)
        field.box = box
        box.field = field
        field.set_default()
        self.fields.append(field)

        if layout is None:
            layout = self.formLayout

        label = QLabel(f'{text}:')
        if not tooltip is None:
            label.setToolTip(tooltip)

        if index is None:
            layout.addRow(label, boxLayout)
        else:
            layout.insertRow(index, label, boxLayout)
        
        return field

    def accept_(self):
        # always access the QT base accept
        return super().accept()

    def accept(self, save_settings=True):
        if not self.check_enforce_items():
            return

        self.items = self.get_items()
        
        if save_settings:
            self._save_settings()
        super().accept()
    
    def check_enforce_items(self):
        """Loop all enforceable fields, make sure vals arent blank/default"""
        if self.enforce_all:
            fields = self.fields
        else:
            fields = list(filter(
                lambda field: field.enforce==True and isinstance(field.box.val, str) and field.box.isEnabled(), self.fields))

        for field in fields:
            if len(field.val) == 0:
                msg = f'"{field.text}" cannot be blank.'
                dlg = msg_simple(msg=msg, icon='warning')
                field.box.select_all()
                return False
        
        return True

    def get_items(self, lower=False):
        """Return dict of all {field items: values}"""
        m = {}
        for field in self.fields:
            m[field.text] = field.val

        if lower:
            m = {k.lower(): v for k, v in m.items()}
        
        return m
    
    def _add_items_to_filter(self):
        # loop params, add all to parent filter
        fltr = self.parent.query.fltr
        for field in self.fields:
            add_items_to_filter(field=field, fltr=fltr)

    def toggle(self, state):
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
        """Save ui controls and values to QSettings"""
        for obj in self.children():
            name = obj.objectName()
            if self._is_handled_type(obj) or name in self._save_items:
                val = obj.val

                if not val is None:
                    self.settings.setValue(f'dlg_{self.name}_{name}', val)

    def _restore_settings(self):
        """Set saved value back to ui control"""
        for obj in self.children():
            name, val = obj.objectName(), None

            if (self._is_handled_type(obj) and
                not name in self._names_to_avoid and
                not len(name) == 0) or name in self._save_items:
                
                val = self.settings.value(f'dlg_{self.name}_{name}')
                if not val is None:
                    obj.val = val

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

        m.update(dbt.model_dict(model=row))
        m = f.convert_dict_db_view(title=self.title, m=m, output='view')
        
        if not self.table_model is None:
            self.table_model.insertRows(m=m, select=True)
       
    def add_row_queue(self, row):
        # add row (model) to queue
        self.queue.append(row)
    
    def flush_queue(self):
        # bulk update all rows in self.queue to db
        update_items = [dbt.model_dict(row) for row in self.queue] # list of dicts

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
            if not field.text in exclude and field.box.isEnabled():
                setattr(row, field.col_db, field.val)
           
    def accept_2(self):
        # not sure if need this yet
        return super().accept()
    
    def accept(self):
        super().accept()
        row = self.row
        self.set_row_attrs(row=row)
        # dbt.print_model(row)

        if not db.add_row(row=row):
            self.update_statusbar('Failed to add row to database.', warn=True)
            return False

        self.add_row_table(row=row)

        self.parent.view.resizeRowsToContents()
        return True # row successfully added to db

class AddEmail(AddRow):
    def __init__(self, parent=None):
        super().__init__(parent=parent, window_title='Add Email')
        IPF = InputField
        self.add_input(field=IPF(text='MineSite', default=gbl.get_minesite()), items=f.config['MineSite'])
        self.add_input(field=IPF(text='Email'))
        self.add_input(field=IPF(text='User Group', default=self.mw.u.usergroup), items=db.domain_map.keys())
    
    def accept(self):
        # TODO build a more generic message for adding new rows
        super().accept()
        m = self.items
        self.update_statusbar(f'New email added to database: {m.get("MineSite", None)}, {m.get("Email", None)}')

class AddEvent(AddRow):
    def __init__(self, parent=None):
        super().__init__(parent=parent, window_title='Add Event')
        FCNumber = None
        IPF, add = InputField, self.add_input
        is_cummins = parent.u.is_cummins if not parent is None else False
        self._save_items = ('unit_qcombobox',)

        layout = self.vLayout
        df = db.get_df_unit()

        add(field=IPF(text='MineSite', default=self.minesite), items=f.config['MineSite'])
        add(field=IPF(text='Unit', enforce=True), items=list(df[df.MineSite==self.minesite].Unit))
        add(field=IPF(text='Date', dtype='date', col_db='DateAdded'))

        # Add btn to check smr 
        btn = self.create_button('Get SMR')
        btn.clicked.connect(self.get_smr)
        self.add_input(field=IPF(text='SMR', dtype='int'), btn=btn)

        if not is_cummins:
            # Checkboxes
            cb_eventfolder = ff.CheckBox('Create Event Folder', checked=True)
            # cb_onedrive = ff.CheckBox('Create OneDrive Folder', checked=True)
            cb_tsi = ff.CheckBox('Create TSI')
            
            # FC
            cb_fc = ff.CheckBox('Link FC')
            cb_fc.stateChanged.connect(self.create_fc)
            btn_open_fcs = btn = self.create_button('Open FCs')
            btn_open_fcs.setToolTip('View all open FCs for current unit.')
            btn_open_fcs.clicked.connect(self.show_open_fcs)
            box_fc = QHBoxLayout()
            box_fc.addWidget(cb_fc)
            box_fc.addWidget(btn_open_fcs)

            # outstanding FCs
            box_fc_out = QHBoxLayout()
            label_fc = QLabel('Outstanding FCs: ')
            label_fc_m = QLabel('M: ')
            label_fc_other = QLabel('Other: ')
            box_fc_out.addWidget(label_fc)
            box_fc_out.addStretch(1)
            box_fc_out.addWidget(label_fc_m)
            box_fc_out.addWidget(label_fc_other)

            # cb_eventfolder.stateChanged.connect(self.toggle_ef)

            self.formLayout.addRow('', cb_eventfolder)
            # self.formLayout.addRow('', cb_onedrive)
            self.formLayout.addRow('', cb_tsi)

            add_linesep(self.formLayout)
            self.formLayout.addRow('', box_fc)
            self.formLayout.addRow('', box_fc_out)
            add_linesep(self.formLayout)

        add(field=IPF(text='Title', dtype='textbox', enforce=True))
        add(field=IPF(text='Failure Cause', dtype='textbox'))

        # Warranty Status
        if is_cummins:
            wnty_default = 'WNTY'
            list_name = 'WarrantyTypeCummins'
        else:
            list_name = 'WarrantyType'
            wnty_default = 'Yes'

        add(
            field=IPF(
                text='Warranty Status',
                col_db='WarrantyYN',
                default=wnty_default),
            items=f.config['Lists'][list_name])

        add(field=IPF(text='Work Order', col_db='WorkOrder'))
        add(field=IPF(text='WO Customer', col_db='SuncorWO'))
        add(field=IPF(text='PO Customer', col_db='SuncorPO'))

        self.add_component_fields()

        self._restore_settings()
        self.fUnit.box.select_all()
        f.set_self(vars())
        
        self.accepted.connect(self.close)
        self.rejected.connect(self.close)
        self.fUnit.box.currentIndexChanged.connect(self.update_open_fc_labels)
        self.update_open_fc_labels()
        self.show()

    def update_open_fc_labels(self):
        """Update outstanding FC labels for M and Other when unit changed"""
        if self.is_cummins:
            return # fc labels not implemented for cummins

        unit = self.fUnit.val

        s = db.get_df_fc(default=True, unit=unit) \
            .groupby(['Type']).size()

        count_m = s.get('M', 0)
        count_other = sum(s[s.index != 'M'].values)

        self.label_fc_m.setText(f'M: {count_m}')
        self.label_fc_other.setText(f'Other: {count_other}')

        color = '#ff5454' if count_m > 0 else 'white'
        self.label_fc_m.setStyleSheet(f"""QLabel {{color: {color}}}""")

    def toggle_ef(self, state):
        """Toggle OneDrive folder when EventFolder change"""
        # source = self.sender()
        # box = source.box
        cb = self.cb_onedrive

        if state == Qt.Checked:
            cb.setEnabled(True)
        else:
            cb.setEnabled(False)

    @pyqtSlot(int)
    def component_changed(self, ix):
        # Update Title text when Component selected in combobox
        combo = self.sender()
        val = combo.val
        if not val.strip() == '':
            self.fTitle.val = f'{val} - CO'

    def create_row(self):
        row = super().create_row()
        row.UID = self.create_uid()
        row.CreatedBy = self.mainwindow.username if not self.mainwindow is None else ''
        row.StatusEvent = 'Work In Progress'
        row.StatusWO = 'Open'
        row.Seg = 1
        row.Pictures = 0

        return row

    def create_button(self, name, width=80):
        btn = QPushButton(name, self)
        btn.setFixedSize(QSize(width, btn.sizeHint().height()))
        return btn
    
    def add_component_fields(self):
        # Add fields to select component/component SMR 1 + 2
        IPF = InputField

        def _add_component(text):
            field = self.add_input(
                field=IPF(
                    text=text,
                    dtype='combobox',
                    col_db='Floc',
                    enforce=True),
                checkbox=True,
                cb_enabled=False)

            field.cb.stateChanged.connect(self.load_components)
            return field

        def _add_removal(text):
            field = self.add_input(
                field=IPF(
                    text=text,
                    dtype='combobox',
                    col_db='SunCOReason',
                    enforce=True),
                enabled=False)

            return field
        
        def _add_smr(text):
            btn = self.create_button('Get SMR')
            btn.clicked.connect(self.get_component_smr)
            field = self.add_input(field=IPF(text=text, dtype='int', col_db='ComponentSMR'), btn=btn)
            field.box.setEnabled(False)
            return field

        add_linesep(self.formLayout)

        for suff in ('', ' 2'):
            field_comp = _add_component(f'Component CO{suff}')
            field_smr = _add_smr(f'Component SMR{suff}')
            field_removal = _add_removal(f'Removal Reason{suff}')

            field_comp.box_smr = field_smr.box # lol v messy
            field_smr.box_comp = field_comp.box
            field_comp.box_removal = field_removal.box

        add_linesep(self.formLayout)
        self.fComponentCO.box.currentIndexChanged.connect(self.component_changed)
    
    @property
    def df_comp(self):
        if not hasattr(self, '_df_comp') or self._df_comp is None:
            self._df_comp = db.get_df_component()
        return self._df_comp
        
    def get_floc(self, component_combined):
        df = self.df_comp
        return df[df.Combined==component_combined].Floc.values[0]
   
    def load_components(self, state, *args):
        """Reload components to current unit when component co toggled
        - Also toggle smr boxes"""

        source = self.sender() # source is checkbox
        box = source.box
        box_smr = box.field.box_smr
        box_removal = box.field.box_removal

        if state == Qt.Checked:
            df = self.df_comp
            unit = self.fUnit.val
            equip_class = db.get_unit_val(unit=unit, field='EquipClass')
            s = df[df.EquipClass==equip_class].Combined
            lst = f.clean_series(s)
            box.set_items(lst)

            # add removal reason items
            lst_removal = f.config['Lists']['RemovalReason']
            box_removal.set_items(lst_removal)
            # box_removal.val = 'High Hour Changeout'
            box_removal.val = ''
            box_removal.setEnabled(True)

            box.lineEdit().selectAll()
            box_smr.setEnabled(True)
            box_removal.setEnabled(True)
        else:
            box_smr.setEnabled(False)
            box_removal.setEnabled(False)

    def get_component_smr(self):
        source = self.sender()
        box = source.box # box is linked to btn through add_input

        df = self.df_comp
        unit, smr, date = self.fUnit.val, self.fSMR.val, self.fDate.val
        component = box.field.box_comp.val

        # spinbox returns None if val is 0
        if smr is None:
            smr = 0

        if smr <= 0:
            msg = f'Set Unit SMR first!'
            msg_simple(msg=msg, icon='warning')
            return

        # get last CO from EL by floc
        floc = self.get_floc(component_combined=component)
        smr_last = smr - db.get_smr_prev_co(unit=unit, floc=floc, date=date)

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
            msg = f'No SMR found for\n\nUnit: {unit}\nDate: {date}\n\nNote - Daily SMR values are not uploaded to the database until 12:20 MST.'
            msg_simple(msg=msg, icon='warning')
    
    def create_uid(self):
        return str(time.time()).replace('.','')[:12]
    
    def show_open_fcs(self):
        """Toggle open FCs dialog for current unit"""
        if not hasattr(self, 'dlg_fc') or self.dlg_fc is None:
            unit = self.fUnit.val
            dlg_fc = UnitOpenFC(parent=self, unit=unit)
            
            # move fc top left to AddEvent top right
            dlg_fc.move(self.frameGeometry().topRight())
            dlg_fc.show()
            self.dlg_fc = dlg_fc
        else:
            self.dlg_fc.close()
            self.dlg_fc = None
    
    def link_fc(self):
        """Add event's UID to FC in FactoryCampaign table"""
        unit, uid = self.row.Unit, self.row.UID
        row = dbt.Row(keys=dict(FCNumber=self.FCNumber, Unit=unit), dbtable=dbm.FactoryCampaign)
        row.update(vals=dict(UID=uid))

    def create_fc(self):
        """Show dialog to select FC from list"""
        unit = self.fUnit.val

        if self.cb_fc.isChecked():
            df = db.get_df_fc(default=True, unit=unit)
            prefix = 'FC '

            ok, val = inputbox(msg='Select FC:', dtype='choice', items=list(df.Title), editable=True)
            if ok:
                self.fTitle.val = prefix + val
                self.FCNumber = val.split(' - ')[0]
                
            else:
                self.cb_fc.setChecked(False)
             
    def accept(self):
        """AddEvent accept adds rows differently (can queue multiple)
        - just bypass everthing and call base qt accept"""
        row, m = self.row, self.m
        unit = self.fUnit.val
        rows = []

        if not self.check_enforce_items():
            return
        
        self.add_row_queue(row=row) # need to update at least row1

        if not unit_exists(unit=unit): return

        # add these values to display in table
        m['Model'] = db.get_unit_val(unit=unit, field='Model')
        m['Serial'] = db.get_unit_val(unit=unit, field='Serial')
        
        # Make sure title is good
        self.fTitle.val = f.nice_title(self.fTitle.val)

        if self.is_cummins:
            row.IssueCategory = 'Engine'
        else:
            # create TSI row (row 1 only)
            if self.cb_tsi.isChecked():
                row.StatusTSI = 'Open'
                
                if not self.mainwindow is None:
                    row.TSIAuthor = self.mainwindow.get_username()

        self.set_row_attrs(
            row=row,
            exclude=['Component CO 2', 'Component SMR 2', 'Removal Reason 2'])

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

        if not self.is_cummins:
            if self.cb_fc.isChecked():
                self.link_fc()
            
            if self.cb_eventfolder.isChecked():
                from .. import eventfolders as efl
                ef = efl.EventFolder.from_model(e=row)
                ef.create_folder(ask_show=True)

    @classmethod
    def _get_handled_types(cls):
        """Don't save any settings except unit_qcombobox"""
        return tuple()

    def closeEvent(self, event):
        """Reimplement just to close the FC dialog too, couldn't find a better way"""
        try: self.dlg_fc.close()
        except: pass

        self._save_settings()
        return super().closeEvent(event)

class AddUnit(AddRow):
    def __init__(self, parent=None):
        super().__init__(parent=parent, window_title='Add Unit')
        df = db.get_df_unit()
        self.tablename = 'UnitID'

        self.add_input(field=InputField(text='Unit'))
        self.add_input(field=InputField(text='Serial'))
        self.add_input(field=InputField(text='Model'), items=list(df.Model.unique()))
        self.add_input(field=InputField(text='MineSite', default=self.minesite), items=f.config['MineSite'])
        self.add_input(field=InputField(text='Customer'), items=list(df.Customer.unique()))
        self.add_input(field=InputField(text='Engine Serial'))
        self.add_input(field=InputField(text='Delivery Date', dtype='date'))

        self.show()
       
    def accept(self):
        # when model is set, check if model_base exists. If not prompt to create one
        model, unit = self.fModel.val, self.fUnit.val
        modelbase = db.get_modelbase(model=model)
        
        if modelbase is None:
            dlg = CreateModelbase(model=model, parent=self)
            if not dlg.exec_():
                return
            
        if super().accept():
            self.update_statusbar(f'New unit added to database: {model}, {unit}', success=True)

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
        db.add_row(row=row)

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
    
class PasswordPrompt(InputForm):
    def __init__(self, id_type='Username', prompt=''):
        super().__init__(window_title='Input Credentials')
        self.enforce_all = True
        layout = self.vLayout
        prompt = f'{prompt}:\n\n(Passwords are always encrypted before storage).\n'
        layout.insertWidget(0, QLabel(prompt))

        self.add_input(field=InputField(text=id_type.title()))
        self.add_input(field=InputField(text='Password'))

class CustomFC(InputForm):
    def __init__(self, **kw):
        super().__init__(window_title='Create Custom FC')
        add, IPF = self.add_input, InputField

        text = f'Enter list or range of units to create a custom FC.\n\
        \nRanges must be defined by two dashes "--", Eg)\nPrefix: F\nUnits: 302--310, 312, 315--317\n\n'
        label = QLabel(text)
        label.setMaximumWidth(300)
        label.setWordWrap(True)
        self.vLayout.insertWidget(0, label)

        add(field=IPF(text='FC Number', enforce=True))
        add(field=IPF(text='Prefix'))
        add(field=IPF(text='Units', enforce=True))
        add(field=IPF(text='Subject', enforce=True))
        add(field=IPF(text='Type'), items=['M', 'FAF', 'DO', 'FT'])
        add(field=IPF(text='Release Date', dtype='date', col_db='ReleaseDate'))
        add(field=IPF(text='Expiry Date', dtype='date', col_db='ExpiryDate'))
    
    def accept(self):
        if not self.check_enforce_items():
            return

        from ..data import factorycampaign as fc
        units = fc.parse_units(units=self.fUnits.val, prefix=self.fPrefix.val)
        self.units = units

        # units have incorrect input
        if not units:
            return
        
        units_bad = db.units_not_in_db(units=units)
        if units_bad:
            # tried with units which don't exist in db
            msg = f'The following units do not exist in the database. Please add them then try again:\n{units_bad}'
            msg_simple(msg=msg, icon='warning')
            return
        
        fc_number = self.fFCNumber.val
        lst_units = '\n'.join(units)
        msg = f'Create new FC "{fc_number}"?\n\nUnits:\n{lst_units}'
        if not msgbox(msg=msg, yesno=True):
            return
        
        super().accept(save_settings=False)

class TSIUserName(PasswordPrompt):
    def __init__(self):
        prompt = 'To use the automated TSI system,\
            \nplease enter your username and password for www.komatsuamerica.net'

        super().__init__(prompt=prompt)

class SMSUserName(PasswordPrompt):
    def __init__(self):
        prompt = 'Please enter your SMS username (email) and password'

        super().__init__(prompt=prompt)

class ExchangeLogin(PasswordPrompt):
    def __init__(self, parent=None):
        prompt = 'Please enter your Exchange email and password'

        super().__init__(id_type='email', prompt=prompt)

class SuncorConnect(PasswordPrompt):
    def __init__(self, parent=None):
        prompt = 'Please enter your Suncor uesrname (without @email.com), password, and 4-6 digit token pin'

        super().__init__(prompt=prompt)

        self.add_input(field=InputField(text='Token'))

class ChangeMinesite(InputForm):
    def __init__(self, parent=None, window_title='Change MineSite'):
        super().__init__(parent=parent, window_title=window_title)
        lst = db.get_list_minesite()
        self.add_input(field=InputField('MineSite', default=self.minesite), items=lst) \
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
    """Qmessagebox that resizes detailed text QTextEdit"""
    def __init__(self, detailed_text=None, *args, **kwargs):            
        super().__init__(*args, **kwargs)
        self.setSizeGripEnabled(True)
        self.initial_resize = False

        if not detailed_text is None:
            self.setDetailedText(detailed_text)

        f.set_self(vars())

    def resizeEvent(self, event):
        result = super().resizeEvent(event)
        if self.initial_resize:
            return result # only need to resize first time msg is loaded

        details_box = self.findChild(QTextEdit)
        if not details_box is None:

            # adjust length of details box by number of lines
            num_lines = len(self.detailed_text.split('\n'))
            font_size = f.config_platform['font size']
            height = num_lines * (font_size + 7)
            new_size = QSize(800, min(height, 600))
            details_box.setFixedSize(new_size)

        self.initial_resize = True
        return result

class ErrMsg(BiggerBox):
    def __init__(self, detailed_text=None, *args, **kw):
        super().__init__(detailed_text=detailed_text, icon=QMessageBox.Critical, *args, **kw)
        self.setWindowTitle('Error')

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

class DialogTableWidget(QTableWidget):
    """Simple table widget to display as a pop-out dialog"""
    def __init__(self, df=None, query=None, editable=False, name='table', col_widths=None, scroll_bar=False, **kw):
        super().__init__()
        self.setObjectName(name)
        self.formats = {}
        self.query = query

        self.setColumnCount(df.shape[1])
        self.setHorizontalHeaderLabels(list(df.columns))

        if col_widths:
            self.min_width = sum(col_widths.values())
            for col, width in col_widths.items():
                self.setColumnWidth(df.columns.get_loc(col), width)

        if not editable:
            self.setEditTriggers(QTableWidget.NoEditTriggers)

        self.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        if not scroll_bar:
            self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        f.set_self(vars())
    
    def sizeHint(self): 
        """"Sketch, but have to override size width"""
        size = super().sizeHint()

        if hasattr(self, 'min_width'):
            width = self.min_width + 34
            if self.scroll_bar:
                width += 15 # width of scrollbar

            return QSize(width, size.height())
        else:
            return size
    
    def set_formats(self, df):
        date_cols = df.dtypes[df.dtypes=='datetime64[ns]'].index.to_list()
        int_cols = df.dtypes[df.dtypes=='Int64'].index.to_list()
        self.formats.update({col: '{:%Y-%m-%d}' for col in date_cols})
        self.formats.update({col: '{:,.0f}' for col in int_cols})

    def display_data(self, df, resize_cols=False):
        if df is None:
            return

        self.set_formats(df=df)
        self.setRowCount(df.shape[0])
        self.setVerticalHeaderLabels(list(df.index.astype(str)))

        # set delegate for column alignment based on dtype
        from .delegates import TableWidgetDelegate
        delegate = TableWidgetDelegate(parent=self, df=df)
        self.setItemDelegate(delegate)

        df_display = f.df_to_strings(df=df, formats=self.formats)

        query = self.query
        if not query is None:
            stylemap = query.get_stylemap(df=df)
            if stylemap is None:
                return

            bg, text = stylemap[0], stylemap[1]

        for irow, row in enumerate(df.index):
            for icol, col in enumerate(df.columns):
              
                item = QTableWidgetItem(str(df_display.loc[row, col]))

                # set background and text colors
                if not query is None:
                    color_bg = bg[col].get(row, None)
                    color_text = text[col].get(row, None)

                    if color_bg: item.setBackground(color_bg)
                    if color_text: item.setForeground(color_text)

                self.setItem(irow, icol, item)

        if resize_cols:
            self.resizeColumnsToContents()

        self.resizeRowsToContents()
        self.adjustSize()

class TableDialog(BaseDialog):
    """Base class dialog with table widget for quick/temp table display"""
    def __init__(self, df=None, cols : Union[dict, list]=None, name='table', parent=None, _show=False, simple_table=True, editable=False, window_title='SMS Event Log', maximized=False, **kw):
        super().__init__(parent, window_title=window_title)

        # auto resize cols if no dict of col_widths
        if isinstance(cols, dict):
            col_widths = cols
            cols = cols.keys()
            resize_cols = False
        else:
            col_widths = None
            resize_cols = True

            if not df is None:
                cols = df.columns.tolist()

        # init table with default cols
        if simple_table:
            tbl = DialogTableWidget(
                df=pd.DataFrame(columns=cols),
                col_widths=col_widths,
                name=name,
                scroll_bar=True,
                **kw)
        else:
            # use full TableView for filters/line highlighting etc
            from . import tables as tbls
            self.query = kw.get('query', None)
            tbl = tbls.TableView(parent=self, default_headers=cols, editable=editable)

        self.vLayout.addWidget(tbl)

        add_okay_cancel(dlg=self, layout=self.vLayout)

        f.set_self(vars())

        if _show:
            self.load_table(df=df)
        
        if maximized:
            self.showMaximized()

    def load_table(self, df):
        tbl = self.tbl
        tbl.display_data(df, resize_cols=self.resize_cols)
        tbl.setFocus()
        self.adjustSize()
    
    def add_buttons(self, *btns, func=None):
        """Add button widgets to top of table

        Parameters
        ----------
        *btns : ff.FormFields
            button widgets to add
        func : callable, optional
            function to trigger on value changed, default None
            - NOTE could make this a dict of name : func
        """        
        btn_controls = QHBoxLayout()

        for item in btns:

            # add trigger function
            if not func is None:
                item.changed.connect(func)

            btn_controls.addWidget(item)

        btn_controls.addStretch(1) # force buttons to right side
        self.vLayout.insertLayout(0, btn_controls)

        f.set_self(vars())

class ACInspectionsDialog(TableDialog):
    """Show SMR history per unit"""

    def __init__(self, parent=None, **kw):
        query = qr.ACMotorInspections()
        df = query.get_df()
        super().__init__(parent=parent, df=df, query=query, simple_table=False, window_title='AC Motor Inspections', maximized=True, **kw)

        self.load_table(df=df)

class UnitSMRDialog(TableDialog):
    """Show SMR history per unit"""

    def __init__(self, parent=None, unit=None, **kw):
        cols = dict(Unit=60, DateSMR=90, SMR=90)

        super().__init__(parent=parent, cols=cols, simple_table=True, window_title='Unit SMR History', **kw)

        df_unit = db.get_df_unit()
        minesite = gbl.get_minesite()
        cb_unit = ff.ComboBox()
        items = f.clean_series(df_unit[df_unit.MineSite == minesite].Unit)
        cb_unit.set_items(items)

        d = dt.now()
        de_lower = ff.DateEdit(date=d + delta(days=-60))
        de_upper = ff.DateEdit(date=d)

        self.add_buttons(cb_unit, de_lower, de_upper, func=self.load_table)

        f.set_self(vars())

        if not unit is None:
            cb_unit.val = unit
            self.load_table()

    def load_table(self):
        """Reload table data when unit or dates change"""
        query = qr.UnitSMR(
            unit=self.cb_unit.val,
            d_rng=(self.de_lower.val, self.de_upper.val))

        df = query.get_df() \
            .sort_values(by='DateSMR', ascending=False)

        super().load_table(df=df)


class UnitOpenFC(TableDialog):
    """Show table widget of unit's open FCs"""
    def __init__(self, unit, parent=None):

        cols = {
            'FC Number': 80,
            'Type': 40,
            'Subject': 300,
            'ReleaseDate': 90,
            'ExpiryDate': 90,
            'Age': 60,
            'Remaining': 70}
            
        super().__init__(parent=parent, cols=cols, name='fc_table')
        self.setWindowTitle('Open FCs')

        query = qr.FCOpen()
        df_fc = db.get_df_fc()
        df_unit = db.get_df_unit()
        minesite = gbl.get_minesite()

        btn_controls = QHBoxLayout()
        cb_minesite = ff.ComboBox(items=db.get_list_minesite(), default=minesite)
        cb_unit = ff.ComboBox()

        self.add_buttons(cb_minesite, cb_unit)

        f.set_self(vars())
        self.load_table(unit=unit)
        
        self.set_units_list()
        cb_unit.val = unit

        cb_minesite.currentIndexChanged.connect(self.set_units_list)
        cb_unit.currentIndexChanged.connect(self._load_table)
    
    def set_units_list(self):
        """Change units list when minesite changes"""
        cb_unit, cb_minesite, df = self.cb_unit, self.cb_minesite, self.df_unit
        items = f.clean_series(df[df.MineSite == cb_minesite.val].Unit)
        cb_unit.set_items(items)
    
    def _load_table(self):
        """Load table from cb_unit value"""
        self.load_table(unit=self.cb_unit.val)

    def load_table(self, unit):
        """Reload table data when unit changes"""
        tbl, df, query, layout = self.tbl, self.df_fc, self.query, self.vLayout

        df = df.pipe(query.df_open_fc_unit, unit=unit)
        super().load_table(df=df)

class DetailsView(QDialog):
    def __init__(self, parent=None, df=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setWindowTitle('Details View')
        self.setMinimumSize(QSize(800, 1000))
        tbl = self.create_table(df=df)
        vLayout = QVBoxLayout(self)
        vLayout.addWidget(tbl)

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
    def __init__(self, parent=None, p_start=None, text=None, unit=None):
        super().__init__(parent=parent)
        self.setWindowTitle('Create TSI Report')
        self.setMinimumSize(QSize(800, 800))
        self.setSizeGripEnabled(True)
        vLayout = QVBoxLayout(self)
        self.parent = parent
        
        text_fields = {}
        if text is None: text = {} # default text for text fields
        if p_start is None:
            p_start = Path.home() / 'Desktop'
        elif not p_start.exists():
            self.update_statusbar(f'Couldn\'t find event images path: {p_start}', warn=True)
        
        dlg = QFileDialogPreview(directory=str(p_start), standalone=False)
        vLayout.addWidget(dlg)
        add_linesep(vLayout)

        # word/pdf radio buttons
        bg1 = QButtonGroup(self)
        btn_pdf = QRadioButton('PDF', self)
        btn_pdf.setChecked(True)
        btn_word = QRadioButton('Word', self)
        bg1.addButton(btn_pdf)
        bg1.addButton(btn_word)

        f.set_self(vars())
        names = ['complaint', 'cause', 'correction', 'details']
        self.add_textbox(names=names)
        add_linesep(vLayout)

        # oil samples

        oil_form = QFormLayout()
        oil_form.setLabelAlignment(Qt.AlignLeft)
        oil_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        # oil_form.setMax

        oil_layout_comp = QHBoxLayout()
        oil_box = ff.ComboBox()
        oil_box.setFixedSize(QSize(300, oil_box.sizeHint().height()))
        oil_cb = ff.CheckBox(checked=False)
        oil_cb.stateChanged.connect(self.toggle_oil_components)
        oil_box.setEnabled(False)
        oil_layout_comp.addWidget(oil_cb)
        oil_layout_comp.addWidget(oil_box)
        # oil_layout_comp.addStretch(1)
        oil_form.addRow(QLabel('Component:'), oil_layout_comp)

        # oil date
        oil_layout_date = QHBoxLayout()
        d = dt.now() + delta(days=-365)
        oil_date = ff.DateEdit(date=d, enabled=False)
        oil_date_cb = ff.CheckBox(checked=False, enabled=False)
        oil_date_cb.stateChanged.connect(self.toggle_oil_date)
        oil_layout_date.addWidget(oil_date_cb)
        oil_layout_date.addWidget(oil_date)
        # oil_layout_date.addStretch(1)
        oil_form.addRow(QLabel('Date Lower:'), oil_layout_date)

        oil_h_layout = QHBoxLayout()
        oil_h_layout.addLayout(oil_form)
        oil_h_layout.addStretch(1)
        
        vLayout.addWidget(QLabel('Oil Samples'))
        vLayout.addLayout(oil_h_layout)
        # vLayout.addLayout(oil_layout)
        # vLayout.addLayout(oil_layout_date)
        add_linesep(vLayout)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(QLabel('Report type:'))
        btn_layout.addWidget(btn_pdf)
        btn_layout.addWidget(btn_word)
        btn_layout.addStretch(1)
        vLayout.addLayout(btn_layout)

        add_okay_cancel(dlg=self, layout=vLayout)
        f.set_self(vars())

        # TODO Faults, PLM?
    
    def toggle_oil_components(self, state):
        """Toggle components when oil cb checked"""
        oil_box = self.oil_box

        if state == Qt.Checked:
            oil_box.setEnabled(True)
            self.oil_date_cb.setEnabled(True)
            # self.oil_date.setEnabled(True)

            df_comp = db.get_df_oil_components(unit=self.unit)
            items = f.clean_series(df_comp.combined)
            oil_box.set_items(items)
            oil_box.select_all()
        else:
            oil_box.setEnabled(False)
            self.oil_date_cb.setEnabled(False)
            self.oil_date_cb.setChecked(False)
            # self.oil_date.setEnabled(False)

    def toggle_oil_date(self, state):
        """Toggle components when oil cb checked"""
        oil_date = self.oil_date

        if state == Qt.Checked:
            oil_date.setEnabled(True)
        else:
            oil_date.setEnabled(False)
    
    def update_statusbar(self, msg, *args, **kw):
        if not self.parent is None:
            self.parent.mainwindow.update_statusbar(msg=msg, *args, **kw)
    
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
        pics = self.dlg.selectedFiles()
        word_report = self.btn_word.isChecked()

        # convert dict of textbox objects to their plaintext (could also use html)
        for name, textbox in self.text_fields.items():
            self.text[name] = textbox.toPlainText()

        # save oil sample component/modifier
        oil_samples = False
        if self.oil_cb.isChecked():
            oil_samples = True
            val = self.oil_box.val
            lst = val.split(' - ')
            component = lst[0]

            # may or may not have modifier
            if len(lst) > 1:
                modifier = lst[1]
            else:
                modifier = None

            if self.oil_date_cb.isChecked():
                d_lower = self.oil_date.val
            else:
                d_lower = None

        f.set_self(vars())
        super().accept()

class QFileDialogPreview(QFileDialog):
    """
    Create QFileDialog with image preview
    """
    def __init__(self, parent=None, caption='', directory=None, filter=None, standalone=True, options=QFileDialog.DontUseNativeDialog, **kw):
        super().__init__(parent, caption, directory, filter, options=options, **kw)
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
            btn_box.hide()
            # self.layout().removeWidget(btn_box) # this stopped working for some reason
 
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

class Search(BaseDialog):
    index_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent, window_title='Search')
        # self.setFocusPolicy(Qt.StrongFocus)

        self.index_changed.connect(self.select)
        items = [] # list of match items
        # parent should be view?
        view = parent
        model = view.model()
        model.highlight_rows = False # turn off row highlighting so we can see single selection
        
        label_matches = QLabel('Matches:')
        search_box = QLineEdit()
        self.meta_state = False
        search_box.textChanged.connect(self.text_changed)
        search_box.installEventFilter(self)
        self.vLayout.addWidget(search_box)
        self.vLayout.addWidget(label_matches)

        # cancel, prev, next
        prev = QPushButton('Prev')
        next_ = QPushButton('Next')
        prev.clicked.connect(self.find_prev)
        next_.clicked.connect(self.find_next)
        prev.setToolTip('Ctrl + Left Arrow')
        next_.setToolTip('Ctrl + Right Arrow | Enter')

        btnbox = QDialogButtonBox(QDialogButtonBox.Cancel)
        btnbox.addButton(prev, QDialogButtonBox.ActionRole)
        btnbox.addButton(next_, QDialogButtonBox.ActionRole)
        
        btnbox.rejected.connect(self.reject)
        self.rejected.connect(self.close) # need to trigger close event to reset selection

        self.vLayout.addWidget(btnbox, alignment=Qt.AlignBottom | Qt.AlignCenter)

        f.set_self(vars())
    
    def closeEvent(self, event):
        self.model.highlight_rows = True
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            mod = event.modifiers()
            key = event.key()

            # print(keyevent_to_string(event))
            if mod and (
                (f.is_win() and mod == Qt.ControlModifier) or
                mod == Qt.AltModifier or
                mod == Qt.MetaModifier or
                mod == (Qt.MetaModifier | Qt.KeypadModifier) or
                mod == (Qt.AltModifier | Qt.KeypadModifier)):
            
                if key == Qt.Key_Right:
                    self.find_next()
                    return True
                elif key == Qt.Key_Left:
                    self.find_prev()
                    return True

            elif key == Qt.Key_Enter or key == Qt.Key_Return:
                self.find_next()
                return True

        return super().eventFilter(obj, event)

    def select(self, i: int):
        """Call view to select, pass tuple of name index"""
        self.current_index = i
        if self.items:
            self.view.select_by_nameindex(self.items[i])
        else:
            i = -1 # no matches, select 0/0
            
        self.label_matches.setText(f'Selected: {i + 1}/{self.num_items}')

    def text_changed(self):
        search_box = self.search_box
        text = search_box.text()
        
        # get list of match items from model
        self.items = self.model.search(text)
        self.num_items = len(self.items)

        self.index_changed.emit(0)

    def find_next(self):
        i = self.current_index
        i += 1
        if i > self.num_items - 1:
            i = 0
        
        self.index_changed.emit(i)
    
    def find_prev(self):
        i = self.current_index
        i -= 1
        if i < 0:
            i = self.num_items - 1

        self.index_changed.emit(i)

class PLMReport(InputForm):
    def __init__(self, unit : str = None, d_upper : dt = None, d_lower : dt = None, **kw):
        super().__init__(window_title='PLM Report', **kw)
        # unit, start date, end date
        IPF = InputField

        if d_upper is None:
            d_upper = dt.now().date()
        
        if d_lower is None:
            d_lower = d_upper + relativedelta(years=-1)
    
        # Unit
        df = db.get_df_unit()
        lst = f.clean_series(df[df.MineSite==self.minesite].Unit)
        self.add_input(field=IPF(text='Unit', default=unit), items=lst)
        
        # Dates
        dates = {'Date Upper': d_upper, 'Date Lower': d_lower}
        for k, v in dates.items():
            self.add_input(
                field=IPF(
                    text=k,
                    default=v,
                    dtype='date'))

class BaseReportDialog(InputForm):
    """Report MineSite/Month period selector dialog for monthly reports"""
    def __init__(self, **kw):
        super().__init__(**kw)

        self.add_input(field=InputField(text='MineSite', default=self.minesite), items=f.config['MineSite'])

        df = qr.df_rolling_n_months(n=12)
        months = df.period.to_list()[::-1]
        self.add_input(field=InputField(text='Month', default=months[0]), items=months)

        f.set_self(vars())

    def accept(self):
        """Set day based on selected month"""
        period = self.fMonth.val
        self.d = self.df.loc[period, 'd_lower']

        super().accept()


def msgbox(msg='', yesno=False, statusmsg=None):
    """Show messagebox, with optional yes/no prompt\n
    If app isn't running, prompt through python instead of dialog

    Parameters
    ----------
    msg : str, optional\n
    yesno : bool, optional\n
    statusmsg : [type], optional\n
        Show more detailed smaller message
    """

    if gbl.app_running() and yesno:
        app = check_app()
        dlg = MsgBox_Advanced(msg=msg, window_title=gbl.title, yesno=yesno, statusmsg=statusmsg)
        return dlg.exec_()
    elif yesno:
        # if yesno and NOT frozen, prompt user through terminal
        return f._input(msg)
    else:
        print(msg)

def msg_simple(msg: str = '', icon: str = '', infotext=None):
    """Show message to user with dialog if app running, else print

    Parameters
    ----------
    msg : str, optional\n
    icon : str, optional
        Show icon eg 'warning', 'critical', default None\n
    infotext : [type], optional\n
        Detailed text to show, by default None
    """
    if gbl.app_running():
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
    else:
        print(msg)

def show_err_msg(text, detailed_text=None):
    if gbl.app_running():
        dlg = ErrMsg(text=text, detailed_text=detailed_text) 
        dlg.exec_()

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
    mw = gbl.get_mainwindow()
    u = mw.u
    m = {'Version': VERSION, 'User Name': u.username, 'Email': u.email, 'User Group': u.usergroup}
    msg = f'SMS Event Log\n\n{f.pretty_dict(m)}'
    return msg_simple(msg=msg)

def set_multiselect(dlg):
    # allow selecting multiple directories for QFileDialog. # NOTE not currently used
    from PyQt5.QtWidgets import (QAbstractItemView, QFileSystemModel,
                                 QListView, QTreeView)

    # set multiselect
    for view in dlg.findChildren((QListView, QTreeView)):
        if isinstance(view.model(), QFileSystemModel):
            view.setSelectionMode(QAbstractItemView.MultiSelection)

def check_dialog_path(p : Path):
    if not fl.check(p, warn=False):
        gbl.update_statusbar(f'Path: {p} does not exist. Check VPN connection.', warn=True)
        p = Path.home() / 'Desktop'
    
    return str(p)

def get_filepath_from_dialog(p_start):
    app = check_app()

    s = QFileDialog.getExistingDirectory(
        directory=check_dialog_path(p_start),
        options=QFileDialog.ShowDirsOnly | QFileDialog.DontUseNativeDialog)

    if s:
        return Path(s)
    return None

def get_filepaths(p_start : Path):
    """Select multiple files from directory"""
    app = check_app()

    lst = QFileDialog.getOpenFileNames(
        directory=check_dialog_path(p_start),
        options=QFileDialog.DontUseNativeDialog)

    if lst:
        return lst[0] # lst is list of files selected + filetypes > ignore filetypes part
    return None

def save_file(p_start=None, name=None, ext='xlsx'):
    # TODO save last folder location to QSettings?
    if p_start is None: 
        p_start = Path.home() / 'Desktop'
    
    p = p_start / f'{name}.{ext}'

    app = check_app()
    s = QFileDialog.getSaveFileName(caption='Save File', directory=str(p), filter='*.xlsx, *.csv', options=QFileDialog.DontUseNativeDialog)
    
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
    # print(dlg.styleSheet())
    return dlg, dlg.exec_()

def check_app():
    """Just need to make sure app is set before showing dialogs"""
    from . import startup
    app = startup.get_qt_app()
    return app

def unit_exists(unit):
    """Check if unit exists, outside of DB class, raise error message if False"""
    if not db.unit_exists(unit=unit):
        msg = f'Unit "{unit}" does not exist in database. Please add it to db from the [Unit Info] tab.'
        msg_simple(msg=msg, icon='warning')
        return False
    else:
        return True


# Used to check keymap vals passed through event filter
# global keymap, modmap
# keymap = {}
# for key, value in vars(Qt).items():
#     if isinstance(value, Qt.Key):
#         keymap[value] = key.partition('_')[2]

# modmap = {
#     Qt.ControlModifier: keymap[Qt.Key_Control],
#     Qt.AltModifier: keymap[Qt.Key_Alt],
#     Qt.ShiftModifier: keymap[Qt.Key_Shift],
#     Qt.MetaModifier: keymap[Qt.Key_Meta],
#     Qt.GroupSwitchModifier: keymap[Qt.Key_AltGr],
#     Qt.KeypadModifier: keymap[Qt.Key_NumLock]}

# def keyevent_to_string(event):
#     sequence = []
#     for modifier, text in modmap.items():
#         if event.modifiers() & modifier:
#             sequence.append(text)

#     key = keymap.get(event.key(), event.text())

#     if key not in sequence:
#         sequence.append(key)

#     return '+'.join(sequence)
