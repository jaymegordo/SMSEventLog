import operator
import sys
from datetime import (datetime as dt, timedelta as delta)
from pathlib import Path

import pandas as pd
import pypika as pk
import sqlalchemy as sa
from sqlalchemy import and_
from pypika import (
    Case,
    Criterion,
    CustomFunction as cf,
    Order,
    functions as fn,
    Query)

from . import (
    functions as f,
    gui as ui)
from .database import db

try:
    from IPython.display import display
except ModuleNotFoundError:
    pass


class Row(object):
    def __init__(self, tbl=None, i=None, keys={}, dbtable=None):
        # create with either: 1. gui.Table + row, or 2. dbtable + keys/values

        if not tbl is None:
            self.tbl = tbl # gui.Table class > the 'model' in mvc
            self.df = self.tbl.df
            dbtable = tbl.dbtable # dbm.TableName = table definition, NOT table object (eg TableName())
        
        if dbtable is None:
            raise AttributeError('db model table not set!')

        self.pks = dbtable.__table__.primary_key.columns.keys() # list of pk field names eg ['UID']

        if not i is None: # update from df
            for pk in self.pks:
                keys[pk] = self.df.iloc[i, self.df.columns.get_loc(pk)] # get ID value from ID field

        self.keys, self.dbtable = keys, dbtable

    def update(self, val, header=None, field=None):
        # update single value in database, based on unique row, field, value, and primary keys(s)
        t, keys = self.dbtable, self.keys

        if len(keys) == 0:
            raise AttributeError('Need to set keys before update!')
        
        cond = [getattr(t, pk)==keys[pk] for pk in keys] # list of multiple key:value pairs for AND clause

        # convert table header to db field name
        if field is None:
            field = f.convert_header(title=self.tbl.title, header=header)

        sql = sa.update(t).values({field: val}).where(and_(*cond))
        
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

def model_dict(model, include_none=False):
    # create dict from table model
    m = {a.key:getattr(model, a.key) for a in sa.inspect(model).mapper.column_attrs}
    if not include_none:
        m = {k:v for k,v in m.items() if v is not None}
    
    return m

def printModel(model, include_none=False):
    m = model_dict(model, include_none=include_none)
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
    startdate = dt(2020,3,28)
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
    df.columns = f.convert_list_db_view(title=title, cols=df.columns)

    return df
