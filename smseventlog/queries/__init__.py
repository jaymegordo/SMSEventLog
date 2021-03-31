import inspect
import json

import numpy as np
from matplotlib.colors import (DivergingNorm, LinearSegmentedColormap,
                               ListedColormap, TwoSlopeNorm, to_hex)
from seaborn import diverging_palette

from .. import errors as er
from .. import functions as f
from .. import styles as st
from ..__init__ import *
from ..database import db
from ..errors import errlog
from ..utils import dbmodel as dbm


log = getlog(__name__)
week_letter = 'W'
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
        """Add query filter

        Parameters
        ----------
        field : str, optional
            field to filter on, default None
        val : str, optional
            val to filter on, default None
        vals : dict, optional
            dict of {field: val}, default None
        opr : operator, optional
            eg opr.eq, default None
        term : str, optional
            filter term eg "between", default None
        table : str | pk.Table, optional
            table if not using query's default table, default None
        ct : pk.Criterion, optional
            fully formed criterion, eg multiple statements or "or" etc, default None

        Returns
        -------
        qr.Filter
            self
        """        
        if not vals is None:
            # not pretty, but pass in field/val with dict a bit easier
            field = list(vals.keys())[0]
            val = list(vals.values())[0]
        
        if table is None:
            table = self.select_table
        elif isinstance(table, str):
            table = T(table)
            
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

class QueryBase():
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

    def add_extra_cols(self, cols : list):
        """Add extra columns to query

        Parameters
        ----------
        cols : list | string
            Item(s) to add
        """        
        if not isinstance(cols, list): cols = [cols]
        self.cols = self.cols + cols

    def add_fltr_args(self, args, subquery=False):
        """Add multiple filters to self.fltr as list

        Parameters
        ----------
        args : list
            list of key:vals with opional other args
        subquery : bool, optional
            use self.fltr2, default False
        """        
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

    def _process_df(self, df, do=True):
        """Wrapper to allow skipping process_df for testing/troubleshooting"""
        if do:
            return df.pipe(self.process_df)
        else:
            return df
    
    @property
    def df(self):
        if not self.df_loaded:
            self.get_df()
        return self._df

    @df.setter
    def df(self, data):
        self._df = data

    def _get_df(self, default=False, base=False, prnt=False, skip_process=False, **kw) -> pd.DataFrame:
        """Execute query and return dataframe
        
        Parameters
        ----------
        default : bool, optional
            self.set_default_filter if default=True, default False
        base : bool, optional
            self.set_base_filter, default False
        prnt : bool, optional
            Print query sql, default False
        skip_process : bool, optional
            Allow skipping process_df for troubleshooting, default False

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
            .pipe(f.default_df) \
            .pipe(f.convert_df_view_cols, m=self.view_cols) \
            .pipe(f.set_default_dtypes, m=self.default_dtypes) \
            .pipe(self._process_df, do=not skip_process)

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
        self.fltr.add(vals=dict(MineSite=self.minesite), table='UnitID')

    def expand_monthly_index(self, df, d_rng=None):
        """Expand monthly PeriodIndex to include missing months"""
        s = df.index
        if d_rng is None:
            # expand to min and max existing dates
            try:
                d_rng = (s.min().to_timestamp(), s.max().to_timestamp() + relativedelta(months=1))
            except:
                log.info('No rows in monthly index to expand.')
                return df

        idx = pd.date_range(d_rng[0], d_rng[1], freq='M').to_period()

        return df \
            .merge(pd.DataFrame(index=idx), how='right', left_index=True, right_index=True) \
            .rename_axis(s.name)

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

def df_period(freq, n=0, ytd=False):
    """Return df of periods for specified freq

    Parameters
    ----------
    freq : str
        M or W
    n : int, optional
        filter last n periods, default 0
    ytd : bool, optional
        filter periods to start of year, default False

    Returns
    -------
    pd.DataFrame
        df of periods
    """
    freq = dict(month='M', week='W').get(freq, freq) # convert from month/week
    d_upper = dt.now()
    d_lower = d_upper + delta(days=-365)
    idx = pd.date_range(d_lower, d_upper, freq=freq).to_period()

    # fmt_week = f'%Y-%{week_letter}'
    fmt_week = '%G-%V'
    m = dict(
        W=dict(fmt_str=fmt_week),
        M=dict(fmt_str='%Y-%m')) \
        .get(freq)
    
    def _rename_week(df, do=False):
        if not do: return df
        return df \
            .assign(name=lambda x: x.period.dt.strftime(f'Week %{week_letter}'))
    
    def _filter_ytd(df, do=ytd):
        if not do: return df
        return df[df.period >= str(df.period.max().year)]

    df = pd.DataFrame(index=idx)

    return df \
        .assign(
            start_date=lambda x: pd.to_datetime(x.index.start_time.date),
            end_date=lambda x: pd.to_datetime(x.index.end_time.date),
            d_rng=lambda x: list(zip(x.start_date.dt.date, x.end_date.dt.date)),
            name=lambda x: x.index.to_timestamp(freq).strftime(m['fmt_str'])) \
        .rename_axis('period') \
        .reset_index(drop=False) \
        .set_index('name', drop=False) \
        .pipe(_filter_ytd, do=ytd) \
        .pipe(_rename_week, do=freq=='W') \
        .rename(columns=dict(name='name_title')) \
        .iloc[-1 * n:]

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

def df_rolling_n_months(n : int=12):
    """Create df of n rolling months with periodindex

    Parameters
    ----------
    n : int, optional
        n months, default 12
    """    
    d_upper = last_day_month(dt.now() + relativedelta(months=-1))
    d_lower = d_upper + relativedelta(months=(n - 1) * -1)
    idx = pd.date_range(d_lower, d_upper, freq='M').to_period()
    return pd.DataFrame(data=dict(period=idx.astype(str)), index=idx) \
        .assign(
            d_lower=lambda x: x.index.to_timestamp(),
            d_upper=lambda x: x.d_lower + pd.tseries.offsets.MonthEnd(1))

f.import_submodule_classes(
    name=__name__,
    filename=__file__,
    gbls=globals(),
    parent_class='smseventlog.queries')