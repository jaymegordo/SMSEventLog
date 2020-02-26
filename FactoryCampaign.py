from collections import defaultdict as dd
from datetime import datetime as date
from datetime import timedelta as delta
from pathlib import Path
from timeit import default_timer as timer

import pandas as pd
import pypika as pk
from bs4 import BeautifulSoup

import Functions as f
from database import db

# from timeit import Timer
	# t = Timer(lambda: fldr.readsingle(p))
	# print(t.timeit(number=10))

def tblcount(tbl):
    cursor = db.get_cursor()
    sql = f'Select count(*) From {tbl}'
    return cursor.execute(sql).fetchval()

def importFC(upload=True, df=None):
    start = timer()
    # load all 'xls' files from import folder to df
    p = Path(f.drive + f.config['FilePaths']['Import FC'])
    lst = [f for f in p.glob('*.xls')]

    # TODO: msgbox found files: would u like to import?

    if df is None: df = pd.concat([read_fc(p=p) for p in lst], sort=False)

    print('Loaded ({}) FCs from {} file(s) in: {}s' \
        .format(len(df), len(lst), f.deltasec(start, timer())))

    # import to temp staging table in db, then merge new rows to FactoryCampaign
    if upload:
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        df.to_sql(name='FactoryCampaignImport', con=db.engine, if_exists='append', index=False)

        print('Rows read from import files: {}'.format(len(df)))

        try:
            # FactoryCampaign Import
            rows = dd(int, cursor.execute('mergeFCImport').fetchall())
            print(dict(rows))
            print('FactoryCampaign: \n\tRows added: {}\n\tRows updated: {}\n\tKA Completion dates added: {}' \
                .format(
                    rows['INSERT'], 
                    rows['UPDATE'], 
                    rows['KADatesAdded']))

            # FC Summary Update
            rows = dd(int, cursor.execute('MergeFCSummary').fetchall())
            print(dict(rows))
            print('FC Summary: \n\tRows added: {}\n\tRows updated: {}' \
                .format(
                    rows['INSERT'], 
                    rows['UPDATE']))
            
            cursor.commit()

            print('Finished: {}'.format(f.deltasec(start, timer())))
        finally:
            cursor.close()
            conn.close()

        # TODO: msgbox would you like to remove files?
    
    return df


def read_fc(p):
    # Raw FC data comes from KA as an html page disguised as an xls
    # TODO: Drop ServiceLetterDate > same as StartDate
    # TODO: Drop CompletionDate > changed to DateCompleteKA, Drop ClaimNumber

    with open(p) as html:
        table = BeautifulSoup(html).findAll('table')[2] # FC data is in 3rd table

    cols = [hdr.text for hdr in table.find('thead').find_all('th')]
    data = [[col.text for col in row.findAll('td')] for row in table.findAll('tr')[1:]]
    df = pd.DataFrame(data=data, columns=cols)

    cols = ['Start Date', 'End Date', 'Completion Date', 'Service Letter Date']
    df[cols] = df[cols].apply(pd.to_datetime)

    dfu = db.get_df_unit()
    df = df.merge(right=dfu[['Model', 'Serial', 'Unit']], how='left')

    # Remove missing units
    # TODO: Return these to user somehow?
    df.Unit.replace('', pd.NA, inplace=True)
    df.dropna(subset=['Unit'], inplace=True)

    # Rename Cols
    df.columns = ['FCNumber', 'Distributor', 'Branch', 'Model', 'Serial', 'Safety', 'StartDate', 'EndDate', 'Subject', 'ClaimNumber', 'CompletionSMR', 'DateCompleteKA', 'Status', 'Hours', 'ServiceLetterDate', 'Classification', 'Unit']

    # Drop and reorder,  Don't import: CompletionSMR, claimnumber, ServiceLetterDate
    cols = ['FCNumber','Model', 'Serial', 'Unit', 'StartDate', 'EndDate', 'DateCompleteKA', 'Subject', 'Classification', 'Hours', 'Distributor', 'Branch',  'Safety', 'Status']
    df = df[cols]

    df.FCNumber = df.FCNumber.str.strip()

    return df

def import_ka():
    p = Path('C:/Users/jayme/OneDrive/Desktop/KA Machine Info')
    lst = [f for f in p.glob('*.html')]

    df = pd.concat([read_ka(p=p) for p in lst], sort=False).reset_index(drop=True)

    return df

def read_ka(p):
    with open(p) as html:
        table = BeautifulSoup(html).findAll('table')[1]

    cols = ['Unit', 'Model', 'Serial', 'LastSMR']
    data = [[col.text.replace('\n', '').replace('\t', '') for col in row.findAll('td')[2:6]] for row in table.findAll('tr')]
    df = pd.DataFrame(data=data, columns=cols)
    df = df[df.Serial.str.len()>2].reset_index(drop=True)
    df.LastSMR = pd.to_datetime(df.LastSMR, format='%m/%d/%Y %H:%M %p')

    return df
