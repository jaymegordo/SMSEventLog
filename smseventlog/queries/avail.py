from .__init__ import *
from .smr import UnitSMRMonthly

log = getlog(__name__)


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
    """Query for calculating availability tables and summary stats for reports"""
    def __init__(self, d_rng=None, period_name=None, model='980%', minesite='FortHills', period='month', unit=None):
        super().__init__()
        self.view_cols.update(
            ma_target='MA Target',
            hrs_period_ma='Hrs Period MA',
            hrs_period_pa='Hrs Period PA')
        
        self.default_dtypes.update(
            **f.dtypes_dict('float', ['ExcludeHours_MA', 'ExcludeHours_PA']))

        self.formats.update({
            'MA Target': '{:.2%}',
            'MA': '{:.2%}',
            'PA': '{:.2%}',
            'Hrs Period MA': '{:,.0f}',
            'Hrs Period PA': '{:,.0f}',
            'Target Hrs Variance': '{:,.0f}',
            'F300 SMR Operated': '{:,.0f}',
            'Variance F300': '{:,.0f}'})

        # if not period_name is None:
        #     m = dict(month=df_months, week=df_weeks)
        #     d_rng = tuple(m[period]().loc[period_name][['StartDate', 'EndDate']])

        if period == 'week':
            # fmt = f'%Y-%{week_letter}-%w'
            fmt = f'%G-%V-%w'
            freq = 'W'
            # fmt_str = f'Week %{week_letter}'
            fmt_str = f'Week %V'
        else:
            fmt = '%Y-%m'
            freq = 'M'
            fmt_str = fmt
        
        f.set_self(vars())

    @classmethod
    def from_name(cls, name, period='month', **kw):
        """Return query for correct range week/month based on single date"""
        row = df_period(freq=period).loc[name]

        offset = dict(
            month=dict(months=-11),
            week=dict(weeks=-11)) \
            .get(period)

        return cls(
            d_rng=(
                row['start_date'] + relativedelta(**offset),
                row['end_date']),
            period=period, **kw)
    
    @property
    def q(self):
        d_rng, period, model, minesite, unit = self.d_rng, self.period, self.model, self.minesite, self.unit
        a, b = pk.Tables('Downtime', 'UnitID')

        hrs_in_period = cf('tblHrsInPeriod', ['d_lower', 'd_upper', 'minesite', 'period'])
        period_range = cf('period_range', ['startdate', 'enddate', 'period'])
        _month = cf('MONTH', ['date'])
        _year = cf('YEAR', ['date'])
        iso_year = cf('dbo.iso_year', ['date'])
        datepart = cf('DATEPART', ['period_type', 'date'])

        month = _month(a.ShiftDate)
        week = datepart(PseudoColumn('iso_week'), a.ShiftDate)

        if period == 'month':
            year = _year(a.ShiftDate)
            _period = fn.Concat(year, '-', month) #.as_('period')
        else:
            year = iso_year(a.ShiftDate) # only use iso_year (slow custom function) when grouping by week
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

        # in case need historical data for single unit
        if not unit is None:
            q_dt = q_dt.where(a.Unit==unit)
            q_base = q_base.where(b.Unit==unit)

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
                period=lambda x: pd.to_datetime(x.period, format=self.fmt).dt.to_period(self.freq),
                d_upper=lambda x: pd.to_datetime(x.period.dt.end_time.dt.date),
                _age=lambda x: x.d_upper.dt.to_period('M').astype(int) - x.DeliveryDate.dt.to_period('M').astype(int),
                age=lambda x: np.where(x.DeliveryDate.dt.day <= 15, x._age + 1, x._age),
                hrs_period=lambda x: ((
                    np.minimum(
                        x.period.dt.end_time,
                        np.datetime64(self.d_rng[1])) - 
                    np.maximum(
                        x.DeliveryDate,
                        x.period.dt.start_time)
                    ).dt.days + 1) * 24,
                hrs_period_ma=lambda x: np.maximum(x.hrs_period - x.ExcludeHours_MA, 0),
                hrs_period_pa=lambda x: np.maximum(x.hrs_period - x.ExcludeHours_PA, 0),
                MA=lambda x: (x.hrs_period_ma - x.SMS) / x.hrs_period_ma,
                PA=lambda x: (x.hrs_period_pa - x.Total) / x.hrs_period_pa) \
            .drop(columns=['_age']) \
            .replace([np.inf, -np.inf], np.nan) \
            .fillna(dict(MA=1, PA=1)) \
            .pipe(lambda df: df[df.hrs_period >= 0]) \
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

    def df_summary(self, group_ahs: bool=False, period: str=None, max_period: bool=True):
        """Group by period and summarise
        - NOTE need to make sure fulll history is loaded to 12 periods back
        - Always exclude F300 from summary calcs

        Parameters
        ----------
        group_ahs : bool
            group by 'operation' eg ahs/staffed
        period : str
            last or ytd
        max_period : bool
            filter only last period or not, default True

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
            
            if max_period:
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
            .format(self.formats) \
            .format({k: '{:,.0f}' for k in ('Total', 'SMS', 'Suncor')})

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
        widths = {'Target Hrs Variance': 60, 'F300 SMR Operated': 60}
        def _style_week(style, do=False):
            if not do: return style
            return style.format(lambda x: x.strftime(self.fmt_str), subset='Period')

        return style \
            .apply(
                func=st.highlight_greater,
                subset=['MA', 'Target Hrs Variance'],
                axis=None,
                ma_target=style.data['MA Target']) \
            .pipe(st.set_column_widths, vals=widths) \
            .pipe(st.highlight_totals_row, n_cols=2, do=self.period=='month') \
            .pipe(_style_week, do=self.period=='week') \
            .format(dict(SMS='{:,.0f}'))

    def df_history_rolling(self, prd_str=False, totals=False, merge_f300=False, **kw):
        """df of 12 period (week/month) rolling summary.

        Parameters
        ----------
        prd_str : bool\n
            convert Period to string (for display and charts), easier but don't always want
        - period col converted back to str
        """
        cols = ['period', 'SMS', 'ma_target', 'MA', 'target_hrs_var', 'PA']
        return self.df_summary(group_ahs=False) \
            .assign(period=lambda x: x.period.dt.strftime(self.fmt_str) if prd_str else x.period) \
            [cols] \
            .pipe(self.merge_f300, do=merge_f300, **kw) \
            .pipe(self.append_totals_history, do=totals) \
            .pipe(self.rename_cols)
    
    def append_totals_history(self, df, do=False):
        """Append YTD Total + Total to 12-period rolling avail history table"""
        if not do: return df

        max_year = df.period.max().to_timestamp().year

        def _max(col_name):
            """Calc for Total & Total YTD"""    
            return [
                df[df.period >= str(max_year)][col_name].sum(),
                df[col_name].sum()]

        data = dict(
            period=['Total YTD', 'Total'],
            SMS=_max('SMS'),
            target_hrs_var=_max('target_hrs_var'))
        
        # may or may not have SMR Operated column
        if 'F300 SMR Operated' in df.columns:
            data.update({
                'F300 SMR Operated': _max('F300 SMR Operated')})

        df2 = pd.DataFrame(data)

        return df \
            .append(df2, ignore_index=True)
    
    def merge_f300(self, df, query_f300=None, do=False, **kw):
        """Merge F300 SMR operated to avail history table"""
        if not do: return df
        if query_f300 is None:
            query_f300 = UnitSMRMonthly(unit='F300')

        df_smr = query_f300.df_monthly() \
            [['SMR Operated']]

        return df.merge(df_smr, how='left', left_on='period', right_on='Period') \
            .rename(columns={
                'SMR Operated': 'F300 SMR Operated',
                'target_var_f300': 'Variance F300'})
            # .assign(target_var_f300=lambda x: x.target_hrs_var + x['SMR Operated']) \
   
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
        subset = ['Total', 'SMS', 'Suncor']

        # HACK need smaller font size for report. add_table_attrs doesn't work for multiple 'style' values, need to overwrite completely. 
        # TODO Could make table attrs a dict and parse before final render
        if not outlook:
            style.set_table_attributes('style="border-collapse: collapse; font-size: 10px;"')

        return style \
            .background_gradient(cmap=cmap, subset=subset, axis=None) \
            .pipe(self.highlight_greater)

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
    """Query for availability table in eventlog"""
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
        self.fltr.add(vals=dict(MineSite=self.minesite), table='UnitID')
    
    def set_default_filter(self, **kw):
        self.set_minesite()
        self.set_lastweek()

    def set_allopen(self, **kw):
        self.set_default_filter()
 
    def process_df(self, df):
        where = np.where
        p = f.resources / 'csv'
        df_assigned = pd.read_csv(p / 'avail_assigned.csv')
        df_resp = pd.read_csv(p / 'avail_resp.csv')

        # merge category assigned to give a 'pre-assignment' to any null Category Assigned vals
        new_rows = df['Category Assigned'].isnull()

        df.loc[new_rows, 'Category Assigned'] = df.merge(df_assigned, how='left', on='DownReason')['Category Assigned_y']

        # filter unassigned rows
        # extract service hrs eg 1000, 4000 from comment
        # % 2000 to get 0, 1000, 500, 250 etc
        expr = r'(\d{3,})'
        serv = df.loc[(
                new_rows &
                df.DownReason.str.contains('service', flags=re.IGNORECASE))] \
            .Comment.str.extract(expr).astype(int) % 2000

        # assign s5, s4, or s1 service to new rows loc
        df.loc[serv.index, 'Category Assigned'] = \
            where(serv == 0, 'S5 Service',
                where(serv == 1000, 'S4 Service', 'S1 Service'))

        # match CategoryAssigned to SMS or suncor and fill duration
        df = df.merge(df_resp, on='Category Assigned', how='left')
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
