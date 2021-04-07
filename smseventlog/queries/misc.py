from .__init__ import *
from .el import EventLogBase

log = getlog(__name__)

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


class FileQuery(QueryBase):
    """Query based on saved .sql file"""
    def __init__(self, p: Path=None, sql=None, **kw):
        super().__init__(**kw)
        """
        Parameters
        ----------
        p : Path
            Path to .sql file
        """   

        f.set_self(vars())
    
    def get_sql(self, **kw):
        if self.sql is None:
            return f.sql_from_file(p=self.p)
        else:
            return self.sql

class ACMotorInspections(FileQuery):
    def __init__(self):
        p = f.projectfolder / 'SQL/FactoryCampaign/ac_motor_inspections.sql'
        super().__init__(p=p)

    def save_excel(self, _open=False):
        p = f.desktop / f'AC Motor Inspections {dt.now().date():%Y-%m-%d}.xlsx'
        style = st.default_style(self.df) \
            .pipe(self.update_style)

        style.to_excel(p, index=False, freeze_panes=(1,0))

        if _open:
            from .utils import fileops as fl
            fl.open_folder(p)
    
    def process_df(self, df):

        import re
        import string
        chars = string.ascii_lowercase[1:]

        def get_next_fc(fc_number):
            """
            Get current letter suffix of fc
            Replace with next letter eg 17H019-2b > 17H019-2c
            """
            expr = r'(?<=[-])*[a-z]'

            try:
                letter = re.search(expr, fc_number)[0]
                next_idx = chars.index(letter) + 1
                next_char = chars[next_idx]
                return re.sub(expr, next_char, fc_number)
            except:
                return f'{fc_number}b'

        df = df \
            .pipe(f.lower_cols) \
            .rename(columns=dict(floc='side')) \
            .assign(
                # hrs_pre_12k=lambda x: np.maximum(12000 - x.comp_smr_cur, 0),
                side=lambda x: x.side.str[-2:],
                date_insp=lambda x: x.date_insp.dt.date,
                hrs_since_last_insp=lambda x: np.where(
                    x.comp_smr_cur > x.comp_smr_at_insp,
                    x.comp_smr_cur - x.comp_smr_at_insp,
                    x.comp_smr_cur).astype(int),
                hrs_till_next_insp=lambda x: np.where(
                    x.comp_smr_cur > 12000,
                    3000 - x.hrs_since_last_insp,
                    np.maximum(12000 - x.comp_smr_cur, 0)).astype(int),
                date_next_insp=lambda x: (pd.Timestamp.now() + pd.to_timedelta(x.hrs_till_next_insp / 20, unit='day')).dt.date,
                overdue=lambda x: x.hrs_till_next_insp < 0,
                fc_number_next=lambda x: x.fc_complete.apply(get_next_fc),
                scheduled=lambda x: x.fc_number_next == x.last_sched_fc,
                action_reqd=lambda x: (~x.scheduled) & (x.hrs_till_next_insp <= 1000)) \
            .pipe(f.convert_int64, all_numeric=True) \
            .pipe(f.parse_datecols)
        
        self.formats.update(f.format_int64(df))

        return df
   
    def update_style(self, style, **kw):

        return style \
            .apply(
                st.background_grad_center,
                subset='hrs_till_next_insp',
                cmap=self.cmap.reversed(),
                center=1000,
                vmax=3000) \
            .apply(
                st.highlight_multiple_vals,
                subset=['overdue', 'action_reqd'],
                m={True: 'bad', False: 'goodgreen'},
                convert=True) \
            .apply(
                st.highlight_multiple_vals,
                subset=['scheduled'],
                m={True: 'goodgreen'},
                convert=True)
