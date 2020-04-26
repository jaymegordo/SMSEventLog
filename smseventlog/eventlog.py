import operator
import sys
from datetime import date
from datetime import datetime as dt
from datetime import timedelta as delta
from pathlib import Path

import pandas as pd
import pypika as pk
import sqlalchemy as sa
from pypika import Case, Criterion
from pypika import CustomFunction as cf
from pypika import Order, Query
from pypika import functions as fn
from sqlalchemy import and_

from . import functions as f
from .database import db

try:
    from IPython.display import display
except ModuleNotFoundError:
    pass


def test_fcsummary():
    fltr = Filter(title='FC Summary')
    # fltr.add(field='Classification', val='M', table=pk.Table('FCSummary'))
    fltr.add(field='MineSite', val='FortHills', table=pk.Table('UnitID'))
    fltr.add(field='ManualClosed', val=0, table=pk.Table('FCSummaryMineSite'))
    fltr.print_criterion()

    df = get_df(fltr=fltr)
    # return df

    # create summary (calc complete %s)
    df2 = pd.DataFrame()
    gb = df.groupby('FC Number')
    df2['Total'] = gb['Complete'].count()
    df2['Complete'] = gb.apply(lambda x: x[x['Complete']=='Y']['Complete'].count())
    df2['Total Complete'] = df2.Complete.astype(str) + ' / ' +  df2.Total.astype(str)
    df2['% Complete'] = df2.Complete / df2.Total
    df2.drop(columns=['Total', 'Complete'], inplace=True)

    # pivot
    index = [c for c in df.columns if not c in ('Unit', 'Complete')] # use all df columns except unit, complete
    df = df.pipe(f.multiIndex_pivot, index=index, columns='Unit', values='Complete').reset_index()

    # merge summary
    df = df.merge(right=df2, how='left', on='FC Number')

    # reorder cols after merge
    cols = list(df)
    cols.insert(10, cols.pop(cols.index('Total Complete')))
    cols.insert(11, cols.pop(cols.index('% Complete')))
    df = df.loc[:, cols]

    return df

class Row(object):
    def __init__(self, tbl=None, i=None, keys={}, dbtable=None):
        # create with either: 1. gui.Table + row, or 2. dbtable + keys/values
        self.i = i

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

    def update_single(self, val, header=None, field=None):
        # convenience func to update single field/header: val in db
        
        # convert table header to db field name
        if field is None:
            field = f.convert_header(title=self.tbl.title, header=header)
        
        self.update(vals={field: val})

    def update(self, vals={}, delete=False):
        # update (multiple) values in database, based on unique row, field, value, and primary keys(s)
        t, keys = self.dbtable, self.keys

        if len(keys) == 0:
            raise AttributeError('Need to set keys before update!')
        
        cond = [getattr(t, pk)==keys[pk] for pk in keys] # list of multiple key:value pairs for AND clause

        if not delete:
            sql = sa.update(t).values(vals).where(and_(*cond))
        else:
            sql = sa.delete(t).where(and_(*cond))
               
        session = db.session
        session.execute(sql)
        session.commit()
    
    def create_model_from_db(self):
        # query sqalchemy orm session using model eg dbo.EventLog, and keys eg {UID=123456789}
        # return instance of model
        session = db.session
        e = session.query(self.dbtable).get(self.keys)

        return e

    def printself(self):
        m = dict(
            title=self.tbl.title,
            table=self.tbl.tablename,
            pk=self.pk,
            id=self.id)
        display(m)

def print_model(model, include_none=False):
    m = f.model_dict(model, include_none=include_none)
    display(m)

class Filter():
    def __init__(self, title):
        self.criterion = {}
        self.title = title
        self.table = pk.Table(f.config['TableName'][title])

    def add(self, field=None, val=None, vals=None, opr=operator.eq, term=None, table=None):
        if not vals is None:
            # not pretty, but pass in field/val with dict a bit easier
            field = list(vals.keys())[0]
            val = list(vals.values())[0]
        
        if table is None:
            table = self.table
            # otherwise must pass in a pk.Table()
            
        field_ = table.field(field)

        if not term is None:
            ct = getattr(field_, term)()
        elif isinstance(val, str):
            if '%' in val:
                ct = field_.like(val)
            else:
                ct = opr(field_, val)
        elif isinstance(val, int):
            ct = opr(field_, val)
        elif isinstance(val, (dt, date)):
            # TODO: opp gt (greater than)
            ct = field_ >= val
        
        self.add_criterion(ct=ct)
    
    def add_criterion(self, ct):
        # check for duplicate criterion, use str(ct) as dict key for actual ct
        # can also use this to pass in a completed pk criterion eg (pk.Table().field() == val)
        self.criterion[str(ct)] = ct
    
    def get_criterion(self):
        return self.criterion.values()

    def print_criterion(self):
        print(self.title)
        for item in self.criterion.values():
            print(item.tables_, item)

def get_df(title=None, fltr=None, defaults=False):
    if fltr is None:
        if title is None:
            raise NameError('Missing Filter, title cannot be None!')
        fltr = Filter(title=title)

    title = fltr.title
    a = fltr.table # pypika Table
    q = None

    # defaults
    startdate = dt(2020,3,28)
    if defaults and a.get_table_name() == 'EventLog':
        fltr.add(field='DateAdded', val=startdate)
        fltr.add(field='MineSite', val='FortHills')

    if title == 'Event Log':
        cols = ['UID', 'PassoverSort', 'StatusEvent', 'Unit', 'Title', 'Description', 'DateAdded', 'DateCompleted', 'IssueCategory', 'SubCategory', 'Cause', 'CreatedBy']

        q = Query.from_(a).select(*cols) \
                .orderby(a.DateAdded, a.Unit)

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

        cols = [a.UID, a.StatusWO, a.WarrantyYN, a.WorkOrder, a.Seg, a.SuncorWO, a.SuncorPO, b.Model, a.Unit, b.Serial, a.Title, a.PartNumber, a.SMR, a.DateAdded, a.DateCompleted, a.CreatedBy, a.WOComments, a.ComponentCO, a.Pictures]

        q = Query.from_(a).select(*cols) \
                    .left_join(b).on_field('Unit') \
                    .orderby(a.DateAdded, a.Unit)

    elif title == 'TSI':
        b = pk.Table('UnitID')

        cols = [a.UID, a.StatusTSI, a.DateAdded, a.TSINumber, a.WorkOrder, a.Unit, b.Model, a.Title, a.SMR, a.ComponentSMR, a.TSIPartName, a.PartNumber, a.SNRemoved, a.TSIDetails, a.TSIAuthor]

        fltr.add(field='StatusTSI', term='notnull')
        
        q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('Unit') \
            .orderby(a.DateAdded, a.Unit)

    elif title == 'FC Summary':
        b, c, d, e = pk.Tables('FCSummary', 'FCSummaryMineSite', 'UnitID', 'EventLog')

        # TODO: bit of duplication here with db
        subject = Case().when(b.SubjectShort.notnull(), b.SubjectShort).else_(b.Subject).as_('Subject')
        complete = Case().when(
            a.DateCompleteSMS.isnull() & \
            a.DateCompleteKA.isnull() & \
            e.DateCompleted.isnull(), 'N').else_('Y').as_('Complete')
        # customsort = Case() \
        #     .when(b.Classification=='M', 1) \
        #     .when(b.Classification=='FAF', 2).else_(3)
        
        cols = [a.Unit, a.FCNumber, subject, b.Classification, c.Resp, b.Hours, b.PartNumber, c.PartAvailability, c.Comments, b.ReleaseDate, b.ExpiryDate, complete]

        q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('FCNumber') \
            .left_join(c).on_field('FCNumber') \
            .left_join(d).on((d.Unit == a.Unit) & (d.MineSite == c.MineSite)) \
            .left_join(e).on_field('UID') \
            .orderby(a.FCNumber)

    elif title == 'FC Details':
        # select from viewFactoryCampaign
        cols = []

    elif title == 'Component CO':
        b, c = pk.Tables('UnitID', 'ComponentType')
        # TODO: Need to filter on UnitID.MineSite, not event log

        cols = [a.UID, b.MineSite, b.Model, a.Unit, c.Component, c.Modifier, a.GroupCO, a.DateAdded, a.SMR, a.ComponentSMR, a.SNRemoved, a.SNInstalled, a.WarrantyYN, a.CapUSD, a.WorkOrder, a.SuncorWO, a.SuncorPO, a.Reman, a.SunCOReason, a.RemovalReason, a.COConfirmed]

        q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('Unit').inner_join(c).on_field('Floc') \
            .orderby(a.Unit, a.DateAdded, c.Modifier, a.GroupCO)

    if q is None:
        q = Query.from_(a).select(*cols) \
    
    q = q.where(Criterion.all(fltr.get_criterion()))
    sql = q.get_sql().replace("'d'", '"d"') # TODO: fix for this was answered
    # print(sql)
    
    datecols = ['DateAdded', 'DateCompleted', 'TimeCalled', 'DateSMR', 'DeliveryDate', 'ReleaseDate', 'ExpiryDate']
    df = pd.read_sql(sql=sql, con=db.engine, parse_dates=datecols)
    df.columns = f.convert_list_db_view(title=title, cols=df.columns)

    return df

# df2 = pd.DataFrame()
# df2['Complete'] = pd.DataFrame(df.iloc[:,10:]=='Y').sum(axis=1) # complete
# pd.DataFrame(df.iloc[:,10:].notnull()).sum(axis=1) # total
