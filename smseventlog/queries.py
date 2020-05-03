import operator

import pandas as pd
import pypika as pk
from pypika import Case, Criterion
from pypika import CustomFunction as cf
from pypika import Order, Query
from pypika import functions as fn

from . import functions as f
from .__init__ import *


class Filter():
    def __init__(self, base_table):
        criterion = {}
        f.set_self(self, vars())

    def add(self, field=None, val=None, vals=None, opr=operator.eq, term=None, table=None):
        if not vals is None:
            # not pretty, but pass in field/val with dict a bit easier
            field = list(vals.keys())[0]
            val = list(vals.values())[0]
        
        if table is None:
            table = self.base_table
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
        for ct in self.criterion.values():
            print('\t', list(ct.tables_)[0], ct)

class QueryBase(object):
    def __init__(self, minesite='FortHills'):
        m = f.config['TableName']
        title = m['Class'][self.__class__.__name__]
        base_table = pk.Table(m['Select'][title])

        f.set_self(self, vars())
        self.set_fltr()

    def get_sql(self):
        if hasattr(self, 'process_criterion'):
            self.process_criterion()

        ct = self.fltr.get_criterion()
        return self.q.where(Criterion.all(ct)).get_sql().replace("'d'", '"d"') # TODO: fix for this was answered
    
    def set_fltr(self):
        self.fltr = Filter(base_table=self.base_table)

class EventLog(QueryBase):
    def __init__(self):
        super().__init__()
        a = self.base_table

        cols = [a.UID, a.PassoverSort, a.StatusEvent, a.Unit, a.Title, a.Description, a.DateAdded, a.DateCompleted, a.IssueCategory, a.SubCategory, a.Cause, a.CreatedBy]

        self.q = Query.from_(a).select(*cols) \
                .orderby(a.DateAdded, a.Unit)

    def set_default_filter(self):
        self.fltr.add(field='MineSite', val=self.minesite)
        self.fltr.add(field='StatusEvent', val='complete', opr=operator.ne)

class WorkOrders(QueryBase):
    def __init__(self):
        super().__init__()

        a = self.base_table
        b = pk.Table('UnitID')

        cols = [a.UID, a.StatusWO, a.WarrantyYN, a.WorkOrder, a.Seg, a.SuncorWO, a.SuncorPO, b.Model, a.Unit, b.Serial, a.Title, a.PartNumber, a.SMR, a.DateAdded, a.DateCompleted, a.CreatedBy, a.WOComments, a.ComponentCO, a.Pictures]

        self.q = Query.from_(a).select(*cols) \
                    .left_join(b).on_field('Unit') \
                    .orderby(a.DateAdded, a.Unit)

    def set_default_filter(self):
        self.fltr.add(field='MineSite', val=self.minesite)
        self.fltr.add(field='StatusWO', val='open')

class ComponentCO(QueryBase):
    def __init__(self):
        super().__init__()
        a = self.base_table
        b, c = pk.Tables('UnitID', 'ComponentType')

        cols = [a.UID, b.MineSite, b.Model, a.Unit, c.Component, c.Modifier, a.GroupCO, a.DateAdded, a.SMR, a.ComponentSMR, a.SNRemoved, a.SNInstalled, a.WarrantyYN, a.CapUSD, a.WorkOrder, a.SuncorWO, a.SuncorPO, a.Reman, a.SunCOReason, a.RemovalReason, a.COConfirmed]

        self.q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('Unit') \
            .inner_join(c).on_field('Floc') \
            .orderby(a.Unit, a.DateAdded, c.Modifier, a.GroupCO)

    def set_default_filter(self):
        self.fltr.add(vals=dict(MineSite=self.minesite))
        self.fltr.add(vals=dict(DateAdded=dt.now().date() + delta(days=-30)))

class TSI(QueryBase):
    def __init__(self):
        super().__init__()
        a, b = self.base_table, pk.Table('UnitID')

        cols = [a.UID, a.StatusTSI, a.DateAdded, a.TSINumber, a.WorkOrder, a.Unit, b.Model, a.Title, a.SMR, a.ComponentSMR, a.TSIPartName, a.PartNumber, a.SNRemoved, a.TSIDetails, a.TSIAuthor]

        self.fltr.add(field='StatusTSI', term='notnull')
        
        self.q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('Unit') \
            .orderby(a.DateAdded, a.Unit)

    def set_default_filter(self):
        self.fltr.add(field='MineSite', val=self.minesite)
        self.fltr.add(field='StatusTSI', val='closed', opr=operator.ne)

class UnitInfo(QueryBase):
    def __init__(self):
        super().__init__()
        a = self.base_table
        isNumeric = cf('ISNUMERIC', ['val'])
        left = cf('LEFT', ['val', 'num'])

        c = pk.Table('UnitSMR')

        days = fn.DateDiff('d', a.DeliveryDate, fn.CurTimestamp())
        remaining = Case().when(days<=365, 365 - days).else_(0).as_('Remaining')
        remaining2 = Case().when(days<=365*2, 365*2 - days).else_(0)

        ge_remaining = Case().when(isNumeric(left(a.Model, 1))==1, remaining2).else_(None).as_('GE_Remaining')

        b = c.select(c.Unit, fn.Max(c.SMR).as_('CurrentSMR'), fn.Max(c.DateSMR).as_('DateSMR')).groupby(c.Unit).as_('b')

        cols = [a.MineSite, a.Customer, a.Model, a.Serial, a.EngineSerial, a.Unit, b.CurrentSMR, b.DateSMR, a.DeliveryDate, remaining, ge_remaining]

        self.q = Query.from_(a).select(*cols) \
                    .left_join(b).on_field('Unit')

    def set_default_filter(self):
        self.fltr.add(vals=dict(MineSite=self.minesite))

class FCBase(QueryBase):
    def __init__(self):
        super().__init__()
    
    def set_default_filter(self):
        fltr = self.fltr
        fltr.add(vals=dict(MineSite=self.minesite), table=pk.Table('UnitID'))
        fltr.add(vals=dict(ManualClosed=0), table=pk.Table('FCSummaryMineSite'))

    def process_criterion(self):
        # need to always filter manualclosed to 'OR is null'
        t = pk.Table('FCSummaryMineSite')
        fltr = self.fltr

        lst = list(filter(lambda x: 'manualclosed' in x.lower(), fltr.criterion))
        if lst:
            fltr.criterion[lst[0]] |= t.ManualClosed.isnull()

class FCSummary(FCBase):
    def __init__(self):
        super().__init__()
        a = self.base_table
        b, c, d = pk.Tables('FCSummary', 'FCSummaryMineSite', 'UnitID')

        complete = Case().when(a.Complete==1, 'Y').else_('N').as_('Complete') # just renaming True to Y
        
        cols = [d.MineSite, a.Unit, a.FCNumber, a.Subject, b.Classification, c.Resp, b.Hours, b.PartNumber, c.PartAvailability, c.Comments, b.ReleaseDate, b.ExpiryDate, complete]

        self.q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('FCNumber') \
            .left_join(d).on(d.Unit==a.Unit) \
            .left_join(c).on((c.FCNumber==a.FCNumber) & (c.MineSite==d.MineSite))

    def process_df(self, df):
        # pivot raw df for fc summary table
        try:
            # create summary (calc complete %s)
            df2 = pd.DataFrame()
            gb = df.groupby('FC Number')

            df2['Total'] = gb['Complete'].count()
            df2['Complete'] = gb.apply(lambda x: x[x['Complete']=='Y']['Complete'].count())
            df2['Total Complete'] = df2.Complete.astype(str) + ' / ' +  df2.Total.astype(str)
            df2['% Complete'] = df2.Complete / df2.Total
            df2.drop(columns=['Total', 'Complete'], inplace=True)

            # pivot - note: can't pivot properly if Hours column (int) is NULL.. just make sure its filled
            index = [c for c in df.columns if not c in ('Unit', 'Complete')] # use all df columns except unit, complete
            df = df.pipe(f.multiIndex_pivot, index=index, columns='Unit', values='Complete').reset_index()

            # merge summary
            df = df.merge(right=df2, how='left', on='FC Number')

            # reorder cols after merge
            cols = list(df)
            endcol = 10
            cols.insert(endcol + 1, cols.pop(cols.index('Total Complete')))
            cols.insert(endcol + 2, cols.pop(cols.index('% Complete')))
            df = df.loc[:, cols]

            df = f.sort_df_by_list(df=df, lst=['M', 'FAF', 'DO', 'FT'], lst_col='Type', sort_cols='FC Number')

        except:
            f.send_error(msg='Can\'t pivot fc summary dataframe')

        return df      

class FCDetails(FCBase):
    def __init__(self):
        super().__init__()
        a = self.base_table
        b, c, d = pk.Tables('FCSummary', 'FCSummaryMineSite', 'UnitID')

        cols = [d.MineSite, d.Model, a.Unit, a.FCNumber, a.Complete, c.ManualClosed, a.Classification, a.Subject, a.DateCompleteSMS, a.DateCompleteKA, b.ExpiryDate, a.SMR, a.Notes]

        self.q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('FCNumber') \
            .left_join(d).on(d.Unit==a.Unit) \
            .left_join(c).on((c.FCNumber==a.FCNumber) & (c.MineSite==d.MineSite)) \
            .orderby(a.Unit, a.FCNumber)

    def set_default_filter(self):
        super().set_default_filter()
        self.fltr.add(vals=dict(Complete=0))

class EmailList(QueryBase):
    def __init__(self):
        super().__init__()
        a = self.base_table

        self.q = Query.from_(a).select('*') \
            .orderby(a.MineSite, a.Email)

    def set_default_filter(self):
        self.fltr.add(vals=dict(MineSite=self.minesite))