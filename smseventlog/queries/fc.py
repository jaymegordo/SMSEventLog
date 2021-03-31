from .__init__ import *

log = getlog(__name__)


class FCBase(QueryBase):
    """Defines base structure/table joins for other FC queries"""
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
        self.fltr.add(vals=dict(MineSite=self.minesite), table='UnitID')
        self.set_allopen()
    
    def set_allopen(self, **kw):
        self.fltr.add(vals=dict(ManualClosed=0), table='FCSummaryMineSite')

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

        # rename Complete True = Y, scheduled = S, else N
        case_scheduled = Case().when(a.Scheduled==1, 'S').else_('N')
        complete = Case().when(a.Complete==1, 'Y').else_(case_scheduled).as_('Complete')
        
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
        
        # If ALL values in column are null (Eg ReleaseDate) need to fill with dummy var to pivot
        for col in ['Release Date', 'Expiry Date']:
            if df[col].isnull().all():
                df[col] = dt(1900,1,1).date()

        index = [c for c in df.columns if not c in ('Unit', 'Complete')] # use all df columns except unit, complete

        df = df \
            .fillna(dict(Hrs=0)) \
            .pipe(f.multiIndex_pivot, index=index, columns='Unit', values='Complete') \
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
    
    def get_df(self, **kw):
        return super().get_df(**kw) \
            .pipe(lambda df: df.loc[:, df.columns[:8]])

    def process_df(self, df):
        df = super().process_df(df)
        df.drop(columns=['MineSite', 'Action Reqd', 'Part Number', 'Parts Avail', 'Comments'], inplace=True)
        return df
    
    def update_style(self, style, **kw):
        return style \
            .pipe(self.update_style_part_1) \
            .pipe(st.set_col_alignment, col_name='Total Complete', alignment='center')

    def exec_summary(self):
        m, m2 = {}, {}
        df = self.df_orig
        df = df[df.Complete.isin(['N', 'S'])]
        s = df.Type

        df_incomplete = df[s == 'M']
        mandatory_incomplete = df_incomplete.Type.count()
        hrs_incomplete = df_incomplete.Hrs.sum()
        # all_else_incomplete = df[s != 'M'].Type.count()

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
    
    def get_df(self, **kw):
        df = self.parent.df.copy()
        df.drop(df.columns[1:8].drop('Type'), axis=1, inplace=True) # drop other cols except Type
        self.df = df
        return df

    def update_style(self, style, **kw):
        """rotate unit column headers vertical
        set font size here based on number of columns, min 5 max 10"""
        df = style.data
        size = 280 // len(df.columns)
        size = min(max(size, 5), 9)
        font_size = f'{size}px'

        unit_col = 2
        nth_child = f'nth-child(n+{unit_col})'
        s = []
        s.append(dict(
            selector=f'th.col_heading:{nth_child}',
            props=[ 
                ('font-size', font_size),
                ('transform', 'rotate(-90deg)'),
                ('padding', '0px 0px'),
                ('text-align', 'center')]))
        
        # SUPER-HACK to make vertical headers resize header row height properly
        s.append(dict(
            selector=f'th.col_heading:{nth_child}:before',
            props=[ 
                ('content', "''"),
                ('padding-top', '110%'),
                ('display', 'inline-block'),
                ('vertical-align', 'middle')]))
        s.append(dict(
            selector=f'td:{nth_child}',
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

        self.cols = [a.UID, d.MineSite, d.Model, a.Unit, a.FCNumber, a.Complete, a.Scheduled, c.ManualClosed, a.Ignore, a.Classification, a.Subject, a.DateCompleteSMS, a.DateCompleteKA, b.ExpiryDate, a.SMR, a.Pictures, a.Notes]

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
            .left_join(b).on_field('Unit')
        
        f.set_self(vars())

    def __set_default_filter(self, **kw):
        # NOTE not used, filtering in db.df_fc currently
        # super().set_default_filter(**kw)
        a = self.a
        ct = ((a.Classification=='M') | (a.ExpiryDate >= dt.now().date()))
        self.fltr.add(ct=ct)
        self.fltr.add(vals=dict(Complete=0))
    
    def process_df(self, df):
        return df \
            .assign(
                Title=lambda x: x.FCNumber.str.cat(x.Subject, sep=' - '),
                # Complete=lambda x: np.where(x.Complete=='True', True, False)
                ) \
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
        a, b, d = self.a, self.b, self.d
        # get all FCs complete during month, datecompletesms
        # group by FC number, count
        
        self.formats.update({
            'Hours': '{:,.1f}',
            'Total Hours': '{:,.1f}'})

        self.cols = [
            a.FCNumber.as_('FC Number'),
            a.Classification.as_('Type'),
            a.Subject,
            fn.Count(a.FCNumber).as_('Completed'),
            b.hours.as_('Hours')]
        self.q = self.q \
            .groupby(a.FCNumber, a.Subject, a.Classification, b.hours) \
            .orderby(a.Classification)

        self.add_fltr_args([
            dict(vals=dict(MinDateComplete=d_rng), term='between'),
            dict(vals=dict(MineSite=minesite), table=d)])

    def process_df(self, df):
        return df.pipe(self.sort_by_fctype) \
            .assign(**{
                'Hours': lambda x: x.Hours.fillna(0),
                'Total Hours': lambda x: x.Completed * x['Hours']})
    
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
        a, b, c, d = self.a, self.b, self.c, self.d

        self.cols = [d.MineSite, a.Unit, a.FCNumber, a.Complete, c.ManualClosed, a.Classification, a.Subject, a.DateCompleteSMS, a.DateCompleteKA, a.MinDateComplete, a.ReleaseDate, a.ExpiryDate, b.hours, a.Ignore]

        q = self.q \
            .where(d.MineSite==minesite)
        
        f.set_self(vars())

    def df_history(self):
        return df_rolling_n_months().d_upper \
            .apply(self.status_at_date) \
            .merge(self.df_complete_monthly(), how='left', left_index=True, right_index=True) \
            .rename_axis('Period') \
            .reset_index(drop=False)
    
    def df_complete_monthly(self):
        """Return df of period, num completed, hrs completed"""
        return self.df \
            .assign(period=lambda x: x.MinDateComplete.dt.to_period('M')) \
            .groupby(['period']) \
            .agg(
                num_completed=('hours', 'count'),
                hrs_completed=('hours', 'sum'))
            
    def df_incomplete(self, checkdate):
        """Return records which are incomplete for given checkdate"""
        return self.df \
            .pipe(lambda df: df[
                (df.ReleaseDate < checkdate) &
                (df.Classification == 'M') &
                (df.Ignore == False) &
                ((df.MinDateComplete.isnull()) | (df.MinDateComplete > checkdate))])
    
    def status_at_date(self, checkdate) -> pd.Series:
        """Count num open and hrs open at checkdate"""
        df = self.df_incomplete(checkdate)
        m = dict(
            num_outstanding=df.shape[0],
            hrs_outstanding=df.hours.sum())

        return pd.Series(m)
