from .__init__ import *
from . import gui as ui
from .dialogs import InputForm, InputField
import pypika as pk

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
            
        elif name == 'minesite':
            lst = self.clean_series(s=db.get_df_unit().MineSite)
            title = 'MineSite'
            add_input(field=IPF(text=title, default=ms), items=lst, checkbox=True)
            
        elif name == 'minesite_config':
            title = 'MineSite'
            add_input(field=IPF(text=title, default=ms), items=f.config[title], checkbox=True)

        elif name == 'minesite_unit':
            table = pk.Table('UnitID')
            lst = self.clean_series(s=db.get_df_unit().MineSite)
            add_input(field=IPF(text='MineSite', default=ms, table=table), items=lst, checkbox=True)
            
        elif name == 'unit':
            df = db.get_df_unit()
            lst = self.clean_series(s=df[df.MineSite==ms].Unit)
            add_input(field=IPF(text=title), items=lst, checkbox=True, cb_enabled=False)
            
        elif name == 'model':
            df = db.get_df_unit()
            lst = self.clean_series(s=df[df.MineSite==ms].Model)
            add_input(field=IPF(text=title), items=lst, checkbox=True, cb_enabled=False)
            
        elif name == 'type':
            table=pk.Table('FCSummary')
            add_input(field=IPF(text=title, col_db='Classification', table=table), items=['M', 'FAF', 'DO', 'FT'], checkbox=True, cb_enabled=False)
            
        elif name == 'fc number':
            df = db.get_df_fc()
            lst = self.clean_series(s=df[df.MineSite==ms].FCNumber)
            add_input(field=IPF(text=title), items=lst, checkbox=True, cb_enabled=False)
        
        elif name == 'fc complete':
            add_input(field=IPF(text=title, col_db='Complete'), items=['False', 'True'], checkbox=True, cb_enabled=False)
            
        elif name == 'manualclosed':
            title = 'Manual Closed'
            table = pk.Table('FCSummaryMineSite')
            add_input(field=IPF(text=title, default='False', table=table), items=['False', 'True'], checkbox=True)
            
        elif name == 'start date':
            # TODO: only set up for eventlog table currently
            add_input(field=IPF(text=title, dtype='date', col_db='DateAdded'), checkbox=True, cb_enabled=False)
            
        elif name == 'end date':
            add_input(field=IPF(text=title, dtype='date', col_db='DateCompleted'), checkbox=True, cb_enabled=False)

        elif name == 'component':
            df = db.get_df_component()
            lst = self.clean_series(df.Component)
            table = pk.Table('ComponentType')
            add_input(field=IPF(text=title, table=table), items=lst, checkbox=True, cb_enabled=False)

    def clean_series(self, s):
        return sorted(list(s.replace('', pd.NA).dropna().unique()))

    def add_refresh_button(self, name, func):
        layout = self.vLayout
        btn = QPushButton(name, self)
        btn.setMaximumWidth(60)
        btn.clicked.connect(self.accept)
        btn.clicked.connect(func)
        layout.insertWidget(0, btn)
    
    def accept(self):
        self.add_items_to_filter(fltr=self.get_fltr())
        self.parent.refresh()
        super().accept()
    
    def get_fltr(self):
        # get filter from parent table or just create default for testing
        parent = self.parent
        if not parent is None:
            return parent.fltr
        else:
            return el.Filter(title='Event Log') # default

class EventLog(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        features = ['last month', 'last week', 'all open', 'minesite_config', 'unit', 'start date', 'end date']
        self.add_features(features=features)

class WorkOrders(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        features = ['last month', 'last week', 'all open', 'minesite_config', 'unit', 'start date', 'end date']
        self.add_features(features=features)

class TSI(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        features = ['last month', 'last week', 'all open', 'minesite', 'unit', 'start date', 'end date']
        self.add_features(features=features)

class FCSummary(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        features = ['all open', 'minesite_unit', 'type', 'manualclosed', 'model', 'Unit']
        self.add_features(features=features)

class FCDetails(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        features = ['all open', 'minesite_unit', 'fc number', 'type', 'manualclosed', 'fc complete', 'model', 'unit']
        self.add_features(features=features)

class UnitInfo(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        features = ['minesite', 'model']
        self.add_features(features=features)

class ComponentCO(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        features = ['minesite_unit', 'component', 'model', 'unit']
        self.add_features(features=features)


# TODO: this doesn't need to be duplicated here
def show_item(name, parent=None):
    # show message dialog by name eg ui.show_item('InputUserName')
    app = ui.get_qt_app()
    dlg = getattr(sys.modules[__name__], name)()
    return dlg.exec_()