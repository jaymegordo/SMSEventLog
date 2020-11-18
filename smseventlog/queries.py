import inspect
import json

import numpy as np
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from seaborn import diverging_palette

from . import errors as er
from . import functions as f
from . import styles as st
from .__init__ import *
from .database import db
from .errors import errlog
from .utils import dbmodel as dbm

log = getlog(__name__)

"""
- Queries control how data is queried/filtered from database.
- Can be consumed by tables/views, reports, etc
- da is 'default args' to be passed to filter when query is executed
"""

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
    def __init__(self, parent=None, minesite=None, da=None, theme='light', select_tablename=None):
        formats, default_dtypes, stylemap_cols = {}, {}, {}
        background_gradients = []
        last_sql = None
        _minesite_default = 'FortHills'
        # color_good = 240 if theme == 'light' else 120
        cmap = diverging_palette(240, 10, sep=10, n=21, as_cmap=True)
        sql = None
        df = pd.DataFrame()
        df_loaded = False
        use_cached_df = False

        m = f.config['TableName']
        color = f.config['color']
        name = self.__class__.__name__

        # loop base classes to get first working title, need this to map view_cols
        for base_class in inspect.getmro(self.__class__):
            title = m['Class'].get(base_class.__name__, None)
            if not title is None: break

        # loop through base classes till we find a working select_table
        if select_tablename is None:
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
            from .gui import _global as gbl
            return gbl.get_minesite()
    
    @minesite.setter
    def minesite(self, val):
        self._minesite = val

    def get_sql(self, last_query=False, **kw) -> str:
        """Return sql from query object.\n
        Parameters
        ----------
        last_query : bool, optional
            Refresh using last saved sql query, by default False\n
        Returns
        -------
        str
            SQL string, consumed in database.get_df
        """        
        if last_query:
            if not self.last_sql is None:
                return self.last_sql
            else:
                self.parent.update_statusbar('No previous query saved yet.')
                return

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

            if q.get_sql() == '':
                # no select cols defined yet
                q = q.select(*self.cols)

            sql = str(q.where(self.fltr.expand_criterion()))
            self.last_sql = sql

        return sql
       
    def set_fltr(self):
        self.fltr = Filter(parent=self)
        self.fltr2 = Filter(parent=self)
    
    def set_lastperiod(self, days=7):
        if hasattr(self, 'date_col') and not self.date_col is None:
            vals = {self.date_col: dt.now().date() + delta(days=days * -1)}
            self.fltr.add(vals=vals, opr=op.ge)
            return True
        else:
            return False
    
    def set_lastweek(self):
        return self.set_lastperiod(days=7)
    
    def set_lastmonth(self):
        return self.set_lastperiod(days=31)
    
    def get_updatetable(self):
        tablename = self.select_table if self.update_table is None else self.select_table
        return getattr(dbm, tablename) # db model definition, NOT instance

    def add_fltr_args(self, args, subquery=False):
        if not isinstance(args, list): args = [args]

        fltr = self.fltr if not subquery else self.fltr2
        
        for da in args:
            fltr.add(**da)
    
    def _set_default_filter(self, do=False, **kw):
        """Just used for piping"""
        if do and hasattr(self, 'set_default_filter'):
            self.set_default_filter(**kw)
        
        return self
    
    def _set_base_filter(self, do=False, **kw):
        """Just used for piping"""
        if do and hasattr(self, 'set_base_filter'):
            self.set_base_filter(**kw)
        
        return self

    def process_df(self, df):
        """Placeholder for piping"""
        return df
    
    @property
    def df(self):
        if not self.df_loaded:
            self.get_df()
        return self._df

    @df.setter
    def df(self, data):
        self._df = data

    def _get_df(self, default=False, base=False, prnt=False, **kw) -> pd.DataFrame:
        """Execute query and return dataframe
        
        Parameters
        ----------
        default : bool, optional
            self.set_default_filter if default=True, default False\n
        base : bool, optional
            self.set_base_filter, default False\n
        prnt : bool, optional
            Print query sql, default False\n

        Returns
        ---
        pd.DataFrame
        """
        self._set_default_filter(do=default, **kw) \
            ._set_base_filter(do=base, **kw)

        sql = self.get_sql(**kw)
        if prnt: print(sql)

        return pd \
            .read_sql(sql=sql, con=db.engine) \
            .pipe(f.parse_datecols) \
            .pipe(f.convert_int64) \
            .pipe(f.convert_df_view_cols, m=self.view_cols) \
            .pipe(f.set_default_dtypes, m=self.default_dtypes) \
            .pipe(self.process_df)

    def get_df(self, **kw) -> pd.DataFrame:
        """Wrapper for _get_df

        Returns
        ---
        pd.DataFrame
        """
        if self.use_cached_df and self.df_loaded:
            return self.df

        try:
            self.df = self._get_df(**kw)
            self.df_loaded = True
            self.fltr.print_criterion()
        finally:
            # always reset filter after every refresh call
            self.set_fltr()

        return self.df

    def get_stylemap(self, df, col=None):
        """Convert irow, icol stylemap to indexes
        - Consumed by datamodel set_stylemap()

        Returns
        ------
        tuple\n
            tuple of defaultdicts bg, text colors
        """
        if df.shape[0] <= 0 or not hasattr(self, 'update_style'):
            return None

        if col is None:
            # calc style for full dataframe
            style = df.style.pipe(self.update_style)
        else:
            # calc style for specific cols
            m = self.stylemap_cols[col]
            df = df[m['cols']] # get slice of df
            style = df.style.pipe(m['func'], **m.get('da', {}))

        style._compute()
        return f.convert_stylemap_index_color(style=style)

    def set_minesite(self):
        self.fltr.add(vals=dict(MineSite=self.minesite), table=T('UnitID'))

class EventLogBase(QueryBase):
    def __init__(self, da=None, **kw):
        super().__init__(da=da, **kw)
        a, b, c = self.select_table, T('UnitID'), T('UserSettings')
        date_col = 'DateAdded'

        q = Query.from_(a) \
            .left_join(b).on_field('Unit') \
            .left_join(c).on(a.CreatedBy==c.UserName)

        f.set_self(vars())

        self.default_dtypes.update(
            **f.dtypes_dict('Int64', ['SMR', 'Unit SMR', 'Comp SMR', 'Part SMR', 'Pics']),
            **f.dtypes_dict('bool', ['Comp CO']))
    
    def set_base_filter(self, **kw):
        self.set_minesite()
        self.set_usergroup(**kw)

    def set_default_filter(self, **kw):
        self.set_base_filter(**kw)
        self.set_allopen(**kw)
    
    def set_usergroup(self, usergroup=None, **kw):
        if usergroup is None: return
        self.fltr.add(field='UserGroup', val=usergroup, table=T('UserSettings'))

class EventLog(EventLogBase):
    def __init__(self, **kw):
        super().__init__(**kw)
        a, b = self.a, self.b

        cols = [a.UID, a.PassoverSort, a.StatusEvent, a.Unit, a.Title, a.Description, a.FailureCause, a.DateAdded, a.DateCompleted, a.IssueCategory, a.SubCategory, a.Cause, a.CreatedBy]

        q = self.q \
            .orderby(a.DateAdded, a.Unit)
        
        f.set_self(vars())
    
    def set_allopen(self, **kw):
        a = self.a
        ct = ((a.StatusEvent != 'complete') | (a.PassoverSort.like('x')))
        self.fltr.add(ct=ct)

class WorkOrders(EventLogBase):
    def __init__(self, **kw):
        super().__init__(**kw)
        a, b = self.a, self.b

        cols = [a.UID, a.StatusWO, a.WarrantyYN, a.WorkOrder, a.Seg, a.SuncorWO, a.SuncorPO, b.Model, a.Unit, b.Serial, a.Title, a.PartNumber, a.SMR, a.DateAdded, a.DateCompleted, a.CreatedBy, a.WOComments, a.ComponentCO, a.Pictures]

        q = self.q \
            .orderby(a.DateAdded, a.Unit)

        f.set_self(vars())    
   
    def set_allopen(self, **kw):
        self.fltr.add(field='StatusWO', val='open')

class ComponentCOBase(EventLogBase):
    def __init__(self, da=None, **kw):
        super().__init__(da=da, **kw)
        a, b, c = self.a, self.b, T('ComponentType')

        q = self.q \
            .inner_join(c).on_field('Floc') \
            .orderby(a.Unit, a.DateAdded, c.Modifier, a.GroupCO)

        f.set_self(vars())

    def set_default_filter(self, **kw):
        super().set_default_filter(**kw)
        self.fltr.add(vals=dict(DateAdded=dt.now().date() + delta(days=-30)))
    
    def set_fltr(self):
        super().set_fltr()
        self.fltr.add(vals=dict(ComponentCO='True'))

    def set_allopen(self, **kw):
        self.fltr.add(field='COConfirmed', val='False')

class ComponentCO(ComponentCOBase):
    def __init__(self, **kw):
        super().__init__(**kw)
        a, b, c = self.a, self.b, self.c

        cols = [a.UID, b.MineSite, b.Model, a.Unit, c.Component, c.Modifier, a.GroupCO, a.DateAdded, a.SMR, a.ComponentSMR, a.SNRemoved, a.SNInstalled, a.WarrantyYN, a.CapUSD, a.WorkOrder, a.SuncorWO, a.SuncorPO, a.Reman, a.SunCOReason, a.RemovalReason, a.COConfirmed]

        f.set_self(vars())

    def update_style(self, style, **kw):
        # only using for highlight_alternating units       
        color = 'navyblue' if self.theme == 'light' else 'maroon'

        return style \
            .apply(st.highlight_alternating, subset=['Unit'], theme=self.theme, color=color)

class ComponentSMR(QueryBase):
    def __init__(self, **kw):
        super().__init__(**kw)
        a, b, c = self.select_table, *pk.Tables('ComponentType', 'UnitID')
        cols = [a.MineSite, a.Model, a.Unit, a.Component, a.Modifier, a.BenchSMR, a.CurrentUnitSMR, a.SMRLastCO, a.CurrentComponentSMR, a.PredictedCODate, a.LifeRemaining]

        q = Query.from_(a) \
            .left_join(b).on_field('Floc') \
            .left_join(c).on_field('Unit') \
            .orderby(a.MineSite, a.Unit)

        f.set_self(vars())

        self.default_dtypes.update(
            **f.dtypes_dict('Int64', ['Bench SMR', 'Curr Unit SMR', 'SMR Last CO', 'Curr Comp SMR', 'Life Remaining']))
    
    def set_default_filter(self, **kw):
        self.set_allopen()

    def set_allopen(self, **kw):
        self.set_minesite()
    
    def background_gradient(self, style):
        df = style.data
        subset = pd.IndexSlice[df['Life Remaining'].notnull(), 'Life Remaining']
        return style.background_gradient(
            cmap=self.cmap.reversed(), subset=subset, axis=None, vmin=-1000, vmax=1000)
    
    def update_style(self, style, **kw):
        return style.pipe(self.background_gradient)

class ComponentCOReport(ComponentCOBase):
    def __init__(self, da, major=False, sort_component=False, **kw):
        super().__init__(da=da, **kw)
        use_cached_df = True

        self.view_cols.update(
            BenchSMR='Bench SMR')

        a, b, c = self.a, self.b, self.c
        life_remaining = (a.ComponentSMR - c.BenchSMR).as_('Life Achieved')

        cols = [b.Model, a.Unit, c.Component, c.Modifier, a.DateAdded, a.ComponentSMR, c.BenchSMR, life_remaining, a.SunCOReason]

        if major:
            q = self.q.where(c.Major==1)

        self.formats.update({
            'Bench_Pct_All': '{:.2%}'})

        f.set_self(vars())
    
    def process_df(self, df):
        # df[cols] = df[cols].fillna(pd.NA)
        df.pipe(f.convert_dtypes, cols=['Comp SMR', 'Life Achieved', 'Bench SMR'], col_type='Int64')

        if self.sort_component:
            df = df.sort_values(['Component', 'CO Date'])

        return df

    def set_default_args(self, d_rng, minesite):
        self.add_fltr_args([
            dict(vals=dict(DateAdded=d_rng), term='between'),
            dict(vals=dict(MineSite=minesite), table=self.b)])
    
    def update_style(self, style, **kw):
        df = style.data
        subset = pd.IndexSlice[df['Life Achieved'].notnull(), 'Life Achieved']
        return style.background_gradient(
            cmap=self.cmap.reversed(), subset=subset, axis=None, vmin=-4000, vmax=4000) \
            .pipe(st.add_table_attributes, s='class="pagebreak_table"')

    @property
    def mask_planned(self):
        return self.df['Removal Reason'] == 'High Hour Changeout'

    @property
    def mask_failed(self):
        return self.df['Removal Reason'].isin(['Failure', 'Warranty'])

    def exec_summary(self):
        m = {}
        df = self.df
        s = df['Removal Reason']

        m['Planned/Unplanned'] = {
            'Planned': s[self.mask_planned].count(),
            'Unplanned': s[~self.mask_planned].count(),
            'Total': s.count()}

        m['Failures'] = {
            'Failed': s[self.mask_failed].count(),
            'Convenience/High Hour/Damage/Other': s[~self.mask_failed].count(),
            'Total': s.count()}

        return m
    
    def df_component_quarter(self):
        """Group component CO records by Quarter/Component for charting"""
        df = self.df.copy()
        df['Quarter'] = df['CO Date'].dt.to_period('Q')

        return df.groupby(['Quarter', 'Component']) \
            .size() \
            .reset_index(name='Count')
    
    def df_failures(self):
        """Group failures into failed/not failed, with pct of each group total
        - Used for chart_comp_failure_rates"""
        df = self.df.copy()
        df['Failed'] = self.mask_failed
        df2 = df.groupby(['Component', 'Failed']) \
            .size() \
            .reset_index(name='Count')
        
        # get percent of failed/not failed per component group
        df2['Percent'] = df2.groupby(['Component']).apply(lambda g: g / g.sum())['Count']

        return df2
    
    def df_mean_life(self):
        """Group by component, show mean life total, failed, not failed"""
        df = self.df.copy()
        
        # change 'warranty' to 'failure
        x = 'Removal Reason'
        df[x] = df[x].replace(dict(Warranty='Failure'))
        
        df = df[df[x].isin(['Failure', 'High Hour Changeout'])]

        df2 = df.groupby('Component').agg({'Bench SMR': 'mean', 'Comp SMR': 'mean'})

        df3 = df \
            .groupby(['Component', 'Removal Reason'])['Comp SMR'] \
            .mean() \
            .reset_index(drop=False) \
            .pivot(index='Component', columns='Removal Reason', values='Comp SMR')

        return df2.merge(right=df3, how='left', on='Component') \
            .rename(columns={
                'Comp SMR': 'Mean_All',
                'Failure': 'Mean_Failure',
                'High Hour Changeout': 'Mean_HighHour'}) \
            .astype(float).round(0).astype('Int64') \
            .reset_index(drop=False) \
            .assign(Bench_Pct_All=lambda x: x['Mean_All'] / x['Bench SMR'])
    
    def update_style_mean_life(self, style, **kw):
        df = style.data
        # subset = pd.IndexSlice[df['Life Achieved'].notnull(), 'Life Achieved']
        subset = ['Bench_Pct_All']
        return style.background_gradient(
            cmap=self.cmap.reversed(), subset=subset, axis=None, vmin=0.5, vmax=1.5) \
            .format(self.formats)

class TSI(EventLogBase):
    def __init__(self, **kw):
        super().__init__(**kw)
        a, b = self.a, self.b

        cols = [a.UID, a.StatusTSI, a.DateAdded, a.TSINumber, a.WorkOrder, b.Model, a.Unit, b.Serial, a.Title, a.SMR, a.ComponentSMR, a.TSIPartName, a.PartNumber, a.SNRemoved, a.FailureCause, a.TSIDetails, a.TSIAuthor, a.Pictures]
        
        q = self.q \
            .orderby(a.DateAdded, a.Unit)

        f.set_self(vars())

    def set_allopen(self, **kw):
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

        c, d = pk.Tables('UnitSMR', 'EquipType')

        days = fn.DateDiff(PseudoColumn('day'), a.DeliveryDate, fn.CurTimestamp())
        remaining = Case().when(days<=365, 365 - days).else_(0).as_('Remaining')
        remaining2 = Case().when(days<=365*2, 365*2 - days).else_(0)

        ge_remaining = Case().when(isNumeric(left(a.Model, 1))==1, remaining2).else_(None).as_('GE_Remaining')

        b = c.select(c.Unit, fn.Max(c.SMR).as_('CurrentSMR'), fn.Max(c.DateSMR).as_('DateSMR')).groupby(c.Unit).as_('b')

        cols = [a.MineSite, a.Customer, d.EquipClass, a.Model, a.Serial, a.EngineSerial, a.Unit, b.CurrentSMR, b.DateSMR, a.DeliveryDate, remaining, ge_remaining]

        q = Query.from_(a) \
            .left_join(b).on_field('Unit') \
            .left_join(d).on_field('Model') \
            .orderby(a.MineSite, a.Model, a.Unit)
        
        f.set_self(vars())

    def set_default_filter(self, **kw):
        self.fltr.add(vals=dict(MineSite=self.minesite))

class FCBase(QueryBase):
    def __init__(self, da=None, **kw):
        super().__init__(da=da, **kw)
        a = self.select_table
        b, c, d = pk.Tables('FCSummary', 'FCSummaryMineSite', 'UnitID')

        self.default_dtypes.update(
            **f.dtypes_dict('Int64', ['SMR', 'Pics']))
        
        self.formats.update({
            'SMR': '{:,.0f}',
            'Pics': '{:,.0f}'})

        q = Query.from_(a) \
            .left_join(b).on_field('FCNumber') \
            .left_join(d).on(d.Unit==a.Unit) \
            .left_join(c).on((c.FCNumber==a.FCNumber) & (c.MineSite==d.MineSite))

        f.set_self(vars())

    def set_default_filter(self, **kw):
        self.fltr.add(vals=dict(MineSite=self.minesite), table=T('UnitID'))
        self.set_allopen()
    
    def set_allopen(self, **kw):
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

    def highlight_mandatory(self, style):
        bg_color = 'navyblue' if self.theme == 'light' else 'maroon'
        return style.apply(st.highlight_val, axis=None, subset=['Type', 'FC Number'], val='m', bg_color=bg_color, t_color='white', target_col='Type', other_cols=['FC Number'], theme=self.theme)

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
   
    @errlog('Can\'t pivot fc summary dataframe', err=True)
    def process_df(self, df):
        """Pivot raw df for fc summary table"""
        self.df_orig = df.copy()

        df_shape = df.shape # saving to var for err troubleshooting
        if len(df) == 0: return df
        # create summary (calc complete %s)
        df2 = pd.DataFrame()
        gb = df.groupby('FC Number')

        df2['Total'] = gb['Complete'].count()
        df2['Complete'] = gb.apply(lambda x: x[x['Complete']=='Y']['Complete'].count())
        df2['Total Complete'] = df2.Complete.astype(str) + ' / ' +  df2.Total.astype(str)
        df2['% Complete'] = df2.Complete / df2.Total
        df2 = df2.drop(columns=['Total', 'Complete']) \
            .rename_axis('FC Number') \
            .reset_index()

        # can't pivot properly if Hours column (int) is NULL > just set to 0
        df.loc[df.Hrs.isnull(), 'Hrs'] = 0
        
        # If ALL values in column are null (Eg ReleaseDate) need to fill with dummy var to pivot
        for col in ['Release Date', 'Expiry Date']:
            if df[col].isnull().all():
                df[col] = dt(1900,1,1).date()

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

        return df      

    def update_style(self, style, **kw):
        # have to split style funcs into pt 1/2 for report vs gui
        return style \
            .pipe(self.update_style_part_1) \
            .pipe(self.update_style_part_2)
    
    def update_style_part_1(self, style):
        return style \
            .background_gradient(cmap=self.cmap.reversed(), subset='% Complete', axis=None) \
            .pipe(self.highlight_mandatory) \
            .apply(st.highlight_expiry_dates, subset=['Expiry Date'], theme=self.theme)

    def update_style_part_2(self, style):
        # color y/n values green/red
        unit_col = 1 if self.name == 'FCSummaryReport2' else 13
        # color_good = 'good' if self.theme == 'light' else 'goodgreen'
        color_good = 'good'
        
        df = style.data
        subset = pd.IndexSlice[:, df.columns[unit_col:]]

        return style.apply(st.highlight_yn, subset=subset, axis=None, color_good=color_good, theme=self.theme)

class FCSummaryReport(FCSummary):
    def __init__(self, da=None, **kw):
        super().__init__(da=da, **kw)
    
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
        """Must init with parent query object to use it's df"""
        super().__init__()
        f.set_self(vars())
    
    def get_df(self, default=False):
        df = self.parent.df.copy()
        df.drop(df.columns[1:8].drop('Type'), axis=1, inplace=True) # drop other cols except Type
        self.df = df
        return df

    def update_style(self, style, **kw):
        # rotate unit column headers vertical
        # set font size here based on number of columns, min 5 max 10
        size = 280 // len(style.data.columns)
        size = min(max(size, 5), 10)
        font_size = f'{size}px'

        unit_col = 2
        s = []
        s.append(dict(
            selector=f'th.col_heading:nth-child(n+{unit_col})',
            props=[ 
                ('font-size', font_size),
                ('padding', '0px 0px'),
                ('transform', 'rotate(-90deg)'),
                ('text-align', 'center')]))
        s.append(dict(
            selector=f'td:nth-child(n+{unit_col})',
            props=[
                ('font-size', font_size),
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

        self.cols = [a.UID, d.MineSite, d.Model, a.Unit, a.FCNumber, a.Complete, c.ManualClosed, a.Classification, a.Subject, a.DateCompleteSMS, a.DateCompleteKA, b.ExpiryDate, a.SMR, a.Pictures, a.Notes]

    def set_default_filter(self, **kw):
        super().set_default_filter(**kw)
        self.fltr.add(vals=dict(Complete=0))

    def update_style(self, style, **kw):
        return style.apply(st.highlight_expiry_dates, subset=['Expiry Date'], theme=self.theme)

class FCOpen(FCBase):
    """Query for db"""
    def __init__(self, theme='dark'):
        super().__init__(theme=theme)
        a, b = pk.Tables('viewFactoryCampaign', 'UnitID')

        cols = [a.FCNumber, a.Unit, b.MineSite, a.Subject, a.Complete, a.Classification, a.ReleaseDate, a.ExpiryDate]
        q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('Unit') \
            .where(
                (a.Complete==0) &
                ((a.Classification=='M') | (a.ExpiryDate >= dt.now().date())))
        
        f.set_self(vars())
    
    def process_df(self, df):
        return df \
            .assign(Title=lambda x: x.FCNumber.str.cat(x.Subject, sep=' - ')) \
            .rename(columns=dict(
                FCNumber='FC Number',
                Classification='Type'))
    
    def df_open_fc_unit(self, df=None, unit=None):
        """Filter df to open FCs per unit
        - Allow passing in df so don't need to query (if comes from cached db df)"""

        if df is None:
            df = self.df
        
        cols = ['FC Number', 'Type', 'Subject', 'ReleaseDate', 'ExpiryDate']

        return df \
            .pipe(lambda df: df[df.Unit==unit]) \
            [cols] \
            .assign(
                Age=lambda x: (dt.now() - x.ReleaseDate).dt.days,
                Remaining=lambda x: (x.ExpiryDate - dt.now()).dt.days) \
            .pipe(
                f.sort_df_by_list,
                lst=['M', 'FAF', 'DO', 'FT'],
                lst_col='Type',
                sort_cols='FC Number') \
            .reset_index(drop=True)
    
    def update_style(self, style):
        """Style df for table dialog"""
        return style \
            .pipe(self.highlight_mandatory) \
            .apply(st.highlight_expiry_dates, subset=['ExpiryDate'], theme=self.theme)

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
        super().__init__(minesite=minesite)
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
        print(sql)
        f.set_self(vars())
    
    def process_df(self, df):
        df['Month'] = df.Date.dt.strftime('%Y-%m')
        return df

class EmailList(QueryBase):
    def __init__(self, **kw):
        """Full table for app display/editing, NOT single list for emailing"""
        super().__init__(**kw)
        a = self.select_table
        cols = [a.UserGroup, a.MineSite, a.Email, a.Passover, a.WORequest, a.FCCancelled, a.PicsDLS, a.PRP, a.FCSummary, a.TSI, a.RAMP, a.Service, a.Parts]

        q = Query.from_(a) \
            .orderby(a.UserGroup, a.MineSite, a.Email)
        
        f.set_self(vars())

    def set_default_filter(self, usergroup=None, **kw):
        self.fltr.add(vals=dict(MineSite=f'{self.minesite}*')) # TODO remove 'like' eventually
        
        if usergroup is None: usergroup = 'SMS'
        self.fltr.add(field='UserGroup', val=usergroup)
    
    def process_df(self, df):
        # TODO remove this replace, temp till _cwc can be removed
        if not 'MineSite' in df.columns:
            return df # EmailListShort doesnt use this col

        df.MineSite = df.MineSite.replace(dict(_CWC='', _AHS=''), regex=True)
        return df

class EmailListShort(EmailList):
    def __init__(self, col_name: str, minesite: str, usergroup: str=None, **kw):
        """Just the list we actually want to email

        Parameters
        ---
        name : str,
            column name to filter for 'x'\n
        minesite : str\n
        usergroup : str, default None\n

        Examples
        ---
        >>> email_list = EmailListShort(col_name='Passover', minesite='FortHills', usergroup='SMS').emails
        >>> ['johnny@smsequip.com', 'timmy@cummins.com']
        """
        super().__init__(**kw)
        a = self.a
        cols = [a.Email]

        q = Query.from_(a)

        f.set_self(vars())
    
    def set_default_filter(self, **kw):
        # Convert view headers to db headers before query
        col_name = f.convert_header(title=self.title, header=self.col_name)
        self.fltr.add(vals={col_name: 'x'})
        
        super().set_default_filter(usergroup=self.usergroup, **kw)
    
    @property
    def emails(self) -> list:
        """Return the actual list of emails"""
        self.set_default_filter() # calling manually instead of passing default=True to be more explicit here
        df = self.get_df(prnt=True)
        try:
            return list(df.Email)
        except:
            log.warning('Couldn\'t get email list from database.')
            return []

class AvailBase(QueryBase):
    def __init__(self, da=None, **kw):
        super().__init__(da=da, **kw)
        a, b = pk.Tables('Downtime', 'UnitID')
        q = Query.from_(a) \
            .inner_join(b).on_field('Unit')

        self.default_dtypes.update(
            **f.dtypes_dict('float64', ['Total', 'SMS', 'Suncor']))
        
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
    def __init__(self, d_rng=None, period_name=None, model='980%', minesite='FortHills', period='month'):
        super().__init__()
        self.view_cols.update(
            ma_target='MA Target',
            hrs_period_ma='Hrs Period MA',
            hrs_period_pa='Hrs Period PA')

        self.formats.update({
            'MA Target': '{:.2%}',
            'MA': '{:.2%}',
            'PA': '{:.2%}',
            'Hrs Period MA': '{:,.0f}',
            'Hrs Period PA': '{:,.0f}',
            'Target Hrs Variance': '{:,.0f}'})

        if not period_name is None:
            m = dict(month=df_months, week=df_weeks)
            d_rng = tuple(m[period]().loc[period_name][['StartDate', 'EndDate']])

        if period == 'week':
            fmt = '%Y-%U-%w'
            fmt_period = 'W'
            fmt_str = 'Week %U'
        else:
            fmt = '%Y-%m'
            fmt_period = 'M'
            fmt_str = fmt
        
        f.set_self(vars())
    
    @property
    def q(self):
        d_rng, period, model, minesite = self.d_rng, self.period, self.model, self.minesite
        a, b = pk.Tables('Downtime', 'UnitID')

        hrs_in_period = cf('tblHrsInPeriod', ['d_lower', 'd_upper', 'minesite', 'period'])
        period_range = cf('period_range', ['startdate', 'enddate', 'period'])
        _year = cf('YEAR', ['date'])
        _month = cf('MONTH', ['date'])
        datepart = cf('DATEPART', ['period_type', 'date'])

        year = _year(a.ShiftDate)
        month = _month(a.ShiftDate)
        week = datepart(PseudoColumn('iso_week'), a.ShiftDate)

        if period == 'month':
            _period = fn.Concat(year, '-', month) #.as_('period')
        else:
            _period = fn.Concat(year, '-', week) #.as_('period')

        # Create all week/month periods in range crossed with units
        q_prd = Query.from_(period_range(d_rng[0], d_rng[1], period)).select('period')
        q_base = Query.from_(b) \
            .select(q_prd.period, b.Unit) \
            .cross_join(q_prd).cross() \
            .where(Criterion.all([
                b.MineSite==minesite,
                b.model.like(model)]))

        # Unit, Total, SMS, Suncor
        cols_dt = [
            _period.as_('period'),
            a.Unit,
            fn.Sum(a.Duration).as_('Total'),
            fn.Sum(a.SMS).as_('SMS'),
            fn.Sum(a.Suncor).as_('Suncor')]

        q_dt = Query.from_(a) \
            .select(*cols_dt) \
            .where(Criterion.all([
                a.ShiftDate.between(d_rng[0], d_rng[1]),
                a.Duration > 0.01])) \
            .groupby(a.Unit, _period)

        cols1 = [
            q_base.period,
            q_base.Unit,
            q_dt.Total,
            q_dt.SMS,
            q_dt.Suncor]

        q1 = Query.from_(q_base) \
            .select(*cols1) \
            .left_join(q_dt).on_field('Unit', 'Period')

        q_hrs = Query.from_(hrs_in_period(d_rng[0], d_rng[1], minesite, period)).select('*')

        cols = [
            b.Model,
            b.DeliveryDate,
            q1.star,
            q_hrs.ExcludeHours_MA,
            q_hrs.ExcludeHours_PA,
            Case().when(b.AHSActive==1, 'AHS').else_('Staffed').as_('Operation')]

        return Query.from_(q1) \
            .select(*cols) \
            .left_join(b).on_field('Unit') \
            .left_join(q_hrs).on_field('Unit', 'Period') \
            .where(b.Model.like(model))

    def process_df(self, df):
        """Calc data from week/monthly grouped data from db"""
        # read ma_guarante data
        p = f.resources / 'csv/ma_guarantee.csv'
        df_ma_gt = pd.read_csv(p)

        if self.period == 'week':
            df.period = df.period + '-0'

        numeric_cols = df.select_dtypes('number').columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        
        # age: add 1 month age to units delivered in first half of the month (<= 15 days)

        return df \
            .assign(
                period=lambda x: pd.to_datetime(x.period, format=self.fmt).dt.to_period(self.fmt_period),
                d_upper=lambda x: pd.to_datetime(x.period.dt.end_time.dt.date),
                _age=lambda x: x.d_upper.dt.to_period('M').astype(int) - x.DeliveryDate.dt.to_period('M').astype(int),
                age=lambda x: np.where(x.DeliveryDate.dt.day <= 15, x._age + 1, x._age),
                hrs_period=lambda x: ((np.minimum(x.period.dt.end_time, np.datetime64(self.d_rng[1])) - x.period.dt.start_time).dt.days + 1) * 24,
                hrs_period_ma=lambda x: np.maximum(x.hrs_period - x.ExcludeHours_MA, 0),
                hrs_period_pa=lambda x: np.maximum(x.hrs_period - x.ExcludeHours_PA, 0),
                MA=lambda x: (x.hrs_period_ma - x.SMS) / x.hrs_period_ma,
                PA=lambda x: (x.hrs_period_pa - x.Total) / x.hrs_period_pa) \
            .drop(columns=['_age']) \
            .replace([np.inf, -np.inf], np.nan) \
            .fillna(dict(MA=1, PA=1)) \
            .sort_values(['age']) \
            .pipe(lambda df: pd.merge_asof(
                left=df, right=df_ma_gt, on='age', direction='forward', allow_exact_matches=True))
    
    def filter_max_period(self, df):
        return df[df.period == max(df.period)]
    
    def df_report(self, period='last'):
        """Return report-only cols, for highest period in raw data"""
        cols = ['Model', 'Unit', 'Total', 'SMS', 'Suncor', 'ma_target', 'MA', 'hrs_period_ma', 'PA', 'hrs_period_pa', 'Operation']

        df = self.df.copy()

        # filter to ytd, group by unit, weighted avg
        if period == 'ytd':
            df = df \
                .assign(
                    period=lambda x: x.period.dt.year) \
                .pipe(self.filter_max_period) \
                .groupby(['Model', 'Unit', 'Operation'], as_index=False) \
                .agg(**self.agg_cols(df=df))

        elif period == 'last':
            df = df.pipe(self.filter_max_period)

        return df[cols] \
            .sort_values(['Unit']) \
            .reset_index(drop=True) \
            .pipe(self.rename_cols)

    def rename_cols(self, df):
        return df.rename(columns=dict(
            period='Period',
            ma_target='MA Target',
            hrs_period_ma='Hrs Period MA',
            hrs_period_pa='Hrs Period PA',
            target_hrs_var='Target Hrs Variance'))

    def w_avg(self, s, df, wcol):
        """Calc weighted avg for column weighted by another, eg MA by hrs_period_ma"""
        return np.average(s, weights=df.loc[s.index, wcol])
    
    def agg_cols(self, df):
        """Column agg funcs for summary and ytd report"""
        w_avg = self.w_avg

        return dict(
            Total=('Total', 'sum'),
            SMS=('SMS', 'sum'),
            Suncor=('Suncor', 'sum'),
            ma_target=('ma_target', partial(w_avg, df=df, wcol='hrs_period_ma')),
            MA=('MA', partial(w_avg, df=df, wcol='hrs_period_ma')),
            PA=('PA', partial(w_avg, df=df, wcol='hrs_period_pa')),
            hrs_period_ma=('hrs_period_ma', 'sum'),
            hrs_period_pa=('hrs_period_pa', 'sum'))

    def df_summary(self, group_ahs=False, period=None):
        """Group by period and summarise
        - NOTE need to make sure fulll history is loaded to 12 periods back

        Parameters
        ----------
        group_ahs : bool\n
            group by 'operation' eg ahs/staffed
        max_period : bool\n
            filter data to max period only first

        Returns
        -------
        pd.DataFrame
            Grouped df
        """        
        df = self.df.copy()
        group_cols = ['period']

        if period in ('last', 'ytd'):
            if period == 'ytd':
                df.period = df.period.dt.year
            
            df = self.filter_max_period(df=df)

        if group_ahs:
            group_cols.append('Operation')

        return df \
            .pipe(lambda df: df[df.Unit != 'F300']) \
            .groupby(group_cols, as_index=False) \
            .agg(
                Unit=('Unit', 'count'),
                **self.agg_cols(df=df)) \
            .assign(
                target_hrs_var=lambda x: (x.MA - x.ma_target) * x.hrs_period_ma)

    def style_totals(self, style):
        return style \
            .pipe(st.highlight_totals_row, exclude_cols=('Unit', 'MA')) \
            .pipe(self.highlight_greater) \
            .format(self.formats)

    def df_totals(self):
        """Return df of totals for most recent period, split by AHS/Staffed"""
        return pd.concat([
                self.df_summary(group_ahs=True, period='last'),
                self.df_summary(group_ahs=False, period='last')]) \
            .fillna(dict(Operation='Total')) \
            .drop(columns=['period']) \
            .reset_index(drop=True) \
            .pipe(self.rename_cols)

    def style_history(self, style, **kw):
        return style \
            .apply(st.highlight_greater, subset=['MA', 'Target Hrs Variance'], axis=None, ma_target=style.data['MA Target']) \
            .pipe(st.set_column_widths, vals={'Target Hrs Variance': 60})

    def df_history_rolling(self, prd_str=True):
        """df of 12 period (week/month) rolling summary.

        Parameters
        ----------
        prd_str : bool\n
            convert Period to string (for display and charts), easier but don't always want
        - period col converted back to str"""
        cols = ['period', 'SMS', 'ma_target', 'MA', 'target_hrs_var', 'PA']
        return self.df_summary(group_ahs=False) \
            .assign(period=lambda x: x.period.dt.strftime(self.fmt_str) if prd_str else x.period) \
            [cols] \
            .pipe(self.rename_cols)
   
    def exec_summary(self, period='last'):
        d_rng = self.d_rng

        df = self.df_summary(period=period)
        totals = df.loc[0].to_dict()

        if period == 'last':
            current_period = totals['period'].strftime(self.fmt_str)
        elif period == 'ytd':
            current_period = 'YTD'

        m = {}
        m[current_period] = {
                'Physical Availability': '{:.2%}'.format(totals['PA']),
                'Mechanical Availability': '{:.2%}'.format(totals['MA']),
                'Target MA': '{:.2%}'.format(totals['ma_target']),
                'Target Hrs Variance': '{:,.0f}'.format(totals['target_hrs_var'])}
        
        return m

    def sum_prod(self, df, col1, col2):
        """Create sumproduct for weighted MA and PA %s
        - NOTE not used, just keeping for reference"""
        return (df[col1] * df[col2]).sum() / df[col2].sum()
    
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

    def _set_fltr(self):
        return
        # self.fltr.add(vals=dict(Duration=0.01), opr=op.gt) # filter out everything less than 0.01
        # ^ can't use this need to see AHS duplicates which were set to 0

    def background_gradient(self, style, theme=None, do=True):
        if not do: return style
        if theme is None: theme = self.theme # Usually dark, but could be light for email
        bg_color = 'white' if theme == 'light' else self.color['bg']['bgdark']
        cmap = LinearSegmentedColormap.from_list('red_white', [bg_color, self.color['bg']['lightred']])
        return style.background_gradient(cmap=cmap, subset=['Total', 'SMS', 'Suncor'], axis=None)
    
    def highlight_category_assigned(self, style):
        if self.theme == 'dark': return style

        m = {
            'S1 Service': 'lightyellow',
            'S4 Service': 'lightblue',
            'S5 Service': 'lightgreen',
            'Collecting Info': 'lightyellow'}

        return style.apply(
            st.highlight_multiple_vals,
            subset=['Category Assigned'],
            m=m,
            convert=True,
            theme=self.theme)

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
            .pipe(self.highlight_category_assigned) \
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
    
    def set_default_filter(self, **kw):
        self.set_minesite()
        self.set_lastweek()

    def set_allopen(self, **kw):
        self.set_default_filter()
 
    def process_df(self, df):
        p = f.resources / 'csv'
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
        df = self.parent.df_report(period='last').copy()
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
        a.SuncorWO, a.IssueCategory, a.SubCategory, a.Cause]

        q = self.q \
            .orderby(a.Unit, a.DateAdded)
        
        f.set_self(vars())
        self.set_minesite()
        
    def set_default_args(self, d_lower):
        a = self.a
        self.add_fltr_args([
            dict(vals=dict(DateAdded=d_lower)),
            dict(ct=(a.Title.like('crack')) | ((a.IssueCategory == 'frame') & (a.Cause == 'crack'))),
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
    def __init__(self, da=None, minesite='FortHills', **kw):
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
        from .data import oilsamples as oil

        return super().process_df(df=df) \
            .pipe(oil.flatten_test_results, keep_cols=['visc40', 'visc100']) \
            .drop(columns=['oilChanged', 'testResults', 'results', 'recommendations', 'comments'])

class UserSettings(QueryBase):
    def __init__(self, parent=None, **kw):
        super().__init__(parent=parent, **kw)
        a = self.select_table
        cols = [a.UserName, a.Email, a.LastLogin, a.Ver, a.Domain, a.UserGroup, a.MineSite]
        q = Query.from_(a) \
            .orderby(a.LastLogin, order=Order.desc)

        f.set_self(vars())

class PLMUnit(QueryBase):
    def __init__(self, unit, d_upper, d_lower=None, **kw):
        """Select PLM report data for single unit.

        Parameters
        ----------
        unit : str\n
        d_upper : dt\n
        d_lower : dt
            If None, default to d_upper - 6 months
        """   
        super().__init__(select_tablename='viewPLM')
        # use_cached_df = True # hmmm dont actually need this
        a = self.select_table
        cols = [a.star]

        if d_lower is None:
            # always start at first day of month
            d_lower = first_last_month(d_upper + delta(days=-180))[0]
        
        d_rng = (d_lower, d_upper + delta(days=1)) # between cuts off at T00:00:00

        q = Query.from_(a) \
            .orderby(a.datetime)

        f.set_self(vars())
        self.set_default_args() # NOTE not sure if need this or if report always does it

    def set_default_args(self, **kw):
        self.add_fltr_args([
            dict(vals=dict(unit=self.unit)),
            dict(vals=dict(datetime=self.d_rng), term='between')])
    
    @property
    def df_calc(self):
        """Calculate columns before aggregating"""
        df = self.df.copy()

        def where(cond):
            """Quicker way to assign val for summing"""
            return np.where(cond, 1, 0)

        return df.assign(
                TotalLoads=1,
                Total_110=lambda x: where(
                    (x.GrossPayload_pct > 1.1) &
                    (x.GrossPayload_pct <= 1.2) &
                    (x.ExcludeFlags == 0)),
                Total_120=lambda x: where(
                    (x.GrossPayload_pct > 1.2) &
                    (x.ExcludeFlags == 0))) \
            .assign(
                Dumped_1KM_110=lambda x: where(
                    (x.Total_110 == 1) &
                    (x.L_HaulDistance <= 1)),
                Lower_110_Shovel=lambda x: where(
                    (x.Total_110 == 1) &
                    (x.L_HaulDistance > 1) &
                    (x.QuickShovelEst_pct <= 1.1)),
                Dumped_1KM_120=lambda x: where(
                    (x.Total_120 == 1) &
                    (x.L_HaulDistance < 1)),
                No_GE_Code=lambda x: where(
                    (x.Total_120 == 1) &
                    (x.L_HaulDistance > 1) &
                    (x.QuickShovelEst_pct <= 1.1) &
                    (x.QuickPayload_pct <= 1.2)))

    def add_totals(self, df):
        """Pipe assigning totals so can be done monthly or with final summary"""
        return df.assign(
                Total_ExcludeFlags=lambda x: x.TotalLoads - x.ExcludeFlags,
                Accepted_110=lambda x: x.Total_110 - x.Dumped_1KM_110 - x.Lower_110_Shovel,
                Accepted_120=lambda x: x.Total_120 - x.Dumped_1KM_120 - x.No_GE_Code) \
            .assign(
                Accepted_100=lambda x: x.Total_ExcludeFlags - x.Accepted_120 - x.Accepted_110,
                Overload_pct_110=lambda x: x.Accepted_110 / x.Total_ExcludeFlags,
                Overload_pct_120=lambda x: x.Accepted_120 / x.Total_ExcludeFlags)
    
    @er.errlog('Failed to get df_monthly', warn=True)
    def df_monthly(self, add_unit_smr=False):
        """Bin data into months for charting, will include missing data = good"""

        # set DateIndex range to lower and upper of data (wouldn't show if data was missing)
        d_rng = self.d_rng
        idx = pd.date_range(d_rng[0], last_day_month(d_rng[1]), freq='M').to_period()

        df = self.df_calc \
            .groupby(pd.Grouper(key='DateTime', freq='M')) \
            .sum() \
            .pipe(self.add_totals) \
            .pipe(lambda df: df.set_index(df.index.to_period())) \
            .merge(pd.DataFrame(index=idx), how='right', left_index=True, right_index=True)

        if add_unit_smr:
            # combine df_smr SMR_worked with plm df
            query_smr = UnitSMRMonthly(unit=self.unit)
            df_smr = query_smr.df_monthly(period_index=True) \
                [['SMR_worked']]

            df = df.merge(df_smr, how='left', left_index=True, right_index=True)

        return df

    @property
    def df_summary(self):
        """Create single summary row from all haulcycle records"""
        # need to grouby first to merge the summed values
        df = self.df_calc
        if df.shape[0] == 0:
            log.warning(f'No results in PLM query dataframe. Unit: {self.unit}')
            return

        gb = df.groupby('Unit')

        return gb \
            .agg(
                MinDate=('DateTime', 'min'),
                MaxDate=('DateTime', 'max')) \
            .merge(right=gb.sum().loc[:, 'ExcludeFlags':], on='Unit', how='left') \
            .pipe(self.add_totals) \
            .reset_index(drop=False)

    @er.errlog('Failed to get df_summary_report', warn=True)
    def df_summary_report(self):
        """Pivot single row of PLM summary into df for report."""
        # if df is None or not 0 in df.index:
        #     raise AttributeError('Can\'t pivot dataframe!')
        m = self.df_summary.iloc[0].to_dict()
        
        cols = ['110 - 120%', '>120%']
        data = {
            'Total loads': (m['Total_110'], m['Total_120']),
            'Dumped within 1km': (m['Dumped_1KM_110'], m['Dumped_1KM_120']),
            '<110% at shovel': (m['Lower_110_Shovel'], ),
            'No GE code': (None, m['No_GE_Code']),
            'Loads accepted': (m['Accepted_110'], m['Accepted_120']),
            '% of loads accepted': (m['Overload_pct_110'], m['Overload_pct_120'])}

        return pd.DataFrame.from_dict(data, orient='index', columns=cols) \
            .reset_index() \
            .rename(columns=dict(index='Load Range'))
   
    def max_date(self):
        a = T('viewPLM')
        q = a.select(fn.Max(a.DateTime)) \
            .where(a.Unit==self.unit)

        return db.max_date_db(q=q)
    
    def highlight_accepted_loads(self, style):
        df = style.data
        subset = pd.IndexSlice[df.index[-1], df.columns[1:]]
        return style.apply(st.highlight_accepted_loads, subset=subset, axis=None)
   
    def format_custom(self, style, subset, type_='int'):       
        """Format first rows of summary table as int, last row as percent"""
        m = dict(int='{:,.0f}', pct='{:,.2%}')
        return style.format(m[type_], subset=subset, na_rep='')
    
    def update_style(self, style, **kw):
        df = style.data
        s = []
        s.append(dict(
            selector=f'th, td',
            props=[
                ('font-size', '12px')]))

        cols = df.columns[1:]

        return style \
            .pipe(self.highlight_accepted_loads) \
            .pipe(st.add_table_style, s=s) \
            .pipe(self.format_custom, subset=pd.IndexSlice[df.index[:-1], cols], type_='int') \
            .pipe(self.format_custom, subset=pd.IndexSlice[df.index[-1], cols], type_='pct')

class UnitSMRMonthly(QueryBase):
    """Return max smr per month per unit, grouped monthly"""
    def __init__(self, unit=None, **kw):
        super().__init__(**kw)
        a, b = pk.Tables('UnitSMR', 'UnitID')

        _year = cf('YEAR', ['date'])
        _month = cf('MONTH', ['date'])
        year = _year(a.DateSMR)
        month = _month(a.DateSMR)
        _period = fn.Concat(year, '-', month)

        cols = [a.Unit, _period.as_('Period'), fn.Max(a.SMR).as_('SMR')]
        q = Query.from_(a) \
            .left_join(b).on_field('Unit') \
            .where(a.Unit==unit) \
            .groupby(a.Unit, _period)

        f.set_self(vars())
    
    def process_df(self, df):
        return df \
            .assign(
                Period=lambda x: pd.to_datetime(x.Period, format='%Y-%m').dt.to_period('M')) \
            .sort_values(['Unit', 'Period']) \
            .assign(SMR_worked=lambda x: x.SMR.diff()) \
            .fillna(0)
    
    def df_monthly(self, period_index=False):
        return self.df.set_index('Period')

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

def last_day_month(d):
    return first_last_month(d)[1]

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
