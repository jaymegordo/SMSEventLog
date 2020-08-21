import inspect
import json

import numpy as np
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap, ListedColormap

from . import dbmodel as dbm
from . import functions as f
from . import styles as st
from .__init__ import *

# Queries control how data is queried/filtered from database.
# Can be consumed by tables/views, reports, etc
# da is 'default args' to be passed to filter when query is executed

class Filter():
    def __init__(self, parent):
        # fltr has to belong to a query object
        criterion, fields = {}, {}
        select_table = parent.select_table
        f.set_self(vars())

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
                val = val.replace('*', '%')
                if '%' in val:
                    ct = field_.like(val)
                else:
                    if opr is None: opr = op.eq
                    ct = opr(field_, val)
            elif isinstance(val, (int, float)):
                if opr is None: opr = op.eq
                ct = opr(field_, val)
            elif isinstance(val, (dt, date)):
                if opr is None: opr = op.ge
                ct = opr(field_, val)
        
        self.add_criterion(ct=ct)
        return self
    
    def add_criterion(self, ct):
        # check for duplicate criterion, use str(ct) as dict key for actual ct
        # can also use this to pass in a completed pk criterion eg (T().field() == val)
        self.criterion[str(ct)] = ct
        if isinstance(ct, pk.terms.ComplexCriterion):
            return # cant use fields in complexcriterion for later access but whatever

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
    
    def expand_criterion(self):
        return Criterion.all(self.get_all_criterion())

    def is_init(self):
        return len(self.criterion) > 0

    def print_criterion(self):
        for ct in self.criterion.values():
            print('\t', list(ct.tables_)[0], ct)

class QueryBase(object):
    def __init__(self, parent=None, minesite=None, da=None, theme='light'):
        formats, default_dtypes, stylemap_cols = {}, {}, {}
        background_gradients = []
        _minesite_default = 'FortHills'
        # color_good = 240 if theme == 'light' else 120
        cmap = sns.diverging_palette(240, 10, sep=10, n=21, as_cmap=True)
        sql, df = None, pd.DataFrame()
        m = f.config['TableName']
        color = f.config['color']
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

        # set dict for db > view_col conversion later
        view_cols = f.get_dict_db_view(title=title)

        f.set_self(vars())
        self.set_fltr()

    @property
    def minesite(self):
        # can either pass in a minesite for reports/etc, or use GUI parent's
        if hasattr(self, '_minesite') and not self._minesite is None:
            return self._minesite
        elif not self.parent is None:
            return self.parent.minesite
        else:
            return self._minesite_default
    
    @minesite.setter
    def minesite(self, val):
        self._minesite = val

    def get_sql(self):
        sql, da = self.sql, self.da

        if sql is None:
            q = self.q
            if hasattr(self, 'process_criterion'):
                self.process_criterion()
        
            if not da is None and hasattr(self, 'set_default_args'):
                self.set_default_args(**da)
            
            # NOTE could build functionality for more than one subquery
            fltr2 = self.fltr2
            if fltr2.is_init() and hasattr(self, 'sq0'):
                self.sq0 = self.sq0.where(fltr2.expand_criterion())
            
            if hasattr(self, 'get_query'): # need to do this after init for queries with subqueries
                q = self.get_query()

            sql = q.select(*self.cols) \
                .where(self.fltr.expand_criterion()) \
                .get_sql().replace("'d'", '"d"') # TODO: fix for this was answered

        return sql
       
    def set_fltr(self):
        self.fltr = Filter(parent=self)
        self.fltr2 = Filter(parent=self)
    
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

    def add_fltr_args(self, args, subquery=False):
        if not isinstance(args, list): args = [args]

        fltr = self.fltr if not subquery else self.fltr2
        
        for da in args:
            fltr.add(**da)
    
    def get_df(self, default=False, **kw):
        from .database import db
        self.df = db.get_df(query=self, default=default, **kw)
        return self.df

    def get_stylemap(self, df, col=None):
        # convert irow, icol stylemap to indexes
        if df.shape[0] <= 0 or not hasattr(self, 'update_style'):
            return {}

        if col is None:
            # calc style for full dataframe
            style = df.style.pipe(self.update_style)
        else:
            # calc style for specific cols
            m = self.stylemap_cols[col]
            df = df[m['cols']] # get slice of df
            style = df.style.pipe(m['func'], **m.get('da', {}))

        style._compute()
        return f.convert_stylemap_index(style=style)

class EventLogBase(QueryBase):
    def __init__(self, da=None, **kw):
        super().__init__(da=da, **kw)
        a, b = self.select_table, T('UnitID')
        date_col = 'DateAdded'

        q = Query.from_(a) \
            .left_join(b).on_field('Unit')

        f.set_self(vars())

        self.default_dtypes.update(
            **f.dtypes_dict('Int64', ['SMR', 'Unit SMR', 'Part SMR', 'Pics']),
            **f.dtypes_dict('bool', ['Comp CO']))
    
    def set_minesite(self):
        self.fltr.add(vals=dict(MineSite=self.minesite), table=T('UnitID'))
    
    def set_default_filter(self):
        self.set_minesite()
        self.set_allopen()

class EventLog(EventLogBase):
    def __init__(self, **kw):
        super().__init__(**kw)
        a, b = self.a, self.b

        cols = [a.UID, a.PassoverSort, a.StatusEvent, a.Unit, a.Title, a.Description, a.FailureCause, a.DateAdded, a.DateCompleted, a.IssueCategory, a.SubCategory, a.Cause, a.CreatedBy]

        q = self.q \
            .orderby(a.DateAdded, a.Unit)
        
        f.set_self(vars())
    
    def set_allopen(self):
        self.fltr.add(field='StatusEvent', val='complete', opr=op.ne)

class WorkOrders(EventLogBase):
    def __init__(self, **kw):
        super().__init__(**kw)
        a, b = self.a, self.b

        cols = [a.UID, a.StatusWO, a.WarrantyYN, a.WorkOrder, a.Seg, a.SuncorWO, a.SuncorPO, b.Model, a.Unit, b.Serial, a.Title, a.PartNumber, a.SMR, a.DateAdded, a.DateCompleted, a.CreatedBy, a.WOComments, a.ComponentCO, a.Pictures]

        q = self.q \
            .orderby(a.DateAdded, a.Unit)

        f.set_self(vars())    
   
    def set_allopen(self):
        self.fltr.add(field='StatusWO', val='open')

class ComponentCOBase(EventLogBase):
    def __init__(self, da=None, **kw):
        super().__init__(da=da, **kw)
        a, b, c = self.a, self.b, T('ComponentType')

        q = self.q \
            .inner_join(c).on_field('Floc') \
            .orderby(a.Unit, a.DateAdded, c.Modifier, a.GroupCO)

        f.set_self(vars())

    def set_default_filter(self):
        super().set_default_filter()
        self.fltr.add(vals=dict(DateAdded=dt.now().date() + delta(days=-30)))
    
    def set_fltr(self):
        super().set_fltr()
        self.fltr.add(vals=dict(ComponentCO='True'))

    def set_allopen(self):
        self.fltr.add(field='COConfirmed', val='False')

class ComponentCO(ComponentCOBase):
    def __init__(self, **kw):
        super().__init__(**kw)
        a, b, c = self.a, self.b, self.c

        cols = [a.UID, b.MineSite, b.Model, a.Unit, c.Component, c.Modifier, a.GroupCO, a.DateAdded, a.SMR, a.ComponentSMR, a.SNRemoved, a.SNInstalled, a.WarrantyYN, a.CapUSD, a.WorkOrder, a.SuncorWO, a.SuncorPO, a.Reman, a.SunCOReason, a.RemovalReason, a.COConfirmed]

        f.set_self(vars())

class ComponentCOReport(ComponentCOBase):
    def __init__(self, da, **kw):
        super().__init__(da=da, **kw)

        self.view_cols.update(
            BenchSMR='Bench SMR')

        a, b, c = self.a, self.b, self.c
        life_remaining = (a.ComponentSMR - c.BenchSMR).as_('Life Achieved')

        cols = [b.Model, a.Unit, c.Component, c.Modifier, a.DateAdded, a.ComponentSMR, c.BenchSMR, life_remaining, a.SunCOReason]

        f.set_self(vars())
    
    def process_df(self, df):
        # df[cols] = df[cols].fillna(pd.NA)
        df.pipe(f.convert_dtypes, cols=['Comp SMR', 'Life Achieved', 'Bench SMR'], col_type='Int64')
        return df

    def set_default_args(self, d_rng, minesite):
        self.add_fltr_args([
            dict(vals=dict(DateAdded=d_rng), term='between'),
            dict(vals=dict(MineSite=minesite), table=self.b)])
    
    def update_style(self, style, **kw):
        df = style.data
        subset = pd.IndexSlice[df['Life Achieved'].notnull(), 'Life Achieved']
        return style.background_gradient(cmap=self.cmap.reversed(), subset=subset, axis=None)

    def exec_summary(self):
        m = {}
        df = self.df
        s = df['Removal Reason']
        mask = s == 'High Hour Changeout' # TODO may need to change this criteria

        m['Changeouts'] = {
            'Planned': s[mask].count(),
            'Unplanned': s[~mask].count()
        }
        return m

class TSI(EventLogBase):
    def __init__(self, **kw):
        super().__init__(**kw)
        a, b = self.a, self.b

        cols = [a.UID, a.StatusTSI, a.DateAdded, a.TSINumber, a.WorkOrder, b.Model, a.Unit, b.Serial, a.Title, a.SMR, a.ComponentSMR, a.TSIPartName, a.PartNumber, a.SNRemoved, a.FailureCause, a.TSIDetails, a.TSIAuthor]
        
        q = self.q \
            .orderby(a.DateAdded, a.Unit)

        f.set_self(vars())

    def set_allopen(self):
        self.fltr.add(field='StatusTSI', val='closed', opr=op.ne)
    
    def set_fltr(self):
        super().set_fltr()
        self.fltr.add(field='StatusTSI', term='notnull')

class UnitInfo(QueryBase):
    def __init__(self, **kw):
        super().__init__(**kw)
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
        
        f.set_self(vars())

    def set_default_filter(self):
        self.fltr.add(vals=dict(MineSite=self.minesite))

class FCBase(QueryBase):
    def __init__(self, da=None, **kw):
        super().__init__(da=da, **kw)
        a = self.select_table
        b, c, d = pk.Tables('FCSummary', 'FCSummaryMineSite', 'UnitID')

        q = Query.from_(a) \
            .left_join(b).on_field('FCNumber') \
            .left_join(d).on(d.Unit==a.Unit) \
            .left_join(c).on((c.FCNumber==a.FCNumber) & (c.MineSite==d.MineSite))

        f.set_self(vars())

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

    def sort_by_fctype(self, df):
        return f.sort_df_by_list(df=df, lst=['M', 'FAF', 'DO', 'FT'], lst_col='Type', sort_cols='FC Number')

class FCSummary(FCBase):
    def __init__(self, da=None, **kw):
        super().__init__(da=da, **kw)

        self.formats.update({
            '% Complete': '{:.0%}',
            'Hrs': '{:.0f}'})

        a, b, c, d = self.a, self.b, self.c, self.d

        complete = Case().when(a.Complete==1, 'Y').else_('N').as_('Complete') # just renaming True to Y
        
        cols = [d.MineSite, a.Unit, a.FCNumber, a.Subject, b.Classification, c.Resp, b.Hours, b.PartNumber, c.PartAvailability, c.Comments, b.ReleaseDate, b.ExpiryDate, complete]
        f.set_self(vars())

    def process_df(self, df):
        # pivot raw df for fc summary table
        self.df_orig = df.copy()

        try:
            # create summary (calc complete %s)
            df2 = pd.DataFrame()
            gb = df.groupby('FC Number')

            df2['Total'] = gb['Complete'].count()
            df2['Complete'] = gb.apply(lambda x: x[x['Complete']=='Y']['Complete'].count())
            df2['Total Complete'] = df2.Complete.astype(str) + ' / ' +  df2.Total.astype(str)
            df2['% Complete'] = df2.Complete / df2.Total
            df2.drop(columns=['Total', 'Complete'], inplace=True)

            # can't pivot properly if Hours column (int) is NULL > just set to 0
            df.loc[df.Hrs.isnull(), 'Hrs'] = 0

            index = [c for c in df.columns if not c in ('Unit', 'Complete')] # use all df columns except unit, complete
            df = df.pipe(f.multiIndex_pivot, index=index, columns='Unit', values='Complete') \
                .reset_index() \
                .merge(right=df2, how='left', on='FC Number') # merge summary

            # reorder cols after merge
            cols = list(df)
            endcol = 10
            cols.insert(endcol + 1, cols.pop(cols.index('Total Complete')))
            cols.insert(endcol + 2, cols.pop(cols.index('% Complete')))
            df = df.loc[:, cols]

            df.pipe(self.sort_by_fctype)
            

        except:
            f.send_error(msg='Can\'t pivot fc summary dataframe')

        return df      

    def update_style(self, style, **kw):
        # have to split style funcs into pt 1/2 for report vs gui
        return style \
            .pipe(self.update_style_part_1) \
            .pipe(self.update_style_part_2)

    def highlight_mandatory(self, style):
        bg_color = 'navyblue' if self.theme == 'light' else 'maroon'
        return style.apply(st.highlight_val, axis=None, subset=['Type', 'FC Number'], val='m', bg_color=bg_color, t_color='white', target_col='Type', other_cols=['FC Number'], theme=self.theme)

    def update_style_part_1(self, style):
        return style.background_gradient(cmap=self.cmap.reversed(), subset='% Complete', axis=None) \
            .pipe(self.highlight_mandatory)

    def update_style_part_2(self, style):
        # color y/n values green/red
        unit_col = 1 if self.name == 'FCSummaryReport2' else 13
        # color_good = 'good' if self.theme == 'light' else 'goodgreen'
        color_good = 'good'
        
        df = style.data
        subset = pd.IndexSlice[:, df.columns[unit_col:]]

        return style.apply(st.highlight_yn, subset=subset, axis=None, color_good=color_good, theme=self.theme)

class FCSummaryReport(FCSummary):
    def __init__(self, da=None):
        super().__init__(da=da)
    
    def get_df(self, default=False):
        # from .database import db
        # df = db.get_df(query=self, default=default)
        df = super().get_df(default=default)
        # self.df = df
        return df[df.columns[:8]]

    def process_df(self, df):
        df = super().process_df(df)
        df.drop(columns=['MineSite', 'Action Reqd', 'Part Number', 'Parts Avail', 'Comments'], inplace=True)
        return df
    
    def update_style(self, style, **kw):
        return style.pipe(self.update_style_part_1)

    def exec_summary(self):
        m, m2 = {}, {}
        df = self.df_orig
        df = df[df.Complete=='N']
        s = df.Type
        mandatory_incomplete = df[s == 'M'].Type.count()
        # all_else_incomplete = df[s != 'M'].Type.count()
        hrs_incomplete = df[s == 'M'].Hrs.sum()

        m['Outstanding (Mandatory)'] = {
            'Count': mandatory_incomplete,
            'Labour Hours': '{:,.0f}'.format(hrs_incomplete)
        }
        # m['Completed'] {

        # }
        return m

class FCSummaryReport2(FCSummary):
    def __init__(self, parent):
        super().__init__()
        # must init with parent query object to use it's df
        f.set_self(vars())
    
    def get_df(self, default=False):
        df = self.parent.df.copy()
        df.drop(df.columns[1:8].drop('Type'), axis=1, inplace=True) # drop other cols except Type
        self.df = df
        return df

    def update_style(self, style, **kw):
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

        return style \
            .pipe(self.update_style_part_2) \
            .pipe(self.highlight_mandatory) \
            .hide_columns(['Type']) \
            .pipe(st.add_table_style, s=s)

class FCDetails(FCBase):
    def __init__(self, **kw):
        super().__init__(**kw)
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

        self.cols = [a.FCNumber.as_('FC Number'), a.Classification.as_('Type'), a.Subject, fn.Count(a.FCNumber).as_('Completed')]
        self.q = self.q \
            .groupby(a.FCNumber, a.Subject, a.Classification) \
            .orderby(a.Classification)

        self.add_fltr_args([
            dict(vals=dict(DateCompleteSMS=d_rng), term='between'),
            dict(vals=dict(MineSite=minesite), table=d)])
    
    def process_df(self, df):
        return df.pipe(self.sort_by_fctype)
    
    def exec_summary(self):
        m = {}
        df = self.df
        mask = df.Type == 'M'
        m['Completed'] = {
            'Mandatory': df[mask].Completed.sum(),
            'All others': df[~mask].Completed.sum()
        }
        return m

class FCHistoryRolling(FCBase):
    def __init__(self, d_rng, minesite='FortHills', da=None):
        super().__init__(da=da)

        # need to see history of open labour hrs per month 12 months rolling
        # count of open at time x - count of complete at time x?

        args = dict(
            d_upper=d_rng[1], # need to pass last day of next month
            minesite=minesite)

        sql = 'SELECT * FROM {}'.format(table_with_args(table='FCHistoryRolling', args=args))
        f.set_self(vars())
    
    def process_df(self, df):
        df['Month'] = df.Date.dt.strftime('%Y-%m')
        return df

class EmailList(QueryBase):
    def __init__(self, **kw):
        super().__init__(**kw)
        a = self.select_table
        self.cols = ['*']

        self.q = Query.from_(a) \
            .orderby(a.MineSite, a.Email)
        
        self.set_default_filter()
        
    def set_default_filter(self):
        if not self.minesite is None:
            self.fltr.add(vals=dict(MineSite=self.minesite))

class AvailBase(QueryBase):
    def __init__(self, da=None, **kw):
        super().__init__(da=da, **kw)
        a, b = pk.Tables('Downtime', 'UnitID')
        q = Query.from_(a) \
            .inner_join(b).on_field('Unit')
        
        f.set_self(vars())

    def set_default_args(self, d_rng):
        self.add_fltr_args([
            dict(vals=dict(ShiftDate=d_rng), term='between')])

class AvailTopDowns(AvailBase):
    def __init__(self, da=None):
        super().__init__(da=da)
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
            .groupby(a.CategoryAssigned) \
            .orderby(total) \
        
        f.set_self(vars())
    
    def process_df(self, df):\
        # sort by total duration, limit 10
        total = df.Total.sum()
        df.sort_values(by='Total', ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
        df = df.iloc[:self.n, :].copy()
        df.columns = ['Category', 'Total', 'SMS', 'Suncor']

        df['SMS %'] = df.SMS / total
        df['Suncor %'] = df.Suncor / total

        return df
    
    def set_default_args(self, d_rng, minesite, n=10):
        self.n = n
        self.add_fltr_args([
            dict(vals=dict(ShiftDate=d_rng), term='between'),
            dict(vals=dict(MineSite=minesite), table=self.b)])

    def exec_summary(self):
        m, m2 = {}, {}
        df = self.df.sort_values(by='SMS', ascending=False).reset_index()

        for i in range(3):
            m2[df.loc[i, 'Category']] = '{:,.0f} hrs, {:.1%}'.format(df.loc[i, 'SMS'], df.loc[i, 'SMS %'])

        m['Top 3 downtime categories'] = m2

        return m

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
            exclude_ma=False,
            ahs_active=True,
            split_ahs=False)
        
        sql = 'SELECT * FROM {} ORDER BY Unit'.format(table_with_args(table='udfMAReport', args=args))
        f.set_self(vars())
    
    def process_df(self, df):
        return self.add_totals(df)
    
    def exec_summary(self):
        totals, d_rng = self.totals, self.d_rng
        days = (d_rng[1] - d_rng[0]).days

        if days > 31:
            current_period = 'YTD'
        elif days > 7:
            current_period = d_rng[0].strftime('%B %Y')
        else:
            current_period = (d_rng[0] + delta(days=7)).strftime('Week %W')

        m = {}
        target_hrs_variance = (totals['MA'] - totals['MA Target']) * totals['Hrs Period MA']

        m[current_period] = {
                'Physical Availability': '{:.2%}'.format(totals['PA']),
                'Mechanical Availability': '{:.2%}'.format(totals['MA']),
                'Target MA': '{:.2%}'.format(totals['MA Target']),
                'Target Hrs Variance': '{:,.0f}'.format(target_hrs_variance)
            }
        
        return m

    def sum_prod(self, df, col1, col2):
        # create sumproduct for weighted MA and PA %s
        return (df[col1] * df[col2]).sum() / df[col2].sum()

    def get_totals(self, df, totals_name='Total'):
        df = df[df.Unit != 'F300']
        m = {
            'Model': totals_name,
            'Unit': df.Unit.count(),
            'Total': df.Total.sum(),
            'SMS': df.SMS.sum(),
            'Suncor': df.Suncor.sum(),
            'MA Target': self.sum_prod(df, 'MA Target', 'Hrs Period MA'),
            'MA': self.sum_prod(df, 'MA', 'Hrs Period MA'),
            'PA': self.sum_prod(df, 'PA', 'Hrs Period PA'),
            'Hrs Period MA': df['Hrs Period MA'].sum(),
            'Hrs Period PA': df['Hrs Period PA'].sum()}

        return m

    def add_totals(self, df, totals_name='Total'):
        # just used to save totals for exec summary now
        m = self.get_totals(df, totals_name)
        self.totals = m
        
        # return df.append(m, ignore_index=True)
        return df
    
    def highlight_greater(self, style):
        return style.apply(st.highlight_greater, subset=['MA', 'Unit'], axis=None, ma_target=style.data['MA Target'])

    def update_style(self, style, outlook=False, **kw):
        df = style.data
        cmap = LinearSegmentedColormap.from_list('red_white', ['white', '#F8696B'])
        
        # u = df.index.get_level_values(0)
        # subset = pd.IndexSlice[u[:-1], ['Total', 'SMS', 'Suncor']] # u[:-1] to exclude totals row
        subset = ['Total', 'SMS', 'Suncor']

        # TODO need to fix this, parse style= better
        if not outlook:
            style.set_table_attributes('style="border-collapse: collapse; font-size: 10px;"')
        else:
            style.set_table_attributes('style="border-collapse: collapse;"')

        return style \
            .background_gradient(cmap=cmap, subset=subset, axis=None) \
            .pipe(self.highlight_greater) \
            # .pipe(st.add_table_attributes, s='style="font-size: 10px;"', do=not outlook)

    def df_totals(self):
        # calc totals for ahs/staffed/all, return df
        # make sure self.df is not none
        df = self.df
        data = []
        data.extend([self.get_totals(
            df=df[df.Operation==name], totals_name=name) for name in ('Staffed', 'AHS')])

        data.append(self.get_totals(df=df))

        return pd.DataFrame(data).rename(columns=dict(Model='Operation'))
    
    def style_totals(self, style):
        return style \
            .pipe(st.highlight_totals_row, exclude_cols=('Unit', 'MA')) \
            .pipe(self.highlight_greater) \
            .format(self.formats)

class AvailHistory(QueryBase):
    def __init__(self, d_rng, period_type='month', model='980%', minesite='FortHills', num_periods=12):
        super().__init__()

        self.view_cols.update(
            Target_MA='MA Target',
            SMS_MA='MA',
            Target_Hrs_Variance='Target Hrs Variance')

        self.formats.update({
            'MA Target': '{:.2%}',
            'MA': '{:.2%}',
            'PA': '{:.2%}',
            'Target Hrs Variance': '{:,.0f}'})

        args = dict(
            model=model,
            minesite=minesite,
            d_upper=d_rng[1],
            period_type=period_type,
            ahs_active=True,
            split_ahs=False,
            num_periods=num_periods)

        sql = 'SELECT * FROM {}'.format(table_with_args(table='udfMASummaryTable', args=args))
        f.set_self(vars())
    
    def process_df(self, df):
        if self.period_type == 'month':
            days = 0
            fmt = '%Y-%m'
        else:
            days = 7 # need to offset week so it ligns up with suncor's weeks
            fmt = '%Y-Week %W'

        df['Period'] = (df.DateLower + delta(days=days)).dt.strftime(fmt)
        df = df[['Period', 'SumSMS', 'MA Target', 'MA', 'Target Hrs Variance', 'PA']]
        return df
    
    def update_style(self, style, **kw):
        return style \
            .apply(st.highlight_greater, subset=['MA', 'Target Hrs Variance'], axis=None, ma_target=style.data['MA Target']) \
            .pipe(st.set_column_widths, vals={'Target Hrs Variance': 60})

class AvailRawData(AvailBase):
    def __init__(self, da=None, **kw):
        super().__init__(da=da, **kw)
        dt_format = '{:%Y-%m-%d %H:%M}'
        self.formats.update({
            'StartDate': dt_format,
            'EndDate': dt_format})

        a = self.a
        cols = [a.Unit, a.ShiftDate, a.StartDate, a.EndDate, a.Duration.as_('Total'), a.SMS, a.Suncor, a.CategoryAssigned.as_('Category Assigned'), a.DownReason, a.Comment]

        q = self.q \
            .orderby(a.Unit, a.StartDate) \
            .orderby(a.EndDate, order=Order.desc)

        f.set_self(vars())

    def set_fltr(self):
        super().set_fltr()
        # self.fltr.add(vals=dict(Duration=0.01), opr=op.gt) # filter out everything less than 0.01
        # ^ can't use this need to see AHS duplicates which were set to 0

    def background_gradient(self, style, theme=None, do=True):
        if not do: return style
        if theme is None: theme = self.theme # Usually dark, but could be light for email
        bg_color = 'white' if theme == 'light' else self.color['bg']['bgdark']
        cmap = LinearSegmentedColormap.from_list('red_white', [bg_color, self.color['bg']['lightred']])
        return style.background_gradient(cmap=cmap, subset=['Total', 'SMS', 'Suncor'], axis=None)

    def update_style(self, style, **kw):
        # used for reporting + gui (only for colors)
        style.set_table_attributes('class="pagebreak_table" style="font-size: 8px;"')
        
        col_widths = dict(StartDate=60, EndDate=60, Total=20, SMS=20, Suncor=20, Comment=150)
        col_widths.update({'Category Assigned': 80})
        color = 'navyblue' if self.theme == 'light' else 'maroon'

        return style \
            .pipe(self.background_gradient) \
            .apply(st.highlight_alternating, subset=['Unit'], theme=self.theme, color=color) \
            .pipe(st.set_column_widths, vals=col_widths) \
            .hide_columns(['DownReason'])

class Availability(AvailRawData):
    # query for availability table in eventlog
    def __init__(self, da=None, **kw):
        super().__init__(da=da, **kw)
        a = self.a
        date_col = 'ShiftDate'
        ct_allopen = a.CategoryAssigned.isnull() | a.SMS.isnull() | a.Suncor.isnull()
        assigned = Case().when(ct_allopen, 0).else_(1).as_('Assigned')
        self.cols.append(assigned)

        f.set_self(vars())

        # set cols, func, and da for stylemap functions
        cols_gradient = ['Total', 'SMS', 'Suncor']
        self.stylemap_cols.update(
            {col: dict(
                cols=cols_gradient,
                func=self.background_gradient) for col in cols_gradient})
        
        # reapplied to 'Unit' when column filtered with 'filter_assigned'. could also do sorting?
        self.stylemap_cols.update(
            {'Unit': dict(
                cols=['Unit'],
                func=st.pipe_highlight_alternating,
                da=dict(
                    subset=['Unit'],
                    color='maroon',
                    theme=self.theme))})

    def set_minesite(self):
        self.fltr.add(vals=dict(MineSite=self.minesite), table=T('UnitID'))
    
    def set_default_filter(self):
        self.set_minesite()
        self.set_lastweek()

    def set_allopen(self):
        self.set_minesite()
        self.fltr.add(ct=self.ct_allopen)
 
    def process_df(self, df):
        p = f.datafolder / 'csv'
        df_assigned = pd.read_csv(p / 'avail_assigned.csv')
        df_resp = pd.read_csv(p / 'avail_resp.csv')

        # merge category assigned to give a 'pre-assignment' to any null Category Assigned vals
        df.loc[df['Category Assigned'].isnull(), 'Category Assigned'] = df.merge(df_assigned, how='left', on='DownReason')['Category Assigned_y']

        # match CategoryAssigned to SMS or suncor and fill duration
        df = df.merge(df_resp, on='Category Assigned', how='left')
        where = np.where
        df.SMS = where(df.SMS.isnull(), where(df.Resp=='SMS', df.Total, 0), df.SMS)
        df.Suncor = where(df.Suncor.isnull(), where(df.Resp=='Suncor', df.Total, 0), df.Suncor)
        df.drop(columns='Resp', inplace=True)

        return df

class AvailShortfalls(AvailBase):
    def __init__(self, parent, da=None, **kw):
        super().__init__(da=da, **kw)
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
        
        f.set_self(vars())

    def update_style(self, style, **kw):
        cmap = LinearSegmentedColormap.from_list('red_white', ['white', '#F8696B'])
        
        return style \
            .background_gradient(cmap=cmap, subset='SMS', axis=None) \
            .background_gradient(cmap=cmap.reversed(), subset='MA', axis=None)
    
    def process_df(self, df):
        # parent query needs to have df loaded already (TODO could change ge_df to store df)
        df2 = df.groupby(['Unit', 'CategoryAssigned']) \
            .agg(dict(SMS='sum', Comment='first')) \
            .reset_index() \
            .query('SMS >= 12')
        
        df2['Combined'] = df2.CategoryAssigned \
            + ' (' + df2.SMS.round(0).map(str) + ') - ' \
            + df2.Comment \
            .replace(pd.NA, '') # cant apply linesep.join if column has NaN

        s = df2.groupby('Unit')['Combined'] \
            .apply(os.linesep.join) \
            .reset_index() \
            .rename(columns=dict(Combined='Major Causes'))
        
        # get ma summary and merge combined comment df
        df = self.parent.df.copy()
        df = df[df.MA < df['MA Target']]

        df = df[df.Model != 'Total']
        df = df[['Unit', 'SMS', 'MA Target', 'MA']]

        df = df.merge(right=s, on='Unit', how='left')

        return df

class FrameCracks(EventLogBase):
    def __init__(self, da=None, **kw):
        super().__init__(da=da, **kw)
        a, b = self.a, self.b
        cols = [a.Unit, a.DateAdded, a.Title, a.SMR, a.TSIPartName, a.TSIDetails, a.WOComments, a.TSINumber, 
        a.SuncorWO]

        q = self.q \
            .orderby(a.Unit, a.DateAdded)
        
        f.set_self(vars())
        self.set_minesite()
        
    def set_default_args(self, d_lower):
        self.add_fltr_args([
            dict(vals=dict(DateAdded=d_lower)),
            dict(vals=dict(Title='%crack%')),
            dict(vals=dict(Model='%980%'), table=self.b)])
        
    def process_df(self, df):
        df = df.rename(columns=dict(SuncorWO='Order'))
        df.Order = pd.to_numeric(df.Order, errors='coerce').astype('Int64')
        return df

class OilSamples(QueryBase):
    def __init__(self, da=None, **kw):
        super().__init__(da=da, **kw)

        self.default_dtypes.update(
            **f.dtypes_dict('Int64', ['unitSMR', 'componentSMR']))

        a, b = self.select_table, T('UnitId')
        cols = [a.star]

        q = Query.from_(a) \
            .left_join(b).on_field('Unit') \
            .orderby(a.Unit, a.Component, a.Modifier, a.sampleDate)

        f.set_self(vars())
    
    def process_df(self, df):
        df.testResults = df.testResults.apply(json.loads) # deserialize testResults from string > list
        return df.set_index('labTrackingNo')
    
    def update_style(self, style, **kw):
        style.set_table_attributes('class="pagebreak_table"')

        c = f.config['color']['bg']
        m = dict(
            S=(c['lightred'], 'white'),
            U=(c['lightorange'], 'black'),
            R=(c['lightyellow'], 'black'))

        # need normal and _f cols to highlight flagged cols
        flagged_cols = [col for col in style.data.columns if '_f' in col]
        subset = flagged_cols.copy()
        subset.extend([col.replace('_f', '') for col in subset])
        
        return style \
            .background_gradient(cmap=self.cmap, subset='sampleRank', axis=None) \
            .apply(st.highlight_flags, axis=None, subset=subset, m=m) \
            .apply(st.highlight_alternating, subset=['Unit']) \
            .hide_columns(flagged_cols)

class OilSamplesRecent(OilSamples):
    def __init__(self, recent_days=-120, da=None):
        super().__init__(da=da)
        a, b = self.a, self.b
        
        # subquery for ordering with row_number
        c = Query.from_(a).select(
            a.star,
            (RowNumber() \
                .over(a.Unit, a.Component, a.Modifier) \
                .orderby(a.sampleDate, order=Order.desc)).as_('rn')) \
        .left_join(b).on_field('Unit') \
        .where(a.sampleDate >= dt.now() + delta(days=recent_days)) \
        .as_('sq0')

        cols = [c.star]       
        sq0 = c
        f.set_self(vars())

    def get_query(self):
        c = self.sq0
        return Query.from_(c) \
            .where(c.rn==1) \
            .orderby(c.Unit, c.Component, c.Modifier)

    def process_df(self, df):
        return super().process_df(df=df) \
            .drop(columns=['rn'])

class OilReportSpindle(OilSamplesRecent):
    def __init__(self, da=None, minesite='FortHills'):
        super().__init__(da=da, **kw)

    def set_default_filter(self):
        self.set_default_args()

    def set_default_args(self):
        self.add_fltr_args([
                dict(vals=dict(component='spindle'), table=self.a),
                dict(vals=dict(minesite=self.minesite), table=self.b),
                dict(vals=dict(model='980%'), table=self.b)],
                subquery=True)

    def process_df(self, df):
        from . import oilsamples as oil

        return super().process_df(df=df) \
            .pipe(oil.flatten_test_results, keep_cols=['visc40', 'visc100']) \
            .drop(columns=['oilChanged', 'testResults', 'results', 'recommendations', 'comments'])

def table_with_args(table, args):
    def fmt(arg):
        if isinstance(arg, bool):
            return f"'{arg}'"
        elif isinstance(arg, int):
            return str(arg)
        else:
            return f"'{arg}'"

    str_args = ', '.join(fmt(arg) for arg in args.values())
    return f'{table}({str_args})'


# data range funcs
def first_last_month(d):
    d_lower = dt(d.year, d.month, 1)
    d_upper = d_lower + relativedelta(months=1) + delta(days=-1)
    return (d_lower, d_upper)

def df_months():
    # Month
    cols = ['StartDate', 'EndDate', 'Name']
    d_start = dt.now() + delta(days=-365)
    d_start = dt(d_start.year, d_start.month, 1)

    m = {}
    for i in range(24):
        d = d_start + relativedelta(months=i)
        name = '{:%Y-%m}'.format(d)
        m[name] = (*first_last_month(d), name)

    return pd.DataFrame.from_dict(m, columns=cols, orient='index')

def df_weeks():
    # Week
    cols = ['StartDate', 'EndDate', 'Name']

    m = {}
    year = dt.now().year
    for wk in range(1, 53):
        s = f'2020-W{wk-1}'
        d = dt.strptime(s + '-1', "%Y-W%W-%w").date()
        m[f'{year}-{wk}'] = (d, d + delta(days=6), f'Week {wk}')

    return pd.DataFrame.from_dict(m, columns=cols, orient='index')
