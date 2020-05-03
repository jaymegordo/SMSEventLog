

import pandas as pd
import pypika as pk
import sqlalchemy as sa
# from pypika import Case, Criterion
# from pypika import CustomFunction as cf
# from pypika import Order, Query
# from pypika import functions as fn
from sqlalchemy import and_, literal

from . import functions as f
from .__init__ import *
from .database import db

try:
    from IPython.display import display
except ModuleNotFoundError:
    pass

log = logging.getLogger(__name__)

class Row(object):
    def __init__(self, tbl=None, i=None, keys={}, dbtable=None):
        # create with either: 1. gui.Table + row, or 2. dbtable + keys/values
        # tbl = gui.Table class > the 'model' in mvc
        
        if not tbl is None:
            df = tbl.df
            title = tbl.title
            if dbtable is None:
                dbtable = tbl.dbtable # dbm.TableName = table definition, NOT table object (eg TableName())
        
        if dbtable is None:
            raise AttributeError('db model table not set!')

        pks = dbtable.__table__.primary_key.columns.keys() # list of pk field names eg ['UID']

        if not i is None: # update keys from df
            for pk in pks:
                header = f.convert_header(title=title, header=pk, inverse_=True)
                keys[pk] = df.iloc[i, df.columns.get_loc(header)] # get key value from df, key must exist in df

        f.set_self(self, vars())

    def update_single(self, val, header=None, field=None, check_exists=False):
        # convenience func to update single field/header: val in db
        
        # convert table header to db field name
        if field is None:
            field = f.convert_header(title=self.title, header=header)
        
        self.update(vals={field: val}, check_exists=check_exists)

    def update(self, vals={}, delete=False, check_exists=False):
        # update (multiple) values in database, based on unique row, field, value, and primary keys(s)
        # key must either be passed in manually or exist in current table's df
        try:
            t, keys = self.dbtable, self.keys

            if len(keys) == 0:
                raise AttributeError('Need to set keys before update!')
            
            session = db.session
            cond = [getattr(t, pk)==keys[pk] for pk in keys] # list of multiple key:value pairs for AND clause

            if not delete:
                sql = sa.update(t).values(vals).where(and_(*cond))
                print(sql)
            else:
                sql = sa.delete(t).where(and_(*cond)) # kinda sketch to even have this here..

            if not check_exists:
                session.execute(sql)
            else:
                # Check if row exists, if not > create new row object, update it, add to session, commit
                q = session.query(t).filter(and_(*cond))
                exists = session.query(literal(True)).filter(q.exists()).scalar()

                if not exists:
                    e = t(**keys, **vals)
                    session.add(e)
                else:
                    session.execute(sql)
                
            session.commit()
        except:
            msg = f'Couldn\'t update value: {vals}'
            f.send_error(msg)
            log.error(msg)
    
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


def get_df(title=None, fltr=None):
    if fltr is None:
        if title is None:
            raise NameError('Missing Filter, title cannot be None!')
        fltr = Filter(title=title)

    title = fltr.title
    a = fltr.table # pypika Table
    q = None

    if title == 'Event Log':
        cols = ['UID', 'PassoverSort', 'StatusEvent', 'Unit', 'Title', 'Description', 'DateAdded', 'DateCompleted', 'IssueCategory', 'SubCategory', 'Cause', 'CreatedBy']

        q = Query.from_(a).select(*cols) \
                .orderby(a.DateAdded, a.Unit)

    elif title == 'Unit Info':

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
        b, c, d = pk.Tables('FCSummary', 'FCSummaryMineSite', 'UnitID')

        complete = Case().when(a.Complete==1, 'Y').else_('N').as_('Complete') # just renaming True to Y
        
        cols = [d.MineSite, a.Unit, a.FCNumber, a.Subject, b.Classification, c.Resp, b.Hours, b.PartNumber, c.PartAvailability, c.Comments, b.ReleaseDate, b.ExpiryDate, complete]

        q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('FCNumber') \
            .left_join(d).on(d.Unit==a.Unit) \
            .left_join(c).on((c.FCNumber==a.FCNumber) & (c.MineSite==d.MineSite)) \
            # .orderby(a.FCNumber)

    elif title == 'FC Details':
        b, c, d = pk.Tables('FCSummary', 'FCSummaryMineSite', 'UnitID')

        cols = [d.MineSite, d.Model, a.Unit, a.FCNumber, a.Complete, c.ManualClosed, a.Classification, a.Subject, a.DateCompleteSMS, a.DateCompleteKA, b.ExpiryDate, a.SMR, a.Notes]

        q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('FCNumber') \
            .left_join(d).on(d.Unit==a.Unit) \
            .left_join(c).on((c.FCNumber==a.FCNumber) & (c.MineSite==d.MineSite)) \
            .orderby(a.Unit, a.FCNumber)

    elif title == 'Component CO':
        b, c = pk.Tables('UnitID', 'ComponentType')

        cols = [a.UID, b.MineSite, b.Model, a.Unit, c.Component, c.Modifier, a.GroupCO, a.DateAdded, a.SMR, a.ComponentSMR, a.SNRemoved, a.SNInstalled, a.WarrantyYN, a.CapUSD, a.WorkOrder, a.SuncorWO, a.SuncorPO, a.Reman, a.SunCOReason, a.RemovalReason, a.COConfirmed]

        q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('Unit') \
            .inner_join(c).on_field('Floc') \
            .orderby(a.Unit, a.DateAdded, c.Modifier, a.GroupCO)

    if title in ('FC Summary', 'FC Details'):
        # bit sketch but need to always filter manualclosed to 'OR is null'
        lst = list(filter(lambda x: 'manualclosed' in x.lower(), fltr.criterion))
        if lst:
            fltr.criterion[lst[0]] |= c.ManualClosed.isnull()

    q = q.where(Criterion.all(fltr.get_criterion()))
    sql = q.get_sql().replace("'d'", '"d"') # TODO: fix for this was answered
    # print(sql)

    try:
        fltr.print_criterion()
        df = pd.read_sql(sql=sql, con=db.engine).pipe(f.parse_datecols)
        df.columns = f.convert_list_db_view(title=title, cols=df.columns)
    except:
        msg = 'Couldn\'t get dataframe.'
        f.send_error(msg=msg)
        log.error(msg)
        df = pd.DataFrame()

    return df

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

def print_model(model, include_none=False):
    m = f.model_dict(model, include_none=include_none)
    display(m)