from .__init__ import *
from . import _global as gbl
from .dialogs import InputForm, InputField, check_app

log = getlog(__name__)

# Dialogs to show and allow user to create filters before refreshing table data

# save settings on accept. ClassName > form name? > value
# https://stackoverflow.com/questions/23279125/python-pyqt4-functions-to-save-and-restore-ui-widget-values

class RefreshTable(InputForm):
    def __init__(self, parent=None):

        # initialize with proper table when called on its own for testing
        if parent is None:
            from . import tables
            parent_name = getattr(tables, self.__class__.__name__, None)
            if parent_name:
                parent = parent_name()
            
        super().__init__(parent=parent, window_title='Refresh Table')      
        self.minesite = gbl.get_minesite()
    
    def add_features(self, features):
        for feature in features:
            self.add_feature(name=feature)
    
    def add_feature(self, name):
        parent, ms = self.parent, self.minesite
        name, title = name.lower(), name.title()
        IPF = InputField
        add_input, add_refresh_button = self.add_input, self.add_refresh_button

        # this is ugly, would rather set up objects and only call when needed, but hard to initialize
        if name == 'all open':
            add_refresh_button(name=title, func=parent.refresh_allopen)

        elif name == 'last week':
            add_refresh_button(name=title, func=lambda: parent.refresh_lastweek(base=False))

        elif name == 'last month':
            add_refresh_button(name=title, func=lambda: parent.refresh_lastmonth(base=False))
                       
        elif name == 'minesite_config':
            title = 'MineSite'
            add_input(field=IPF(text=title, default=ms), items=f.config[title], checkbox=True)

        # TODO remove eventually, temp for EmailList table
        elif name == 'minesite_like':
            title = 'MineSite'
            add_input(field=IPF(text=title, default=ms, like=True), items=f.config[title], checkbox=True)

        elif name == 'minesite':
            table = T('UnitID')
            lst = db.get_list_minesite()
            add_input(field=IPF(text='MineSite', default=ms, table=table), items=lst, checkbox=True)

        elif name == 'work order':
            add_input(field=IPF(text=title), checkbox=True, cb_enabled=False)
            
        elif name == 'unit':
            df = db.get_df_unit()
            lst = f.clean_series(s=df[df.MineSite==ms].Unit)
            add_input(field=IPF(text=title), items=lst, checkbox=True, cb_enabled=False)
            
        elif name == 'model':
            table = T('UnitID')
            df = db.get_df_unit()
            lst = f.clean_series(s=df[df.MineSite==ms].Model)
            add_input(field=IPF(text=title, table=table), items=lst, checkbox=True, cb_enabled=False)
            
        elif name == 'type':
            table=T('FCSummary')
            add_input(field=IPF(text=title, col_db='Classification', table=table), items=['M', 'FAF', 'DO', 'FT'], checkbox=True, cb_enabled=False)
            
        elif name == 'fc number':
            df = db.get_df_fc()
            lst = f.clean_series(s=df[df.MineSite==ms]['FC Number'])
            add_input(field=IPF(text='FC Number'), items=lst, checkbox=True, cb_enabled=False)
        
        elif name == 'fc complete':
            add_input(field=IPF(text=title, col_db='Complete'), items=['False', 'True'], checkbox=True, cb_enabled=False)
            
        elif name == 'manualclosed':
            title = 'Manual Closed'
            table = T('FCSummaryMineSite')
            add_input(field=IPF(text=title, default='False', table=table), items=['False', 'True'], checkbox=True)
            
        elif name == 'start date':
            # TODO: only set up for eventlog table currently
            add_input(field=IPF(text=title, dtype='date', col_db=self.col_db_startdate), checkbox=True, cb_enabled=False)
            
        elif name == 'end date':
            add_input(field=IPF(text=title, dtype='date', col_db=self.col_db_enddate, opr=op.le), checkbox=True, cb_enabled=False)

        elif name == 'component':
            df = db.get_df_component()
            lst = f.clean_series(df.Component)
            table = T('ComponentType')
            add_input(field=IPF(text=title, table=table), items=lst, checkbox=True, cb_enabled=False)
        
        elif name == 'tsi author':
            username = self.mainwindow.username
            add_input(field=IPF(text='TSI Author', default=username, col_db='TSIAuthor'), checkbox=True, cb_enabled=False)

        elif name == 'tsi number':
            add_input(field=IPF(text='TSI Number'), checkbox=True, cb_enabled=False)
        
        elif name == 'major components':
            if self.__class__.__name__ == 'ComponentSMR':
                table = None # default to viewPredictedCO
                cb_enabled = True
            else:
                table = T('ComponentType')
                cb_enabled = False

            add_input(field=IPF(text=title, default='True', table=table, col_db='Major'), items=['True', 'False'], checkbox=True, cb_enabled=cb_enabled)
        
        elif name == 'title':
            add_input(field=IPF(text='Title', col_db=title), checkbox=True, cb_enabled=False,
                tooltip='Use wildcards * to match results containing partial text.\nEg:\n\
                - Steering* > return "Steering Pump" and "Steering Arm", but not "Change Steering Pump"\n\
                - *MTA* > return "The MTA Broke" and "MTA Failure"')
        
        elif name == 'fc subject':
            df = db.get_df_fc()
            lst = f.clean_series(df.Subject)
            add_input(field=IPF(text='Subject', table=T('FCSummary')), items=lst, checkbox=True, cb_enabled=False)
        
        elif name == 'usergroup':
            u = self.mainwindow.u

            if self.parent.title in ('Event Log', 'Work Orders'):
                enabled = False if not u.is_cummins else True
                table = T('UserSettings')
            else:
                enabled = True
                table = None

            field = IPF(
                    text='User Group',
                    default=db.domain_map_inv.get(u.domain, 'SMS'),
                    col_db='UserGroup',
                    table=table)

            add_input(
                field=field,
                items=db.domain_map.keys(),
                checkbox=True,
                cb_enabled=enabled,
                tooltip='Limit results to only those created by users in your domain.\n(Ensure users have been correctly initialized.)')

    def add_refresh_button(self, name, func):
        layout = self.vLayout
        btn = QPushButton(name, self)
        btn.setMaximumWidth(60)
        layout.insertWidget(0, btn)
        btn.clicked.connect(self._add_items_to_filter)
        btn.clicked.connect(super().accept)
        btn.clicked.connect(func)
    
    def accept(self):
        self._add_items_to_filter()
        self.parent.refresh()
        return super().accept()
    
    def get_fltr(self):
        # get filter from parent table or just create default for testing
        parent = self.parent
        if not parent is None:
            return parent.query.fltr
        else:
            return qr.EventLog().fltr # default

class EventLogBase(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.col_db_startdate, self.col_db_enddate = 'DateAdded', 'DateCompleted'

        features = ['last month', 'last week', 'all open', 'minesite', 'unit', 'model', 'title', 'work order', 'start date', 'end date']
        self.add_features(features=features)
        self.insert_linesep(i=3, layout_type='vbox')

class EventLog(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.add_feature(name='usergroup')

class WorkOrders(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.add_feature(name='usergroup')

class ComponentCO(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.add_features(features=['component', 'major components'])

class ComponentSMR(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # Component/major comp need different table
        self.add_features(features=['minesite', 'unit', 'model', 'component', 'major components'])

class TSI(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.add_features(features=['tsi author', 'tsi number'])

class FCBase(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.df = db.get_df_fc()
    
    def toggle(self, state):
        # filter FC subjects to current minesite
        # IF minesite is enabled AND subject is enabled
        # if minesite not enabled, filter to all
        source = self.sender()
        box = source.box
        cb_minesite = self.fMineSite.cb
        minesite = self.fMineSite.val
        df = self.df

        if box is self.fSubject.box:
            if state == Qt.Checked:
                if cb_minesite.isChecked():
                    # filter to FCs for active minesite
                    items = f.clean_series(s=df[df.MineSite==minesite].Subject)
                    box.set_items(items=items)
                    self.update_statusbar(f'Filtering FC Subjects for MineSite: {minesite}')
                else:
                    # minseite not enabled, set to everything
                    box.reset()
                    self.update_statusbar('Resetting FC Subjects for all MineSites.')

        super().toggle(state)

class FCSummary(FCBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        features = ['all open', 'minesite', 'fc number', 'fc subject', 'type', 'manualclosed', 'model', 'Unit']
        self.add_features(features=features)

class FCDetails(FCBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        features = ['all open', 'minesite', 'fc number', 'fc subject', 'type', 'manualclosed', 'fc complete', 'model', 'unit']
        self.add_features(features=features)

class UnitInfo(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        features = ['minesite', 'model']
        self.add_features(features=features)

class EmailList(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        features = ['minesite_like', 'usergroup']
        self.add_features(features=features)

class Availability(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        col_db_startdate, col_db_enddate = 'StartDate', 'EndDate'
        
        df_week = qr.df_weeks()
        df_month = qr.df_months()

        d = dt.now().date() + delta(days=-6)
        default_week = df_week[df_week.StartDate < d].iloc[-1, :].name #index name

        d = dt.now() + delta(days=-30)
        default_month = df_month[df_month.StartDate < d].iloc[-1, :].name #index name

        f.set_self(vars())

        self.add_input(field=InputField(text='Week', default=default_week), items=df_week.index, checkbox=True, cb_enabled=False)
        self.add_input(field=InputField(text='Month', default=default_month), items=df_month.index, checkbox=True, cb_enabled=False)

        self.add_features(['start date', 'end date', 'unit'])
        self.insert_linesep(i=2)

    def set_rng(self):
        fMonth, fWeek = self.fMonth, self.fWeek

        if fMonth.cb.isChecked():
            name = fMonth.val
            period_type = 'month'
        elif fWeek.cb.isChecked():
            name = fWeek.val
            period_type = 'week'
        
        df = qr.df_period(freq=period_type)
        d_rng = df.loc[name, 'd_rng']
        f.set_self(vars())

    def accept(self):
        if any([self.fWeek.cb.isChecked(), self.fMonth.cb.isChecked()]):

            self.set_rng()
            self.parent.query.fltr.add(vals=dict(ShiftDate=self.d_rng), term='between')
            self.parent.refresh()
            return super().accept_()
        else:
            return super().accept()

class AvailReport(Availability):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def accept(self):
        self.set_rng()
        return super().accept_()


# NOTE this doesn't need to be duplicated here
def show_item(name, parent=None):
    # show message dialog by name eg gbl.show_item('InputUserName')
    app = check_app()
    dlg = getattr(sys.modules[__name__], name)(parent=parent)
    return dlg, dlg.exec_()