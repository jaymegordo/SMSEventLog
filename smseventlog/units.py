from . import exchange as exh
from . import functions as f
from .__init__ import *
from .database import db

global m, cols
m = dict(imptable='UnitSMRImport', impfunc='ImportUnitSMR')
cols = ['Unit', 'DateSMR', 'SMR']

def import_unit_hrs_email():
    # NOTE will need to check maxdate per FH and 63N
    maxdate = db.max_date_db(table='UnitSMR', field='DateSMR') + delta(days=1)
    df = exh.combine_email_data(folder='SMR', maxdate=maxdate)
    df = process_df(df)
    db.import_df(df=df, imptable=m['imptable'], impfunc=m['impfunc'])

def process_df(df):
    if df is None: return None
    df = df[['SAP_Parameter', 'Date', 'Hours']]
    df.columns = cols

    df.DateSMR = pd.to_datetime(df.DateSMR, format='%Y%m%d')
    df = df[df.Unit.str.contains('SMR')]
    df.Unit = df.Unit.str.replace('F0', 'F').str.replace('SMR', '')
    df = df[df.Unit.str.contains('F3')] # filter only F300 980s for now
    df.SMR = df.SMR.astype(int)

    return df.reset_index(drop=True)

def import_unit_hrs(p=None):
    if p is None:
        if f.is_win():
            p = Path(f.drive + f.config['FilePaths']['Import Unit Hours'])
        else:
            p = Path('/Users/Jayme/OneDrive/Desktop/Import/Unit Hours')
        
        lst = [f for f in p.glob('*.xls*')]
        p = lst[0]

    df = read_unit_hrs(p=p)
    db.import_df(df=df, imptable=m['imptable'], impfunc=m['impfunc'], notification=False)
    # TODO: could ask to delete file after import?

def read_unit_hrs(p):
    df = pd.read_excel(p)
    columns = cols.append('Description')
    df.columns = columns

    df.SMR = df.SMR.astype(int)
    df.Unit = df.Unit.str.replace('F0', 'F').replace('^0', '', regex=True)
    df = df[df.Unit.str.startswith('F') | df.Description.str.contains('SMR')]
    df.drop(columns='Description', inplace=True)

    return df
        
def df_unit_hrs_monthly(month):
    # return df pivot of unit hrs on specific dates for caculating monthly SMR usage
    minesite = 'FortHills'

    # convert month (int) to first day of month and next month
    dtlower = dt(dt.now().year, month, 1)
    dates = []
    dates.append(dtlower)
    dates.append(dtlower + relativedelta(months=1))

    a = T('UnitID')
    b = T('UnitSMR')
    
    cols = [a.Unit, b.DateSMR, b.SMR]

    q = Query.from_(a).select(*cols) \
        .left_join(b).on_field('Unit') \
        .where((a.MineSite==minesite) & (b.DateSMR.isin(dates) & (a.ExcludeMA.isnull())))
    
    df = pd.read_sql(sql=q.get_sql(), con=db.engine)

    # Pivot df to dates as columns
    df = df.pivot(index='Unit', columns='DateSMR', values='SMR')
    df['Difference'] = df.iloc[:, 1] - df.iloc[:, 0]
    df.rename_axis('Unit', inplace=True, axis=1) # have to rename 'DateSMR' index to Unit

    # Merge Serial, DeliveryDate from unit info
    dfu = db.get_df_unit(minesite=minesite).set_index('Unit')[['Serial', 'DeliveryDate']]
    df = dfu.merge(right=df, how='right', on='Unit')
    df.reset_index(inplace=True)

    return df

def update_comp_smr():
    from .gui import dialogs as dlgs
    try:
        cursor = db.cursor
        res = cursor.execute('updateUnitComponentSMR').fetchall()[0]
        cursor.commit()
    finally:
        cursor.close()

    unit_hrs, comp_hrs = res[0], res[1]
    msg = f'Unit SMR updated: {unit_hrs}\nComponent SMR updated: {comp_hrs}'
    dlgs.msg_simple(msg=msg)