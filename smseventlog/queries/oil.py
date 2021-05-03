from .__init__ import *

log = getlog(__name__)


class OilSamples(QueryBase):
    def __init__(self, **kw):
        super().__init__(**kw)

        self.default_dtypes.update(
            **f.dtypes_dict('Int64', ['unit_smr', 'component_smr']))

        a, b = self.select_table, T('UnitId')
        # cols = [a.star]
        cols = [a.unit, a.component_id, a.modifier, a.sample_date, a.unit_smr, a.oil_changed, a.sample_rank, a.test_results, a.test_flags]

        q = Query.from_(a) \
            .left_join(b).on_field('Unit') \
            .orderby(a.unit, a.component_id, a.modifier, a.sample_date)

        f.set_self(vars())

    def set_default_filter(self, **kw):
        self.set_base_filter(**kw)
        self.set_allopen(**kw)
        
    def set_base_filter(self, **kw):
        self.set_minesite()

    def set_allopen(self, **kw):
        a = self.a
        # ct = ((a.StatusEvent != 'complete') | (a.PassoverSort.like('x')))
        # self.fltr.add(ct=ct)
        self.add_fltr_args([
            dict(vals=dict(process_date=dt.now() + delta(days=-3))),
            # dict(vals=dict(component_id=component))
            ])
    
    def process_df(self, df):
        """Expand nested dicts of samples/flags to full columns"""
        expand_dict = lambda df, col, suff: df.join(
            pd.DataFrame(
                df.pop(col) \
                .apply(json.loads).tolist()).add_suffix(suff))

        # save full df with flags for styling
        df = df \
            .pipe(expand_dict, col='test_results', suff='') \
            .pipe(expand_dict, col='test_flags', suff='_fg')

        # set iso/opc cols to Int64
        iso_cols = [col for col in df.columns if 'iso_' in col and not 'count' in col]
        opc_cols = [col for col in df.columns if 'opc_' in col]
        iso_cols.extend(opc_cols)

        self.default_dtypes.update(
            **f.dtypes_dict('Int64', iso_cols))

        # remove spaces between \ for iso and opc cols
        for col in ('opc', 'iso_count'):
            if col in df.columns:
                df[col] = df[col].str.replace(' ', '')

        suffix = '_fg'
        flagged_cols = [col for col in df.columns if suffix in col]
        self.flagged_cols = flagged_cols

        self.df_flags = df.copy()
        return df.drop(columns=flagged_cols)

    def set_default_args(self, unit=None, component=None):
        self.add_fltr_args([
            dict(vals=dict(unit=unit)),
            dict(vals=dict(component_id=component))])
    
    def style_flags(self, style, **kw):
        """Style flags red/orange/yellow and overall sample_rank"""
        if not hasattr(self, 'df_flags'):
            raise AttributeError('df_flags not set!')
        
        # join flagged cols back to set flag colors
        style.data = style.data.join(self.df_flags[self.flagged_cols])
        style.columns = self.df_flags.columns

        c = f.config['color']['bg']
        m_color = dict(
            S=(c['lightred'], 'white'),
            U=(c['lightorange'], 'black'),
            R=(c['lightyellow'], 'black'))

        # need normal and _f cols to highlight flagged cols
        suffix = '_fg'
        # flagged_cols = [col for col in style.data.columns if suffix in col]
        subset = self.flagged_cols.copy()
        subset.extend([col.replace(suffix, '') for col in subset])

        return style \
            .background_gradient(cmap=self.cmap, subset='sample_rank', axis=None, vmin=0, vmax=10.0) \
            .apply(
                st.highlight_flags,
                axis=None,
                subset=subset,
                m=m_color,
                theme=self.theme,
                none_inherit=False,
                convert=False) \
            .hide_columns(self.flagged_cols)
    
    def update_style(self, style, **kw):
        # style = self.df_flags.style
        style.set_table_attributes('class="pagebreak_table"')
        color = 'navyblue' if self.theme == 'light' else 'maroon'

        return style \
            .pipe(self.style_flags) \
            .apply(st.highlight_alternating, subset=['unit'], theme=self.theme, color=color)

class OilSamplesReport(OilSamples):
    """Query for oil sample in failure reports"""
    def __init__(self, unit, component, modifier=None, n=10, d_lower=None, **kw):
        super().__init__(**kw)
        a, b = self.a, self.b
        cols = [a.unit, a.component_id, a.modifier, a.sample_date, a.unit_smr, a.oil_changed, a.sample_rank, a.test_results, a.test_flags]

        q = Query \
            .from_(a) \
            .where(
                (a.unit==unit) &
                (a.component_id==component)) \
            .orderby(a.sample_date, order=Order.desc)
        
        if d_lower is None:
            q = q.top(n)
        else:
            q = q.where(a.sample_date >= d_lower)
        
        if not modifier is None:
            q = q.where(a.modifier==modifier)

        f.set_self(vars())
    
    # def process_df(self, df):
        # """Oil report needs style to have all flagged cols"""
        # super().process_df(df)
        # return self.df_flags

    #     expand_dict = lambda df, col, suff: df.join(
    #         pd.DataFrame(
    #             df.pop(col) \
    #             .apply(json.loads).tolist()).add_suffix(suff))

    #     return df \
    #         .pipe(expand_dict, col='test_results', suff='') \
    #         .pipe(expand_dict, col='test_flags', suff='_fg')
    
    def update_style(self, style, **kw):
        return style \
            .pipe(self.style_flags) \
            .format({k: '{:.1f}' for k in style.data.select_dtypes(float).columns}) \
            .format(dict(sample_date='{:%Y-%m-%d}'))

class OilSamplesRecent(OilSamples):
    def __init__(self, recent_days=-120, da=None):
        super().__init__(da=da)
        a, b = self.a, self.b
        
        # subquery for ordering with row_number
        c = Query.from_(a).select(
            a.star,
            (RowNumber() \
                .over(a.unit, a.component_id, a.modifier) \
                .orderby(a.sample_date, order=Order.desc)).as_('rn')) \
        .left_join(b).on_field('Unit') \
        .where(a.sample_date >= dt.now() + delta(days=recent_days)) \
        .as_('sq0')

        cols = [c.star]       
        sq0 = c
        f.set_self(vars())

    def get_query(self):
        c = self.sq0
        return Query.from_(c) \
            .where(c.rn==1) \
            .orderby(c.unit, c.component_id, c.modifier)

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
