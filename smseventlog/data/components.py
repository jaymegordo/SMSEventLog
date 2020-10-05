from .__init__ import *
from . import queries as qr
from . import eventfolders as efl

class ComponentCOConditions(qr.ComponentCOBase):
    def __init__(self, d_lower=None, components=None, minesite='FortHills', **kw):
        super().__init__(**kw)
        a, b, c = self.a, self.b, self.c

        self.cols = [a.UID, a.Unit, a.Title, a.WorkOrder, c.Component, c.Modifier, a.DateAdded, a.SMR, a.ComponentSMR, a.Floc]

        if d_lower is None:
            d_lower = dt(2020,4,1)

        if components is None:
            components = ['Spindle', 'Front Suspension', 'Rear Suspension', 'Steering Cylinder']
    
        self.fltr \
            .add(ct=a.DateAdded>=d_lower) \
            .add(ct=c.Component.isin(components)) \
            .add(ct=a.MineSite==minesite)

    def set_default_filter(self):
        self.set_minesite()

def get_condition_reports(d_lower=None):
    # query all component CO records
    query = ComponentCOConditions(minesite='FortHills')
    df_comp = db.get_df_component()
    df = query.get_df().merge(right=df_comp[['Floc', 'Combined']], how='left', on='Floc') \
        .set_index('UID', drop=False)

    pdfs = []

    # loop dataframe and check/get condition report pdfs
    for row in df.itertuples():
        ef = efl.EventFolder.from_model(e=row)
        ef.check(check_pics=False)
        df.loc[row.UID, 'HasReport'] = str(ef.condition_reports[0]) if ef.has_condition_report else False

        pdfs.extend(ef.condition_reports)
    
    # save excel file of data
    p = Path.home() / 'Desktop/condition_reports.xlsx'
    df.to_excel(p, index=False)

    # copy all condition reports to folder
    p_dst = Path.home() / 'desktop/Condition Reports'
    for p in pdfs:
        fl.copy_file(p_src=p, p_dst=p_dst / p.name)

    return df, pdfs