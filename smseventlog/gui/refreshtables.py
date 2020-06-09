from .__init__ import *
from . import gui as ui
from .dialogs import InputForm, InputField
from pypika import Table as T
from .. import reports as rp

log = logging.getLogger(__name__)

# Dialogs to show and allow user to create filters before refreshing table data

class RefreshTable(InputForm):
    def __init__(self, parent=None):

        # initialize with proper table when called on its own for testing
        if parent is None:
            from . import tables
            parent_name = getattr(tables, self.__class__.__name__, None)
            if parent_name:
                parent = parent_name()
            
        super().__init__(parent=parent, title='Refresh Table')      
        self.minesite = ui.get_minesite()
        self.mainwindow = ui.get_mainwindow()

        # create list of default boxes, call with dict
        # m = dict()
        # m['All Open'] = self.add_refresh_button(name='All Open', func=parent.refresh_allopen)
        # m['All Open'] = self.add_refresh_button
        
        # super().show()
    
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
            add_refresh_button(name=title, func=parent.refresh_lastweek)

        elif name == 'last month':
            add_refresh_button(name=title, func=parent.refresh_lastmonth)
                       
        elif name == 'minesite_config':
            title = 'MineSite'
            add_input(field=IPF(text=title, default=ms), items=f.config[title], checkbox=True)

        elif name == 'minesite':
            table = T('UnitID')
            lst = db.get_list_minesite()
            add_input(field=IPF(text='MineSite', default=ms, table=table), items=lst, checkbox=True)
            
        elif name == 'unit':
            df = db.get_df_unit()
            lst = f.clean_series(s=df[df.MineSite==ms].Unit)
            add_input(field=IPF(text=title), items=lst, checkbox=True, cb_enabled=False)
            
        elif name == 'model':
            df = db.get_df_unit()
            lst = f.clean_series(s=df[df.MineSite==ms].Model)
            add_input(field=IPF(text=title), items=lst, checkbox=True, cb_enabled=False)
            
        elif name == 'type':
            table=T('FCSummary')
            add_input(field=IPF(text=title, col_db='Classification', table=table), items=['M', 'FAF', 'DO', 'FT'], checkbox=True, cb_enabled=False)
            
        elif name == 'fc number':
            df = db.get_df_fc()
            lst = f.clean_series(s=df[df.MineSite==ms].FCNumber)
            add_input(field=IPF(text=title), items=lst, checkbox=True, cb_enabled=False)
        
        elif name == 'fc complete':
            add_input(field=IPF(text=title, col_db='Complete'), items=['False', 'True'], checkbox=True, cb_enabled=False)
            
        elif name == 'manualclosed':
            title = 'Manual Closed'
            table = T('FCSummaryMineSite')
            add_input(field=IPF(text=title, default='False', table=table), items=['False', 'True'], checkbox=True)
            
        elif name == 'start date':
            # TODO: only set up for eventlog table currently
            add_input(field=IPF(text=title, dtype='date', col_db='DateAdded'), checkbox=True, cb_enabled=False)
            
        elif name == 'end date':
            add_input(field=IPF(text=title, dtype='date', col_db='DateCompleted', opr=op.le), checkbox=True, cb_enabled=False)

        elif name == 'component':
            df = db.get_df_component()
            lst = f.clean_series(df.Component)
            table = T('ComponentType')
            add_input(field=IPF(text=title, table=table), items=lst, checkbox=True, cb_enabled=False)
        
        elif name == 'tsi author':
            username = self.mainwindow.username
            add_input(field=IPF(text='TSI Author', default=username, col_db='TSIAuthor'), checkbox=True, cb_enabled=False)
        
        elif name == 'major components':
            table = T('ComponentType')
            add_input(field=IPF(text=title, default='True', table=table, col_db='Major'), items=['True', 'False'], checkbox=True, cb_enabled=False)

    def add_refresh_button(self, name, func):
        layout = self.vLayout
        btn = QPushButton(name, self)
        btn.setMaximumWidth(60)
        layout.insertWidget(0, btn)
        btn.clicked.connect(self.add_items_to_filter)
        btn.clicked.connect(super().accept)
        btn.clicked.connect(func)
    
    def accept(self):
        self.add_items_to_filter()
        self.parent.refresh()
        super().accept()
    
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

        features = ['last month', 'last week', 'all open', 'minesite', 'unit', 'model', 'start date', 'end date']
        self.add_features(features=features)

class EventLog(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

class WorkOrders(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

class ComponentCO(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.add_features(features=['component', 'major components'])

class TSI(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.add_features(features=['tsi author'])

class FCSummary(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        features = ['all open', 'minesite', 'fc number', 'type', 'manualclosed', 'model', 'Unit']
        self.add_features(features=features)

class FCDetails(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        features = ['all open', 'minesite', 'fc number', 'type', 'manualclosed', 'fc complete', 'model', 'unit']
        self.add_features(features=features)

class UnitInfo(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        features = ['minesite', 'model']
        self.add_features(features=features)

class EmailList(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        features = ['minesite']
        self.add_features(features=features)

class Availability(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        df_week = df_weeks()
        df_month = df_months()

        d = dt.now().date() + delta(days=-7)
        default_week = df_week[df_week.StartDate < d].iloc[-1, :].name #index name

        d = dt.now() + delta(days=-30)
        default_month = df_month[df_month.StartDate < d].iloc[-1, :].name #index name

        self.add_input(field=InputField(text='Week', default=default_week), items=df_week.index, checkbox=True, cb_enabled=False)
        self.add_input(field=InputField(text='Month', default=default_month), items=df_month.index, checkbox=True, cb_enabled=False)

        f.set_self(self, vars())

    def accept(self):
        fMonth, fWeek = self.fMonth, self.fWeek

        if fMonth.cb.isChecked():
            val = fMonth.get_val()
            df = self.df_month
        elif fWeek.cb.isChecked():
            val = fWeek.get_val()
            df = self.df_week

        d_rng = (df.loc[val, 'StartDate'], df.loc[val, 'EndDate'])
        self.parent.query.fltr.add(vals=dict(ShiftDate=d_rng), term='between')
        self.close()
        self.parent.refresh()

def df_months():
    # Month
    cols = ['StartDate', 'EndDate']
    d_start = dt.now() + delta(days=-365)
    d_start = dt(d_start.year, d_start.month, 1)

    m = {}
    for i in range(24):
        d = d_start + relativedelta(months=i)
        name = '{:%Y-%m}'.format(d)
        m[name] = rp.first_last_month(d)

    return pd.DataFrame.from_dict(m, columns=cols, orient='index')

def df_weeks():
    # Week
    cols = ['StartDate', 'EndDate']

    m = {}
    year = dt.now().year
    for wk in range(1, 53):
        s = f'2020-W{wk-1}'
        d = dt.strptime(s + '-1', "%Y-W%W-%w").date()
        m[f'{year}-{wk}'] = (d, d + delta(days=6))

    return pd.DataFrame.from_dict(m, columns=cols, orient='index')

# TODO: this doesn't need to be duplicated here
def show_item(name, parent=None):
    # show message dialog by name eg ui.show_item('InputUserName')
    app = ui.get_qt_app()
    dlg = getattr(sys.modules[__name__], name)(parent=parent)
    return dlg.exec_()