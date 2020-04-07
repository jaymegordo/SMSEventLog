import sys
from datetime import (datetime as date, timedelta as delta)
from pathlib import Path
from dateutil.relativedelta import *

import pandas as pd
import pypika as pk
from pypika import Query

from . import (
    functions as f)
from .database import db

def import_unit_hrs(p=None):
    
    if p is None:
        if sys.platform.startswith('win'):
            p = Path(f.drive + f.config['FilePaths']['Import Unit Hours'])
        else:
            p = Path('/Users/Jayme/OneDrive/Desktop/Import/Unit Hours')

    df = read_unit_hrs(p=p)

    try:
        df.to_sql('UnitSMRImport', con=db.engine, if_exists='append', index=False)

        cursor = db.get_cursor()
        rowsadded = cursor.execute('ImportUnitSMR').rowcount
        cursor.commit()
    except:
        f.senderror()

    print(f'Rows added to unitSMR table: {rowsadded}')

def read_unit_hrs(p):
    df = pd.read_excel(p)
    df.columns = ['Unit', 'DateSMR', 'SMR', 'Description']

    df.SMR = df.SMR.astype(int)
    df.Unit = df.Unit.str.replace('F0', 'F').replace('^0', '', regex=True)
    df = df[df.Unit.str.startswith('F') | df.Description.str.contains('SMR')]
    df.drop(columns='Description', inplace=True)

    return df
        
def df_unit_hrs_monthly(month):
    # return df pivot of unit hrs on specific dates for caculating monthly SMR usage
    minesite = 'FortHills'

    # convert month (int) to first day of month and next month
    dtlower = date(date.now().year, month, 1)
    dates = []
    dates.append(dtlower)
    dates.append(dtlower + relativedelta(months=1))

    a = pk.Table('UnitID')
    b = pk.Table('UnitSMR')
    
    cols = [a.Unit, b.DateSMR, b.SMR]

    q = Query.from_(a).select(*cols) \
        .left_join(b).on_field('Unit') \
        .where((a.MineSite==minesite) & (b.DateSMR.isin(dates)))
    
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


