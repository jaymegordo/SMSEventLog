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
from pkg_resources import parse_version
from timeit import default_timer as timer

import folders as fl
import functions as f
import userforms as uf
from database import db

global title, titlename
titlename = 'SMS Event Log'
title = titlename + '.xlsm'
# title = 'testproject.xlsm'


# UPDATE
def push_update_ui(vertype='patch'):
    wb = book()
    # get old version
    rng = book().sheets('version').range('version')
    v_current = parse_version(rng.value)

    # update version range
    v_new = f.bump_version(ver=v_current, vertype=vertype)
    rng.value = v_new

    # update .txt
    p = v_txt()
    p.rename(p.parent / f'{v_new}.txt')

    msg = f'{title} UI updated.\n\nOld: {v_current.base_version}\nNew: {v_new}'
    # uf.msg_simple(msg=msg)
    print(msg)

def v_txt():
    p = Path(__file__).parent / 'data/excel/'
    return sorted(p.glob('*.txt'))[0]

def v_check():
    return parse_version(v_txt().name.strip('.txt'))

def v_current():
    return parse_version(book().sheets('version').range('version').value)

def check_ver_ui():
    ans = True if v_check() > v_current() else False
    print(ans)
    return ans

def check_update_ui():
    # TODO: make sure this works when run from excel
    # copy new excel file from site-packages and replace currently active book
    if check_ver_ui():

        msg = f'A new version of the EventLog UI is available.\n\nCurrent: {v_current()}\nNew: {v_check()}\n\nWould you like to update?'
        if uf.msgbox(msg=msg, yesno=True):

            # rename current wb
            start = timer()
            wb_old = book()
            app = wb_old.app
            app.screen_updating = False
            p_old = Path(book().fullname).parent / f'{titlename}-OLD.xlsm'
            wb_old.save(path=str(p_old))

            # open new wb
            p = f.topfolder / f'data/excel/{title}'
            wb = xw.books.open(p)

            # delete old wb
            wb_old.close()
            p_old.unlink()
            app.screen_updating = True
            msg = f'wb updated in {f.deltasec(start, timer())}s'
            uf.msgbox(msg=msg)


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

def book():
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
    tbl.df = pd.read_sql(sql=q.get_sql(), con=db.engine)
    # db.close()

    # return tbl.df
    tbl.to_excel()

# TABLE - class to bridge excel listobjects, dataframes, and xlwings ranges
class Table():
    def __init__(self, ws=None, lsto=None, df=None):
        self.win = sys.platform.startswith('win')
        if not df is None: self.df = df

        if not ws is None and lsto is None:
            if isinstance(ws, str):
                ws = book().sheets(ws)

            if self.win:
                self.lsto = ws.api.ListObjects(1)  # win
                address = self.lsto.range.address
            else:
                self.lsto = ws.api.list_objects[1] # mac
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
        # translate between excel table header 'nice' names and names in database
        m = defaultdict(dict, f.config['Headers'])[self.ws.name]
        cols = self.headers()

        return [m[col] if col in m.keys() else col for col in cols]

    def headers(self):
        return self.header.value

    def fix_E(self, cols):
        # clear -E from df columns so excel doesn't translate to scientific
        df = self.df
        if not isinstance(cols, list): cols = [cols]
        for col in cols:
            df[col].loc[df[col].str.contains('E-')] = "'" + df[col]
    
    def to_excel(self, df=None):
        if df is None:
            df = self.df
        else:
            self.df = df

        self.fix_E(cols=list(filter(lambda x: x.lower() == 'model', df.columns)))
        
        app = self.app
        lsto = self.lsto
        app.screen_updating = False
        enable_events(app=app, val=False)

        self.clear_filter()
        self.clear_table()
        self.body.options(index=False, header=False).value = df

        app.screen_updating = True
        enable_events(app=app, val=True)

    def clear_filter(self):
        lsto = self.lsto
        if self.win and lsto.autofilter.filtermode: # win
            lsto.autofilter.showalldata()
        elif not self.win and lsto.autofilter_object.autofiltermode(): # mac
            self.ws.api.show_all_data()

    def clear_table(self):
        rng = self.body
        if len(rng.rows) > 1:
            rng[1:,:].delete()

        # listobject needs to always have 1 non empty row
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
