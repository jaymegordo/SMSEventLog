from .__init__ import *

log = getlog(__name__)

class UnitSMR(QueryBase):
    """Return all SMR values for single unit"""
    def __init__(self, unit, d_rng=None, **kw):
        super().__init__(**kw)
        a = T('UnitSMR')

        if d_rng is None:
            d_upper = dt.now()
            d_lower = d_upper + delta(days=-60)
            d_rng = (d_lower, d_upper)
        
        cols = ['Unit', 'DateSMR', 'SMR']

        q = Query.from_(a) \
            .where(a.Unit==unit) \
            .where(a.DateSMR.between(d_rng[0], d_rng[1]))

        f.set_self(vars())
    
    def process_df(self, df):
        """Add index of all dates in d_rng"""
        return pd.period_range(*self.d_rng, freq='d') \
            .to_timestamp() \
            .to_frame(name='DateSMR') \
            .reset_index(drop=True) \
            .assign(Unit=self.unit) \
            .merge(right=df[['DateSMR', 'SMR']], on='DateSMR', how='left') \
            [['Unit', 'DateSMR', 'SMR']]     

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
            .set_index('Period') \
            .pipe(self.expand_monthly_index) \
            .assign(SMR_worked=lambda x: x.SMR.diff()) \
            .fillna(dict(SMR_worked=0, Unit=self.unit))
    
    def df_monthly(self, max_period=None, n_periods=0, totals=False, **kw):
        df = self.df
        if max_period is None:
            max_period = df.index.max()

        return df \
            .pipe(lambda df: df[df.index <= max_period]) \
            .iloc[n_periods * -1:, :] \
            .pipe(self.append_totals, do=totals) \
            .rename(columns=dict(SMR_worked='SMR Operated'))
    
    def append_totals(self, df, do=True):
        if not do:
            return df

        max_year = df.index.max().to_timestamp().year
        data = dict(
            Period=['Total YTD', 'Total'],
            SMR_worked=[df[df.index >= str(max_year)].SMR_worked.sum(), df.SMR_worked.sum()])
        df2 = pd.DataFrame(data)

        return df \
            .reset_index(drop=False) \
            .append(df2, ignore_index=True)
    
    def style_f300(self, style):
        return style \
            .pipe(st.highlight_totals_row, n_cols=2)

class UnitSMRReport(QueryBase):
    """Return Unit SMR on first day of current and next month to calc usage in month"""
    def __init__(self, d : dt, minesite='FortHills', **kw):
        super().__init__(**kw)
        a, b = pk.Tables('UnitID', 'UnitSMR')

        d_lower = dt(d.year, d.month, 1)
        dates = (d_lower, d_lower + relativedelta(months=1)) # (2020-12-01, 2021-01-01)

        cols = [a.Unit, b.DateSMR, b.SMR]

        q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('Unit') \
            .where((a.MineSite==minesite) & (b.DateSMR.isin(dates) & (a.ExcludeMA.isnull())))

        f.set_self(vars())
    
    def process_df(self, df):
        """Pivot dates for first of months, then merge unit delivery date/serial from db"""
        df = df \
            .assign(DateSMR=lambda x: x.DateSMR.dt.strftime('%Y-%m-%d')) \
            .pivot(index='Unit', columns='DateSMR', values='SMR') \
            .rename_axis('Unit', axis=1) \
            .assign(Difference=lambda x: x.iloc[:, 1] - x.iloc[:, 0]) \
       
        return db.get_df_unit(minesite=self.minesite) \
            .set_index('Unit') \
            [['Serial', 'DeliveryDate']] \
            .merge(right=df, how='right', on='Unit') \
            .reset_index()            
