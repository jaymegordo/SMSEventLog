from .__init__ import *
from .el import EventLogBase

log = getlog(__name__)


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

        cols = [a.UID, b.MineSite, b.Model, a.Unit, c.Component, c.Modifier, a.GroupCO, a.DateAdded, a.SMR, a.ComponentSMR, a.SNRemoved, a.SNInstalled, a.WarrantyYN, a.CapUSD, a.WorkOrder, a.SuncorWO, a.SuncorPO, a.Reman, a.SunCOReason, a.FailureCause, a.COConfirmed]

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
        cols = [a.MineSite, a.Model, a.Unit, a.Component, a.Modifier, a.BenchSMR, a.CurrentUnitSMR, a.SMRLastCO, a.CurrentComponentSMR, a.PredictedCODate, a.LifeRemaining, a.SNInstalled]

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
        self.fltr.add(vals=dict(major=1))
    
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
