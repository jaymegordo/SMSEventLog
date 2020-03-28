import operator
import sys
from datetime import (datetime as date, timedelta as delta)
from pathlib import Path
from urllib import parse

import pandas as pd
import pypika as pk
import sqlalchemy as sa

from pypika import (
    Case,
    Criterion,
    CustomFunction as cf,
    Order,
    functions as fn,
    Query)

# print('EVENTLOG __file__: {}'.format(__file__))
# print('EVENTLOG __package__: {}'.format(__package__))
# print('smseventlog in sys.modules: {}'.format('smseventlog' in sys.modules))
# print('EVENTLOG Current directory: {}'.format(Path.cwd()))

from . import (
    functions as f,
    gui as ui)
from .database import db


try:
    from IPython.display import display
except ModuleNotFoundError:
    pass


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
    m = {a.key:getattr(model, a.key) for a in sa.inspect(model).mapper.column_attrs}
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

        q = Query.from_(a).select(*cols) \
                    .left_join(b).on_field('Unit')  
           
    elif title == 'Work Orders':
        b = pk.Table('UnitID')

        cols = [a.UID, a.StatusWO, a.WarrantyYN, a.WorkOrder, a.Seg, a.SuncorWO, a.SuncorPO, b.Model, a.Unit, b.Serial, a.Title, a.PartNumber, a.SMR, a.DateAdded, a.DateCompleted, a.CreatedBy, a.WOComments, a.ComponentCO, a.Downloads, a.Pictures]

        q = Query.from_(a).select(*cols) \
                    .left_join(b).on_field('Unit')  

    elif title == 'TSI':
        b = pk.Table('UnitID')

        cols = [a.UID, a.StatusTSI, a.DateAdded, a.TSINumber, a.WorkOrder, a.Unit, b.Model, a.Title, a.SMR, a.ComponentSMR, a.TSIPartName, a.PartNumber, a.SNRemoved, a.TSIDetails, a.TSIAuthor]

        fltr.add(field='StatusTSI', term='notnull')
        
        q = Query.from_(a).select(*cols) \
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

        q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('Unit').inner_join(c).on_field('Floc') \
            .orderby(a.Unit, a.DateAdded, c.Modifier, a.GroupCO)

    if q is None:
        q = Query.from_(a).select(*cols) \
    
    q = q.where(Criterion.all(fltr.criterion))
    sql = q.get_sql().replace("'d'", '"d"')
    
    datecols = ['DateAdded', 'DateCompleted', 'TimeCalled', 'DateSMR', 'DeliveryDate']
    df = pd.read_sql(sql=sql, con=db.engine, parse_dates=datecols)
    df.columns = f.convert_headers(title=title, cols=df.columns)

    return df