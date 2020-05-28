import inspect

import numpy as np
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap, ListedColormap

from . import dbmodel as dbm
from . import functions as f
from .__init__ import *


class Filter():
    def __init__(self, parent):
        # fltr has to belong to a query object
        criterion, fields = {}, {}
        select_table = parent.select_table
        f.set_self(self, vars())

    def add(self, field=None, val=None, vals=None, opr=None, term=None, table=None, ct=None):
        if not vals is None:
            # not pretty, but pass in field/val with dict a bit easier
            field = list(vals.keys())[0]
            val = list(vals.values())[0]
        
        if table is None:
            table = self.select_table
            # otherwise must pass in a T()
            
        field_ = table.field(field)
        if ct is None:
            if not term is None:
                func = getattr(field_, term)
                # between
                if val:
                    ct = func(*val)
                else:
                    ct = func()
            elif isinstance(val, str):
                if '%' in val:
                    ct = field_.like(val)
                else:
                    if opr is None: opr = op.eq
                    ct = opr(field_, val)
            elif isinstance(val, int):
                if opr is None: opr = op.eq
                ct = opr(field_, val)
            elif isinstance(val, (dt, date)):
                # TODO: opp gt (greater than)
                if opr is None: opr = op.ge
                ct = opr(field_, val)
        
        self.add_criterion(ct=ct)
    
    def add_criterion(self, ct):
        # check for duplicate criterion, use str(ct) as dict key for actual ct
        # can also use this to pass in a completed pk criterion eg (T().field() == val)
        self.criterion[str(ct)] = ct

        if hasattr(ct, 'left'):
            field = ct.left.name
        elif hasattr(ct, 'term'):
            field = list(ct.term.fields_())[0].name

        self.fields[field.lower()] = ct
    
    def check_criterion(self, field):
        # check if field is in criterion fields - not sure if I need this
        lst = list(filter(lambda x: field.lower() in x.lower(), self.criterion))
        ans = True if lst else False
        return ans
    
    def get_criterion(self, field):
        # return criterion containing selected field 
        lst = list(filter(lambda x: field.lower() in x.lower(), self.criterion))
        ans = lst[0] if lst else None
        return ans

    def get_all_criterion(self):
        return self.criterion.values()

    def print_criterion(self):
        for ct in self.criterion.values():
            print('\t', list(ct.tables_)[0], ct)

class QueryBase(object):
    def __init__(self, minesite='FortHills', kw=None):
        view_cols, formats = {}, {}
        background_gradients = []
        cmap = sns.diverging_palette(240, 10, sep=10, n=21, as_cmap=True)
        sql, df = None, pd.DataFrame()
        m = f.config['TableName']
        name = self.__class__.__name__

        # loop base classes to get first working title, need this to map view_cols
        for base_class in inspect.getmro(self.__class__):
            title = m['Class'].get(base_class.__name__, None)
            if not title is None: break

        # loop through base classes till we find a working select_table
        for base_class in inspect.getmro(self.__class__):
            select_tablename = m['Select'].get(base_class.__name__, None)
            if not select_tablename is None: break
        
        select_table = T(select_tablename)
        
        # try to get updatetable, if none set as name of select table
        if not select_tablename is None:
            update_tablename = m['Update'].get(name, select_tablename)
            update_table = getattr(dbm, update_tablename, None)

        f.set_self(self, vars())
        self.set_fltr()

        if not kw is None and hasattr(self, 'set_default_args'):
            self.set_default_args(**kw)

    def get_sql(self):
        sql = self.sql
        if sql is None:
            q = self.q
            if hasattr(self, 'process_criterion'):
                self.process_criterion()

            sql = q.select(*self.cols) \
                .where(Criterion.all(self.fltr.get_all_criterion())) \
                .get_sql().replace("'d'", '"d"') # TODO: fix for this was answered

        return sql
    
    def set_fltr(self):
        self.fltr = Filter(parent=self)
    
    def set_lastperiod(self, days=7):
        if not self.date_col is None:
            vals = {self.date_col: dt.now().date() + delta(days=days * -1)}
            self.fltr.add(vals=vals, opr=op.ge)
        else:
            raise ValueError('date_col not set!')
    
    def set_lastweek(self):
        self.set_lastperiod(days=7)
    
    def set_lastmonth(self):
        self.set_lastperiod(days=31)
    
    def get_updatetable(self):
        tablename = self.select_table if self.update_table is None else self.select_table
        return getattr(dbm, tablename) # db model definition, NOT instance

    def add_fltr_args(self, args):
        if not isinstance(args, list): args = [args]
        for kw in args:
            self.fltr.add(**kw)
    
    def get_df(self, default=False):
        from .database import db
        self.df = db.get_df(query=self, default=default)
        return self.df

class EventLogBase(QueryBase):
    def __init__(self, kw=None):
        super().__init__(kw=kw)
        a, b = self.select_table, T('UnitID')
        date_col = 'DateAdded'
        f.set_self(self, vars())
    
    def set_minesite(self):
        self.fltr.add(vals=dict(MineSite=self.minesite), table=T('UnitID'))
    
    def set_default_filter(self):
        self.set_minesite()
        self.set_allopen()

class EventLog(EventLogBase):
    def __init__(self):
        super().__init__()
        a, b = self.a, self.b

        cols = [a.UID, a.PassoverSort, a.StatusEvent, a.Unit, a.Title, a.Description, a.DateAdded, a.DateCompleted, a.IssueCategory, a.SubCategory, a.Cause, a.CreatedBy]

        q = Query.from_(a) \
            .left_join(b).on_field('Unit') \
            .orderby(a.DateAdded, a.Unit)
        
        f.set_self(self, vars())
    
    def set_allopen(self):
        self.fltr.add(field='StatusEvent', val='complete', opr=op.ne)

class WorkOrders(EventLogBase):
    def __init__(self):
        super().__init__()
        a, b = self.a, self.b

        cols = [a.UID, a.StatusWO, a.WarrantyYN, a.WorkOrder, a.Seg, a.SuncorWO, a.SuncorPO, b.Model, a.Unit, b.Serial, a.Title, a.PartNumber, a.SMR, a.DateAdded, a.DateCompleted, a.CreatedBy, a.WOComments, a.ComponentCO, a.Pictures]

        q = Query.from_(a) \
                .left_join(b).on_field('Unit') \
                .orderby(a.DateAdded, a.Unit)

        f.set_self(self, vars())    
   
    def set_allopen(self):
        self.fltr.add(field='StatusWO', val='open')

class ComponentCOBase(EventLogBase):
    def __init__(self, kw=None):
        super().__init__(kw=kw)
        a, b, c = self.a, self.b, T('ComponentType')

        q = Query.from_(a) \
            .left_join(b).on_field('Unit') \
            .inner_join(c).on_field('Floc') \
            .orderby(a.Unit, a.DateAdded, c.Modifier, a.GroupCO)

        f.set_self(self, vars())

    def set_default_filter(self):
        super().set_default_filter()
        self.fltr.add(vals=dict(DateAdded=dt.now().date() + delta(days=-30)))

    def set_allopen(self):
        self.fltr.add(field='COConfirmed', val='False')

class ComponentCO(ComponentCOBase):
    def __init__(self):
        super().__init__()
        a, b, c = self.a, self.b, self.c

        cols = [a.UID, b.MineSite, b.Model, a.Unit, c.Component, c.Modifier, a.GroupCO, a.DateAdded, a.SMR, a.ComponentSMR, a.SNRemoved, a.SNInstalled, a.WarrantyYN, a.CapUSD, a.WorkOrder, a.SuncorWO, a.SuncorPO, a.Reman, a.SunCOReason, a.RemovalReason, a.COConfirmed]

        f.set_self(self, vars())

class ComponentCOReport(ComponentCOBase):
    def __init__(self, kw):
        super().__init__(kw=kw)

        # self.formats.update({
        #     'Life Remaining': '{:,.0f}'})
        self.view_cols.update(
            BenchSMR='Bench SMR')

        a, b, c = self.a, self.b, self.c
        life_remaining = (a.ComponentSMR - c.BenchSMR).as_('Life Achieved')

        cols = [b.Model, a.Unit, c.Component, c.Modifier, a.DateAdded, a.ComponentSMR, c.BenchSMR, life_remaining, a.SunCOReason]

        f.set_self(self, vars())
    
    def process_df(self, df):
        # df[cols] = df[cols].fillna(pd.NA)
        df.pipe(f.convert_dtypes, cols=['Comp SMR', 'Life Achieved', 'Bench SMR'], col_type='Int64')
        return df

    def set_default_args(self, d_rng, minesite):
        self.add_fltr_args([
            dict(vals=dict(DateAdded=d_rng), term='between'),
            dict(vals=dict(MineSite=minesite), table=T('UnitID'))])
    
    def update_style(self, style, df):
        subset = pd.IndexSlice[df['Life Achieved'].notnull(), 'Life Achieved']
        style.background_gradient(cmap=self.cmap.reversed(), subset=subset, axis=None)

class TSI(EventLogBase):
    def __init__(self):
        super().__init__()
        a, b = self.a, self.b

        cols = [a.UID, a.StatusTSI, a.DateAdded, a.TSINumber, a.WorkOrder, a.Unit, b.Model, a.Title, a.SMR, a.ComponentSMR, a.TSIPartName, a.PartNumber, a.SNRemoved, a.TSIDetails, a.TSIAuthor]
        
        q = Query.from_(a) \
            .left_join(b).on_field('Unit') \
            .orderby(a.DateAdded, a.Unit)

        f.set_self(self, vars())

    def set_allopen(self):
        self.fltr.add(field='StatusTSI', val='closed', opr=op.ne)
    
    def set_fltr(self):
        super().set_fltr()
        self.fltr.add(field='StatusTSI', term='notnull')

class UnitInfo(QueryBase):
    def __init__(self):
        super().__init__()
        a = self.select_table
        isNumeric = cf('ISNUMERIC', ['val'])
        left = cf('LEFT', ['val', 'num'])

        c = T('UnitSMR')

        days = fn.DateDiff('d', a.DeliveryDate, fn.CurTimestamp())
        remaining = Case().when(days<=365, 365 - days).else_(0).as_('Remaining')
        remaining2 = Case().when(days<=365*2, 365*2 - days).else_(0)

        ge_remaining = Case().when(isNumeric(left(a.Model, 1))==1, remaining2).else_(None).as_('GE_Remaining')

        b = c.select(c.Unit, fn.Max(c.SMR).as_('CurrentSMR'), fn.Max(c.DateSMR).as_('DateSMR')).groupby(c.Unit).as_('b')

        cols = [a.MineSite, a.Customer, a.Model, a.Serial, a.EngineSerial, a.Unit, b.CurrentSMR, b.DateSMR, a.DeliveryDate, remaining, ge_remaining]

        q = Query.from_(a) \
                .left_join(b).on_field('Unit')
        
        f.set_self(self, vars())

    def set_default_filter(self):
        self.fltr.add(vals=dict(MineSite=self.minesite))

class FCBase(QueryBase):
    def __init__(self):
        super().__init__()
        a = self.select_table
        b, c, d = pk.Tables('FCSummary', 'FCSummaryMineSite', 'UnitID')

        q = Query.from_(a) \
            .left_join(b).on_field('FCNumber') \
            .left_join(d).on(d.Unit==a.Unit) \
            .left_join(c).on((c.FCNumber==a.FCNumber) & (c.MineSite==d.MineSite))

        f.set_self(self, vars())

    def set_default_filter(self):
        self.fltr.add(vals=dict(MineSite=self.minesite), table=T('UnitID'))
        self.set_allopen()
    
    def set_allopen(self):
        self.fltr.add(vals=dict(ManualClosed=0), table=T('FCSummaryMineSite'))

    def process_criterion(self):
        # need to always filter manualclosed to 'OR is null'
        t = T('FCSummaryMineSite')
        fltr = self.fltr

        ct = fltr.get_criterion(field='manualclosed')
        if not ct is None:
            fltr.criterion[ct] |= t.ManualClosed.isnull() # need to operate on the original dict, not copy ct

class FCSummary(FCBase):
    def __init__(self):
        super().__init__()

        self.formats.update({
            '% Complete': '{:.2%}',
            'Hrs': '{:.0f}'})

        a, b, c, d = self.a, self.b, self.c, self.d

        complete = Case().when(a.Complete==1, 'Y').else_('N').as_('Complete') # just renaming True to Y
        
        self.cols = [d.MineSite, a.Unit, a.FCNumber, a.Subject, b.Classification, c.Resp, b.Hours, b.PartNumber, c.PartAvailability, c.Comments, b.ReleaseDate, b.ExpiryDate, complete]

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

class FCSummaryReport(FCSummary):
    def __init__(self):
        super().__init__()
    
    def get_df(self, default=False):
        from .database import db
        df = db.get_df(query=self, default=default)
        self.df = df
        return df[df.columns[:8]]

    def process_df(self, df):
        df = super().process_df(df)
        df.drop(columns=['MineSite', 'Action Reqd', 'Part Number', 'Parts Avail', 'Comments'], inplace=True)
        return df
    
    def update_style(self, style, df):
        style.background_gradient(cmap=self.cmap.reversed(), subset='% Complete', axis=None)

class FCSummaryReport2(FCSummary):
    def __init__(self, parent):
        super().__init__()
        # must init with parent query object to use it's df
        f.set_self(self, vars())
    
    def get_df(self, default=False):
        df = self.parent.df.copy()
        df.drop(df.columns[1:8], axis=1, inplace=True)
        self.df = df
        return df

    def update_style(self, style, df):
        # color y/n values green/red
        subset = pd.IndexSlice[:, df.columns[1:]]
        style.apply(highlight_yn, subset=subset, axis=None)

        # rotate unit column headers vertical
        unit_col = 2
        s = []
        s.append(dict(
            selector=f'th.col_heading:nth-child(n+{unit_col})',
            props=[ 
                ('font-size', '5px'),
                ('padding', '0px 0px'),
                ('transform', 'rotate(-90deg)'),
                ('text-align', 'center')]))
        s.append(dict(
            selector=f'td:nth-child(n+{unit_col})',
            props=[
                ('font-size', '5px'),
                ('padding', '0px 0px'),
                ('text-align', 'center')]))
        
        style.set_table_styles(s)

class FCDetails(FCBase):
    def __init__(self):
        super().__init__()
        a, b, c, d = self.a, self.b, self.c, self.d

        self.cols = [d.MineSite, d.Model, a.Unit, a.FCNumber, a.Complete, c.ManualClosed, a.Classification, a.Subject, a.DateCompleteSMS, a.DateCompleteKA, b.ExpiryDate, a.SMR, a.Notes]

    def set_default_filter(self):
        super().set_default_filter()
        self.fltr.add(vals=dict(Complete=0))

class NewFCs(FCBase):
    def __init__(self, d_rng, minesite):
        super().__init__()
        a, b, d = self.a, self.b, self.d

        # get a groupby of all fcnumbers where unit.minesite = forthills
        q2 = Query.from_(a) \
            .select(a.FCNumber) \
            .select(fn.Count(a.FCNumber).as_('Count')) \
            .left_join(b).on_field('FCNumber') \
            .left_join(d).on_field('Unit') \
            .where((d.MineSite==minesite) & (b.ReleaseDate.between(*d_rng))) \
            .groupby(a.FCNumber)

        self.cols = [b.FCNumber, b.SubjectShort, b.Subject.as_('Info'), b.Classification, q2.Count, b.ReleaseDate, b.ExpiryDate]

        self.q = Query.from_(b) \
            .inner_join(q2).on_field('FCNumber')
    
class FCComplete(FCBase):
    def __init__(self, d_rng, minesite):
        super().__init__()
        a, d = self.a, self.d
        # get all FCs complete during month, datecompletesms
        # group by FC number, count

        self.cols = [a.FCNumber, a.Subject, fn.Count(a.FCNumber).as_('Count')]
        self.q = self.q \
            .groupby(a.FCNumber, a.Subject)

        self.add_fltr_args([
            dict(vals=dict(DateCompleteSMS=d_rng), term='between'),
            dict(vals=dict(MineSite=minesite), table=d)])

class EmailList(QueryBase):
    def __init__(self):
        super().__init__()
        a = self.select_table
        self.cols = ['*']

        self.q = Query.from_(a) \
            .orderby(a.MineSite, a.Email)
        
    def set_default_filter(self):
        self.fltr.add(vals=dict(MineSite=self.minesite))

class AvailBase(QueryBase):
    def __init__(self, minesite='FortHills', kw=None):
        super().__init__(minesite=minesite, kw=kw)
        a, b = pk.Tables('Downtime', 'UnitID')
        q = Query.from_(a) \
            .inner_join(b).on_field('Unit')
        
        f.set_self(self, vars())

    def set_default_args(self, d_rng):
        self.add_fltr_args([
            dict(vals=dict(ShiftDate=d_rng), term='between')])

class AvailTopDowns(AvailBase):
    def __init__(self, kw=None):
        super().__init__(kw=kw)
        self.formats.update({
            'Total': '{:,.0f}',
            'SMS': '{:,.0f}',
            'Suncor': '{:,.0f}',
            'SMS %': '{:.2%}',
            'Suncor %': '{:.2%}'})
        a, b = self.a, self.b

        total = fn.Sum(a.Duration).as_('Total')
        sum_sms = fn.Sum(a.SMS).as_('Sum_SMS')
        sum_suncor = fn.Sum(a.Suncor).as_('Sum_Suncor')

        cols = [a.CategoryAssigned, total, sum_sms, sum_suncor]

        q = self.q \
            .left_join(b).on_field('Unit') \
            .groupby(a.CategoryAssigned) \
            .orderby(total) \
        
        f.set_self(self, vars())
    
    def process_df(self, df):\
        # sort by total duration, limit 10
        total = df.Total.sum()
        df.sort_values(by='Total', ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
        df = df.iloc[:self.n, :]
        df.columns = ['Category', 'Total', 'SMS', 'Suncor']

        df['SMS %'] = df.SMS / total
        df['Suncor %'] = df.Suncor / total

        return df
    
    def set_default_args(self, d_rng, minesite, n=10):
        self.n = n
        self.add_fltr_args([
            dict(vals=dict(ShiftDate=d_rng), term='between'),
            dict(vals=dict(MineSite=minesite), table=T('UnitID'))])

class AvailSummary(QueryBase):
    def __init__(self, d_rng, model='980%', minesite='FortHills'):
        super().__init__()
        self.view_cols.update(
            Target_MA='MA Target',
            SMS_MA='MA',
            HrsPeriod_MA='Hrs Period MA',
            HrsPeriod_PA='Hrs Period PA')

        self.formats.update({
            'MA Target': '{:.2%}',
            'MA': '{:.2%}',
            'PA': '{:.2%}',
            'Hrs Period MA': '{:,.0f}',
            'Hrs Period PA': '{:,.0f}'})
        
        args = dict(
            d_lower=d_rng[0],
            d_upper=d_rng[1],
            model=model,
            minesite=minesite,
            exclude_ma=1,
            ahs_active=1,
            split_ahs=0)
        
        sql = 'SELECT * FROM {} ORDER BY Unit'.format(table_with_args(table='udfMAReport', args=args))
        f.set_self(self, vars())
    
    def process_df(self, df):
        return self.add_totals(df)
    
    def sum_prod(self, df, col1, col2):
        # create sumproduct for weighted MA and PA %s
        return (df[col1] * df[col2]).sum() / df[col2].sum()

    def add_totals(self, df):
        m = {
            'Model': 'Total',
            'Unit': df.Unit.count(),
            'Total': df.Total.sum(),
            'SMS': df.SMS.sum(),
            'Suncor': df.Suncor.sum(),
            'MA Target': self.sum_prod(df, 'MA Target', 'Hrs Period MA'),
            'MA': self.sum_prod(df, 'MA', 'Hrs Period MA'),
            'PA': self.sum_prod(df, 'PA', 'Hrs Period PA'),
            'Hrs Period MA': df['Hrs Period MA'].sum(),
            'Hrs Period PA': df['Hrs Period PA'].sum()}
        
        return df.append(m, ignore_index=True)
    
    def update_style(self, style, df):
        # cmap = sns.diverging_palette(240, 10, sep=10, n=21, as_cmap=True)
        # cmap = ListedColormap(sns.color_palette('Reds', n_colors=21))
        # self.background_gradients.extend([
        #     dict(cmap=cmap, subset=['Total', 'SMS', 'Suncor'])])

        cmap = LinearSegmentedColormap.from_list('red_white', ['white', '#F8696B'])
        
        u = df.index.get_level_values(0)
        subset = pd.IndexSlice[u[:-1], ['Total', 'SMS', 'Suncor']]
        style.background_gradient(cmap=cmap, subset=subset, axis=None)

        style.apply(highlight_greater, subset=['MA Target', 'MA', 'Unit'], axis=None)

        bg = f.config['color']['thead']
        style.apply(lambda x: [f'background: {bg};color: white' if not x.index[i] in ('Unit', 'MA') else 'background: inherit' for i, v in enumerate(x)], subset=df.index[-1], axis=1)
        
class AvailRolling(QueryBase):
    def __init__(self, d_rng, model='980%', minesite='FortHills'):
        super().__init__()

        self.view_cols.update(
            Target_MA='MA Target',
            SMS_MA='MA')

        self.formats.update({
            'MA Target': '{:.2%}',
            'MA': '{:.2%}'})

        args = dict(
            model=model,
            minesite=minesite,
            d_upper=d_rng[1],
            period_type='month',
            ahs_active=1,
            split_ahs=0)

        sql = 'SELECT * FROM {}'.format(table_with_args(table='udfMASummaryTable', args=args))
        f.set_self(self, vars())
    
    def process_df(self, df):
        df['Month'] = df.DateLower.dt.strftime('%Y-%m')
        df = df[['Month', 'SumSMS', 'MA Target', 'MA']]
        return df
    
    def update_style(self, style, df):
        style.apply(highlight_greater, subset=['MA Target', 'MA'], axis=None)

class Availability(AvailBase):
    def __init__(self, minesite='FortHills', kw=None):
        super().__init__(minesite=minesite, kw=kw)
        a = self.a
        date_col = 'ShiftDate'

        assigned = Case().when(a.CategoryAssigned.isnull(), 0).else_(1).as_('Assigned')
        cols = [a.Unit, a.ShiftDate, a.StartDate, a.EndDate, a.Duration, a.SMS, a.Suncor, a.CategoryAssigned, a.DownReason, a.Comment, assigned]

        q = self.q \
            .orderby(a.Unit, a.StartDate)

        f.set_self(self, vars())

    def set_minesite(self):
        self.fltr.add(vals=dict(MineSite=self.minesite), table=T('UnitID'))
    
    def set_default_filter(self):
        self.set_minesite()
        self.set_lastweek()

    def set_allopen(self):
        self.fltr.add(field='CategoryAssigned', term='isnull')
    
    def process_df(self, df):
        p = f.datafolder / 'csv'
        df_assigned = pd.read_csv(p / 'avail_assigned.csv')
        df_resp = pd.read_csv(p / 'avail_resp.csv')

        # merge category assigned to give a 'pre-assignment' to any null Category Assigned vals
        df.loc[df.CategoryAssigned.isnull(), 'CategoryAssigned'] = df.merge(df_assigned, how='left', on='DownReason')['CategoryAssigned_y']

        # match CategoryAssigned to SMS or suncor and fill duration
        df = df.merge(df_resp, on='CategoryAssigned', how='left')
        where = np.where
        df.SMS = where(df.SMS.isnull(), where(df.Resp=='SMS', df.Duration, 0), df.SMS)
        df.Suncor = where(df.Suncor.isnull(), where(df.Resp=='Suncor', df.Duration, 0), df.Suncor)
        df.drop(columns='Resp', inplace=True)

        return df

class AvailShortfalls(AvailBase):
    def __init__(self, parent, minesite='FortHills', kw=None):
        super().__init__(minesite=minesite, kw=kw)
        # NOTE needs to have availsummary parent
        self.formats.update({
            'MA Target': '{:.2%}',
            'MA': '{:.2%}',
            'SMS': '{:,.0f}'})

        a = self.a

        cols = [a.Unit, a.SMS, a.CategoryAssigned, a.Comment]

        # could also select longest comment?
        q = self.q \
            .orderby(a.Unit, a.StartDate)
        
        f.set_self(self, vars())

    def update_style(self, style, df):
        cmap = LinearSegmentedColormap.from_list('red_white', ['white', '#F8696B'])
        style.background_gradient(cmap=cmap, subset='SMS', axis=None)
        style.background_gradient(cmap=cmap.reversed(), subset='MA', axis=None)
    
    def process_df(self, df):
        # parent query needs to have df loaded already (TODO could change ge_df to store df)
        df2 = df.groupby(['Unit', 'CategoryAssigned']) \
            .agg(dict(SMS='sum', Comment='first')) \
            .reset_index() \
            .query('SMS >= 12')
        
        df2['Combined'] = df2.CategoryAssigned \
            + ' (' + df2.SMS.round(0).map(str) + ') - ' \
            + df2.Comment
        df2 = df2.groupby('Unit')['Combined'] \
            .apply(os.linesep.join) \
            .reset_index() \
            .rename(columns=dict(Combined='Major Causes'))
        
        # get ma summary and merge combined comment df
        df = self.parent.df.copy()
        df = df[df.MA < df['MA Target']]

        df = df[df.Model != 'Total']
        df = df[['Unit', 'SMS', 'MA Target', 'MA']]

        df = df.merge(right=df2, on='Unit', how='left')

        return df
    
def table_with_args(table, args):
    def fmt(arg):
        if isinstance(arg, int):
            return str(arg)
        else:
            return f"'{arg}'"

    str_args = ', '.join(fmt(arg) for arg in args.values())
    return f'{table}({str_args})'

def format_cell(bg, t):
    return f'background: {bg};color: {t};'

def highlight_greater(df):
    # Highlight cells good or bad where MA > MA Target
    m = f.config['color']
    bg, t = m['bg'], m['text']

    m = df['MA'] > df['MA Target']

    df1 = pd.DataFrame(data='background: inherit', index=df.index, columns=df.columns)
    df1['MA'] = np.where(m, format_cell(bg['good'], t['good']), format_cell(bg['bad'], t['bad']))
    if 'Unit' in df.columns:
        df1['Unit'] = df1['MA']
    return df1

def highlight_yn(df):
    m = f.config['color']
    bg, t = m['bg'], m['text']

    m1, m2 = df=='Y', df=='N' # create two boolean masks

    where = pd.np.where
    data = where(m1, format_cell(bg['good'], t['good']), where(m2, format_cell(bg['bad'], t['bad']), 'background: inherit'))

    return pd.DataFrame(data=data, index=df.index, columns=df.columns)
