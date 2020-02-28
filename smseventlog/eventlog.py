import sys
from collections import defaultdict
from datetime import datetime as date
from datetime import timedelta as delta
from pathlib import Path
from urllib import parse

import pandas as pd
import pypika as pk
import xlwings as xw
import yaml

import folders as fl
import functions as f
from userforms import *
from database import db

if sys.platform.startswith('win'):
    import win32api

def mac():
    pass
    # list object
        # list_rows[1].range_object.get_address()
        # show_autofilter() > returns true or false
        # .cell_table.value() > returns list of lists
        # .header_row.value()
        # .show_autofilter() > returns if filters are visible
    # range_object
        # value()
        # formula_r1c1() > returns all values in range as list of lists
        # get_address()
def example():
    wb = xw.books('SMS Event Log.xlsm')
    ws = wb.sheets('Event Log')
    lsto = Table(ws=ws)

def test(msg='no message'):    
    msgbox(msg, title=xw.books.active.name.split('.')[0])

def msgbox_excel(msg='', title='Excel Messagebox'):
    app = xw.apps[xw.apps.keys()[0]]
    win32api.MessageBox(app.hwnd, msg, title)

def book():
    title = 'SMS Event Log.xlsm'
    # title = 'testproject.xlsm'
    return xw.books(title)

def refresh_table(title=None):
    # global db
    startdate = date(2020, 1, 10)
    minesite = 'FortHills'

    if title is None:
        ws = xw.books.active.sheets.active
        title = ws.name
    else:
        ws = book().sheets(title)

    tbl = Table(ws=ws)
    cols = tbl.headers_db()

    if title == 'Event Log':
        a = pk.Table('EventLog')
        q = pk.Query.from_(a).select(*cols) \
            .where(a.MineSite == minesite) \
            .where(a.DateAdded >= startdate)
    elif title == 'Python':
        a = pk.Table('UnitID')
        q = pk.Query.from_(a).select(*cols) \
            .where(a.MineSite == minesite)
    
    # if db is None:
    #     db = DB()
    tbl.df = pd.read_sql(sql=q.get_sql(), con=db.conn)
    # db.close()

    # return tbl.df
    tbl.to_excel()

def colstest(*cols, first=1):
    for col in cols:
        print(str(first) + col)

class Table():
    def __init__(self, ws=None, lsto=None, df=None):
        self.win = sys.platform.startswith('win')
        if not df is None: self.df = df

        if not ws is None and lsto is None:
            if isinstance(ws, str):
                ws = book().sheets(ws)

            if self.win:
                self.lsto = ws.api.ListObjects(1)
                address = self.lsto.range.address
            else:
                self.lsto = ws.api.list_objects[1]
                address = self.lsto.range_object.get_address()

            self.ws = ws
            self.wb = ws.book
        else:
            self.lsto = lsto
            wsxl = lsto.range.worksheet
            self.wb = xw.books(wsxl.parent.name)
            self.ws = self.wb.sheets(wsxl.name)

        self.app = self.wb.app
        self.rng = self.ws.range(address)
        self.header = self.rng[:1,:]
        self.body = self.rng[1:,:]

    def get_df(self):
        return self.rng.options(pd.DataFrame, header=True, index=False).value

    def rows(self, row):
        return self.body[row, :].value

    def columns(self, col):
        return self.body[:, col].value

    def headers_db(self):
        m = defaultdict(dict, f.config['Headers'])[self.ws.name]
        cols = self.headers()

        return [m[col] if col in m.keys() else col for col in cols]

    def headers(self):
        return self.header.value

    def fixE(self, cols):
        # clear -E from df columns
        df = self.df
        if not isinstance(cols, list): cols = [cols]
        for col in cols:
            df[col].loc[df[col].str.contains('E-')] = "'" + df[col]
    
    def to_excel(self, df=None):
        if df is None:
            df = self.df
        else:
            self.df = df

        self.fixE(cols=list(filter(lambda x: x.lower() == 'model', df.columns)))
        
        app = self.app
        lsto = self.lsto
        app.screen_updating = False
        enable_events(app=app, val=False)

        self.clearfilter()
        self.cleartable()
        self.body.options(index=False, header=False).value = df

        app.screen_updating = True
        enable_events(app=app, val=True)

    def clearfilter(self):
        lsto = self.lsto
        if self.win and lsto.autofilter.filtermode:
            lsto.autofilter.showalldata()
        elif not self.win and lsto.autofilter_object.autofiltermode():
            self.ws.api.show_all_data()

    def cleartable(self):
        rng = self.body
        if len(rng.rows) > 1:
            rng[1:,:].delete()

        if rng[0].value is None: rng[0].value = ' '

def enable_events(app, val=None):
    if sys.platform.startswith('win'):
        if not val is None:
            app.api.enableevents = val
        else:
            return app.api.enableevents
    else:
        if not val is None:
            app.api.enable_events.set(val)
        else:
            return app.api.enable_events()

# if __name__ == "__main__":
#     xw.books.active.set_mock_caller()
#     main()
