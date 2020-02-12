from datetime import datetime as date
from datetime import timedelta as delta
from pathlib import Path
from urllib import parse
from collections import defaultdict
import sys

import pandas as pd
import pypika as pk

if sys.platform.startswith('win'):
    import win32api
    
import xlwings as xw
import yaml

import Folders as fl

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


def topfolder():
    # TODO: this needs to be dynamic
    return Path(__file__).parent

def example():
    wb = xw.books('SMS Event Log.xlsm')
    ws = wb.sheets('Event Log')
    lsto = el.Table(ws=ws)

def test():
    # wb = xw.Book.caller()
    wb = xw.books('testproject.xlsm')
    # app = wb.app
    # ans = app.api.InputBox('Tell me the truth: ', 'InputBox of Truth')
    # msgbox(f'The truth is: {ans}')
    # q = pk.Table('UnitID').select('Unit', 'Serial')
    wb.sheets('Python').range('K1').value = 'tttttt'
    # msgbox(q.get_sql())
    
def msgbox(msg='', title='Excel'):
    app = xw.apps[xw.apps.keys()[0]]
    win32api.MessageBox(app.hwnd, msg, title)

def book():
    title = 'SMS Event Log.xlsm'
    title = 'testproject.xlsm'
    return xw.books(title)

def refresh_table(title=None):
    
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
            # .where(a.MineSite == minesite)
    
    with fl.DB() as db:
        df = pd.read_sql(sql=q.get_sql(), con=db.conn)

    tbl.to_excel(df=df)

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
        self.rngheader = self.rng[:1,:]
        self.rngbody = self.rng[1:,:]

    def get_df(self):
        return self.rng.options(pd.DataFrame, header=True, index=False).value

    def headers_db(self):
        p = Path(topfolder()) / 'config.yaml'
        with open(p) as file:
            m = defaultdict(dict, yaml.full_load(file)['Headers'])[self.ws.name]

        cols = self.headers()

        return [m[col] if col in m.keys() else col for col in cols]

    def headers(self):
        return self.rngheader.value
    
    def to_excel(self, df):
        app = self.app
        lsto = self.lsto
        app.screen_updating = False
        enable_events(app=app, val=False)

        self.clearfilter()
        self.cleartable()
        self.rngbody.options(index=False, header=False).value = df

        app.screen_updating = True
        enable_events(app=app, val=True)

    def clearfilter(self):
        lsto = self.lsto
        if self.win and lsto.autofilter.filtermode:
            lsto.autofilter.showalldata()
        elif lsto.autofilter_object.autofiltermode():
            self.ws.api.show_all_data()

    def cleartable(self):
        rng = self.rngbody
        if len(rng.rows) > 1:
            rng[1:,:].delete()

        if rng[0].value is None: rng[0].value = ' '

        # ws = self.ws
        # lsto = self.lsto
        # dbr = lsto.databodyrange
        # rng = ws.range(lsto.listcolumns(1).databodyrange.address)
        # if len(rng) > 1:
        #     rng[1:].clear_contents()
        #     dbr.removeduplicates(1)
        #     lsto.listrows(2).range.delete

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
