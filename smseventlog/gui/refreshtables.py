from .__init__ import *
from . import gui as ui
from .dialogs import InputForm, InputField
import pypika as pk
# from . import dialogs as dlgs
# from ..__init__ import *

import logging
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
        parent = self.parent
        ms = self.minesite
        name = name.lower()
        title = name.title()
        ipt = InputField
        add_input, add_refresh_button = self.add_input, self.add_refresh_button

        # this is ugly, would rather set up objects and only call when needed, but hard to initialize
        if name == 'all open':
            add_refresh_button(name=title, func=parent.refresh_allopen)
        elif name == 'last week':
            add_refresh_button(name=title, func=parent.refresh_lastweek)
        elif name == 'last month':
            add_refresh_button(name=title, func=parent.refresh_lastmonth)
        elif name == 'minesite':
            title = 'MineSite'
            add_input(field=ipt(text=title, default=ms), items=f.config[title])
        elif name == 'unit':
            df = db.get_df_unit()
            lst = self.clean_series(s=df[df.MineSite==ms].Unit)
            add_input(field=ipt(text=title), items=lst, checkbox=True, cb_enabled=False)
        elif name == 'model':
            df = db.get_df_unit()
            lst = self.clean_series(s=df[df.MineSite==ms].Model)
            add_input(field=ipt(text=title), items=lst, checkbox=True, cb_enabled=False)
        elif name == 'type':
            table=pk.Table('FCSummary')
            add_input(field=ipt(text=title, col_db='Classification', table=table), items=['M', 'FAF', 'DO', 'FT'], checkbox=True, cb_enabled=False)
        elif name == 'manualclosed':
            title = 'Manual Closed'
            table = pk.Table('FCSummaryMineSite')
            add_input(field=ipt(text=title, default='False', table=table), items=['False', 'True'], checkbox=True)

    def clean_series(self, s):
        return list(s.replace('', pd.NA).dropna().unique())

    def add_refresh_button(self, name, func):
        layout = self.vLayout
        btn = QPushButton(name, self)
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

        features = ['last month', 'last week', 'all open', 'minesite', 'unit']
        self.add_features(features=features)
        
        self.add_input(field=InputField(text='Date', dtype='date', col_db='DateAdded'), checkbox=True, cb_enabled=False)

class FCSummary(RefreshTable):
    def __init__(self, parent=None):
        # print(self.__class__.__name__)
        # if parent is None:
        #     parent = tbls.FCSummary()
        super().__init__(parent=parent)
        ms = self.minesite
        table=pk.Table('UnitID')
        # TODO: distinct minesites from unitID table, not config
        self.add_input(field=InputField(text='MineSite', default=ms, table=table), items=f.config['MineSite'])

        features = ['all open', 'type', 'manualclosed', 'model']
        self.add_features(features=features)


class UnitInfo(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        ms = self.minesite

class ComponentCO(RefreshTable):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        ms = self.minesite


# TODO: this doesn't need to be duplicated here
def show_item(name, parent=None):
    # show message dialog by name eg ui.show_item('InputUserName')
    app = ui.get_qt_app()
    dlg = getattr(sys.modules[__name__], name)()
    return dlg.exec_()