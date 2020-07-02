import re

import numpy as np
import pandas as pd

from . import functions as f
from . import queries as qr
from .__init__ import *
from .database import db


def load_df_smr(d_lower=None):
    if d_lower is None:
        d_lower = dt(2018,1,1)

    sql = f"select a.* \
        FROM UnitSMR a \
        LEFT JOIN UnitID b on a.Unit=b.Unit \
    Where b.MineSite='FortHills' and \
    a.DateSMR>='{d_lower}'"

    return pd.read_sql(sql=sql, con=db.engine, parse_dates=['DateSMR']) \
        .rename(columns=dict(DateSMR='DateAdded')) \
        .sort_values(['DateAdded'])

def format_int(df, cols):
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
    return df

def load_df_sun():
    # load new suncor data from sap, save to this location
    p = Path('/Users/Jayme/OneDrive/Desktop/Import/Frame Cracks/Frame Cracks.xlsx')
    df = pd \
        .read_excel(p, parse_dates=['Created on']) \
        .pipe(format_int, cols=('Order', 'Notification'))
    df['Unit'] = df['Functional Loc.'].str.split('-').str[0].str.replace('F0', 'F')

    return df


def load_df_old():
    # load processed + combined history
    p = f.datafolder / 'csv/FH Frame Cracks History.xlsx'
    df = pd \
        .read_excel(p) \
        .pipe(format_int, cols=('Order', 'Notification', 'SMR'))

    df['_merge'] = 'old'
    return df

def load_processed_excel():
    # reload processed excel file
    df = load_df_old() \
        .drop(columns='_merge')
    df = df[df.Location != 'x']
    df['Month'] = df.Date.dt.to_period('M')

    return df

def pre_process_framecracks(d_lower=None):
    if d_lower is None:
        d_lower = dt.now() + delta(days=-31)
    
    df_old = load_df_old()

    # load new data, merge
    query = qr.FrameCracks(kw=dict(d_lower=d_lower))
    df_sms = query.get_df()
    df_sun = load_df_sun()
    df_smr = load_df_smr(d_lower=d_lower)

    df_new = merge_sms_sun(df_sms, df_sun, df_smr)
    
    # remove rows where Order already exists in df_old
    df_new = df_new[(~df_new.Order.isin(df_old.Order) | df_new.Order.isnull())]

    # concat old + new, drop duplicates
    # remember to keep first item (description, WOComments) in SMS as original, so later duplicates are dropped
    df = pd.concat([df_old, df_new]) \
        .drop_duplicates(subset=['Order', 'Description', 'Title', 'Unit', 'TSIDetails', 'WOComments', 'Location'], keep='first') \
        .pipe(format_int, cols=('Order', 'Notification', 'SMR')) \
        .reset_index(drop=True)

    # convert datetime to date
    df['Date'] = df['Date'].dt.date

    # copy to clipboard, paste back into sheet (could use xlwings to write to table but too much work)
    df[df['_merge'] != 'old'].to_clipboard(index=False, header=False, excel=True)

    print(f'Loaded new rows:\n\tdf_sms: {df_sms.shape}, df_sun: {df_sun.shape}, Total: {len(df_new)} \
        \n\tNew Merged: {len(df) - len(df_old)}')
    return df

def merge_sms_sun(df_sms, df_sun, df_smr):

    # df_sms  = df_sms.rename(columns=dict(SuncorWO='Order'))
    # df_sun.Order = df_sun.Order.astype('Int64')
    d_lower = '2018-01-01'

    # merge on Order when exists, then append others
    df = df_sun[df_sun.Order.notnull()] \
        .merge(right=df_sms[df_sms.Order.notnull()], how='outer', on=['Order', 'Unit'], indicator=True) \
        .append(df_sun[df_sun.Order.isnull()]) \
        .append(df_sms[df_sms.Order.isnull()]) \
    
    # mark rows not merged as new still
    df.loc[df['_merge'].isnull(), '_merge'] = 'New'
    
    # use DateAdded > prefer sms, then sun
    df.DateAdded = np.where(df.DateAdded.notnull(), df.DateAdded, df['Created on'])
    df = df \
        .query(f'DateAdded >= "{d_lower}"') \
        .drop(columns=['Created on'] ) \
        .sort_values(['DateAdded']) \

    # merge smr where missing
    df = pd.merge_asof(left=df, right=df_smr, on='DateAdded', by='Unit', direction='nearest')
    df['SMR'] = np.where(df.SMR_x.notnull(), df.SMR_x, df.SMR_y)
    df.SMR = df.SMR.astype('Int64')

    df = df.drop(columns=['SMR_x', 'SMR_y']) \
        .sort_values(['Unit', 'DateAdded']) \
        .reset_index(drop=True)
    
    # tag dumpbody location using floc
    df.loc[df['Functional Loc.']=='STRUCTR-BODYGP-DUMPBODY', 'Location'] = 'Dumpbody'

    # try and get Location from sms data, else NaN
    lst = ['front', 'mid', 'rear', 'dumpbody', 'deck', 'handrail']
    pat = '({})'.format('|'.join([f'\({item}\)' for item in lst])) # match value = "(rear)"
    df['Location'] = df['WOComments'].str.extract(pat, expand=False, flags=re.IGNORECASE) \
        .str.replace('(', '').str.replace(')', '').str.title()
    
    df = df.rename(columns=dict(DateAdded='Date'))

    return df

def df_smr_bin(df):
    # create bin labels for data at 1000hr smr intervals
    df['SMR Bin'] = pd \
        .cut(df['SMR'], bins=pd.interval_range(start=0, end=24000, freq=1000)) #.astype(str)

    return df \
        .groupby(['SMR Bin', 'Location']) \
        .size() \
        .reset_index(name='Count')

def df_smr_avg(df):
    # get avg smr for each category
    df1 = df.groupby('Location') \
        .agg(dict(SMR='mean', Location='size')) \
        .rename(columns=dict(SMR='Mean SMR', Location='Count')) \
        .reset_index()
    df1['Mean SMR'] = df1['Mean SMR'].astype(int)

    return df1

def df_month(df):
    # group into monthly bins
    return df \
        .groupby(['Month', 'Location']) \
        .size() \
        .reset_index(name='Count')
