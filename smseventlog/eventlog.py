import json
import operator
import sys
from collections import defaultdict
from datetime import datetime as date
from datetime import timedelta as delta
from pathlib import Path
from timeit import default_timer as timer
from urllib import parse

import pandas as pd
import pypika as pk
import sqlalchemy as sa
import xlwings as xw
import yaml
from pkg_resources import parse_version
from pypika import Case, Criterion
from pypika import CustomFunction as cf
from pypika import Order
from pypika import functions as fn

import folders as fl
import functions as f
import gui as ui
from database import db

try:
    from IPython.display import display
except ModuleNotFoundError:
    pass


global title, titlename
titlename = 'SMS Event Log'
title = titlename + '.xlsm'

class Row(object):
    def __init__(self, tbl, i):
        self.tbl = tbl # Table class
        self.df = self.tbl.df

        self.i = i # row index in df
        # need to check for multi-column key eventually
        self.pk = tbl.table.__table__.primary_key.columns.keys()[0] # pk field name eg 'UID'

        # get ID value from ID field
        self.id = self.df.iloc[i, self.df.columns.get_loc(self.pk)]

    def update(self, header, val):
        if self.id is None:
            raise AttributeError('Need to set id before update!')

        t, pk, i, id = self.tbl.table, self.pk, self.i, self.id

        pk_field = getattr(t, pk)

        # TODO: maybe check if this needs to always be converted?
        field = f.convert_header(title=self.tbl.title, header=header)

        sql = sa.update(t).where(pk_field==id).values({field: val})
        # print(i, val, id, self.df.index[i])
        session = db.session
        session.execute(sql)
        session.commit()

    def printself(self):
        m = dict(
            title=self.tbl.title,
            table=self.tbl.tablename,
            pk=self.pk,
            id=self.id)
        display(m)

def printModel(model, null=False):
    m = {a.key:getattr(model, a.key) for a in inspect(model).mapper.column_attrs}
    if not null:
        m = {k:v for k,v in m.items() if v is not None}
    display(m)

class Filter():
    def __init__(self, title):
        self.criterion = []
        self.title = title
        self.table = pk.Table(f.config['TableName'][title])

    def add(self, field, val=None, opr=operator.eq, term=None):
        field_ = self.table.field(field)
        lst = self.criterion

        if not term is None:
            lst.append(getattr(field_, term)())
        elif isinstance(val, str):
            if '%' in val:
                lst.append(field_.like(val))
            else:
                lst.append(opr(field_, val))
        elif isinstance(val, int):
            lst.append(opr(field_, val))
        elif isinstance(val, date):
            # TODO: opp gt 
            lst.append(field_ >= val)
    
    def add_complete(self, criterion):
        self.criterion.append(criterion)

    def print_criterion(self):
        for item in self.criterion:
            print(str(item))

def get_df(title=None, fltr=None, defaults=False):
    if fltr is None:
        if title is None:
            raise NameError('Missing Filter, title cannot be None!')
        fltr = Filter(title=title)

    title = fltr.title
    a = fltr.table
    q = None

    # defaults
    startdate = date(2020,3,6)
    if defaults and a.get_table_name() == 'EventLog':
        fltr.add(field='DateAdded', val=startdate)
        fltr.add(field='MineSite', val='FortHills')

    if title == 'Event Log':
        cols = ['UID', 'PassoverSort', 'StatusEvent', 'Unit', 'Title', 'Description', 'DateAdded', 'DateCompleted', 'IssueCategory', 'SubCategory', 'Cause', 'CreatedBy']


    elif title == 'Unit Info':
        if defaults:
            fltr.add(field='model', val='980E%')

        isNumeric = cf('ISNUMERIC', ['val'])
        left = cf('LEFT', ['val', 'num'])

        c = pk.Table('UnitSMR')

        days = fn.DateDiff('d', a.DeliveryDate, fn.CurTimestamp())
        remaining = Case().when(days<=365, 365 - days).else_(0).as_('Remaining')
        remaining2 = Case().when(days<=365*2, 365*2 - days).else_(0)

        ge_remaining = Case().when(isNumeric(left(a.Model, 1))==1, remaining2).else_(None).as_('GE_Remaining')

        b = c.select(c.Unit, fn.Max(c.SMR).as_('CurrentSMR'), fn.Max(c.DateSMR).as_('DateSMR')).groupby(c.Unit).as_('b')

        cols = [a.MineSite, a.Customer, a.Model, a.Serial, a.EngineSerial, a.Unit, b.CurrentSMR, b.DateSMR, a.DeliveryDate, remaining, ge_remaining]

        q = pk.Query.from_(a).select(*cols) \
                    .left_join(b).on_field('Unit')  
           
    elif title == 'Work Orders':
        b = pk.Table('UnitID')

        cols = [a.UID, a.StatusWO, a.WarrantyYN, a.WorkOrder, a.Seg, a.SuncorWO, a.SuncorPO, b.Model, a.Unit, b.Serial, a.Title, a.PartNumber, a.SMR, a.DateAdded, a.DateCompleted, a.CreatedBy, a.WOComments, a.ComponentCO, a.Downloads, a.Pictures]

        q = pk.Query.from_(a).select(*cols) \
                    .left_join(b).on_field('Unit')  

    elif title == 'TSI':
        b = pk.Table('UnitID')

        cols = [a.UID, a.StatusTSI, a.DateAdded, a.TSINumber, a.WorkOrder, a.Unit, b.Model, a.Title, a.SMR, a.ComponentSMR, a.TSIPartName, a.PartNumber, a.SNRemoved, a.TSIDetails, a.TSIAuthor]

        fltr.add(field='StatusTSI', term='notnull')
        
        q = pk.Query.from_(a).select(*cols) \
            .left_join(b).on_field('Unit')

    elif title == 'FC Summary':
        # this will need to be a query from db
        cols = []

    elif title == 'FC Details':
        # calculated
        cols = []

    elif title == 'Component CO':
        b = pk.Table('UnitID')
        c = pk.Table('ComponentType')

        cols = [a.UID, b.MineSite, b.Model, a.Unit, c.Component, c.Modifier, a.GroupCO, a.DateAdded, a.SMR, a.ComponentSMR, a.SNRemoved, a.SNInstalled, a.WarrantyYN, a.CapUSD, a.WorkOrder, a.SuncorWO, a.SuncorPO, a.Reman, a.SunCOReason, a.RemovalReason, a.COConfirmed]

        q = pk.Query.from_(a).select(*cols) \
            .left_join(b).on_field('Unit').inner_join(c).on_field('Floc') \
            .orderby(a.Unit, a.DateAdded, c.Modifier, a.GroupCO)

    if q is None:
        q = pk.Query.from_(a).select(*cols) \
    
    q = q.where(Criterion.all(fltr.criterion))
    sql = q.get_sql().replace("'d'", '"d"')
    
    datecols = ['DateAdded', 'DateCompleted', 'TimeCalled', 'DateSMR', 'DeliveryDate']
    df = pd.read_sql(sql=sql, con=db.engine, parse_dates=datecols)
    df.columns = f.convert_headers(title=title, cols=df.columns)

    return df


# UPDATE
def push_update_ui(vertype='patch'):
    wb = book()
    # get old version
    rng = book().sheets('version').range('version2')
    v_current = parse_version(rng.value)

    # update version range
    v_new = f.bump_version(ver=v_current, vertype=vertype)
    rng.value = v_new

    # update .txt
    p = v_txt()
    p.rename(p.parent / f'{v_new}.txt')

    msg = f'{title} UI updated.\n\nOld: {v_current.base_version}\nNew: {v_new}'
    # ui.msg_simple(msg=msg)
    print(msg)

def v_txt():
    p = Path(__file__).parent / 'data/excel/'
    return sorted(p.glob('*.txt'))[0]

def v_check():
    return parse_version(v_txt().name.strip('.txt'))

def v_current():
    return parse_version(book().sheets('version').range('version2').value)

def check_ver_ui():
    ans = True if v_check() > v_current() else False
    return ans

def check_update_ui():
    # TODO: make sure this works when run from excel
    # copy new excel file from site-packages and replace currently active book
    if check_ver_ui():

        msg = f'A new version of the EventLog UI is available.\n\nCurrent: {v_current()}\nNew: {v_check()}\n\nWould you like to update?'
        if ui.msgbox(msg=msg, yesno=True):

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
            ui.msgbox(msg=msg)


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
    lsto = TableExcel(ws=ws)

def book():
    return xw.books(title)


# TABLE - class to bridge excel listobjects, dataframes, and xlwings ranges
class TableExcel():
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


    # if title is None:
    #     ws = xw.books.active.sheets.active
    #     title = ws.name
    # else:
    #     ws = book().sheets(title)

    # tbl = Table(ws=ws)
    # cols = tbl.headers_db()
