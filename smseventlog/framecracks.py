from .__init__ import *
from .database import db
import pandas as pd
import numpy as np

def load_sms():

    sql = "select \
        a.Unit, \
        a.DateAdded, \
        a.Title, \
        a.SMR, \
        a.TSIPartName, \
        a.TSIDetails, \
        a.WOComments, \
        a.TSINumber, \
        a.SuncorWO \
    FROM EventLog a INNER JOIN UnitID b on a.Unit=b.Unit \
    WHERE \
        a.Title like '%crack%' and \
        b.MineSite='FortHills'"

    df = pd.read_sql(sql=sql, con=db.engine) \
        .rename(columns=dict(SuncorWO='Order'))
    
    df.Order = pd.to_numeric(df.Order, errors='coerce').astype('Int64')
    df.DateAdded = df.DateAdded.apply(pd.to_datetime)

    return df

def df_smr():
    sql = "select a.* \
        FROM UnitSMR a \
        LEFT JOIN UnitID b on a.Unit=b.Unit \
    Where b.MineSite='FortHills' and \
    a.DateSMR >= '2018-01-01'"

    return pd.read_sql(sql=sql, con=db.engine, parse_dates=['DateSMR']) \
        .rename(columns=dict(DateSMR='DateAdded')) \
        .sort_values(['DateAdded'])

def merge_sms_sun(df_sms, df_sun, df_smr):

    # df_sms  = df_sms.rename(columns=dict(SuncorWO='Order'))
    # df_sun.Order = df_sun.Order.astype('Int64')
    d_lower = '2018-01-01'

    df = df_sun[df_sun.Order.notnull()] \
        .merge(right=df_sms[df_sms.Order.notnull()], how='outer', on=['Order', 'Unit'], indicator=True) \
        .append(df_sun[df_sun.Order.isnull()]) \
        .append(df_sms[df_sms.Order.isnull()]) \
        
    df.DateAdded = np.where(df.DateAdded.notnull(), df.DateAdded, df['Created on'])
    df = df \
        .query(f'DateAdded >= "{d_lower}"') \
        .drop(columns=['Created on'] ) \
        .sort_values(['DateAdded']) \

    df = pd.merge_asof(left=df, right=df_smr, on='DateAdded', by='Unit', direction='nearest')
    df['SMR'] = np.where(df.SMR_x.notnull(), df.SMR_x, df.SMR_y)
    df.SMR = df.SMR.astype('Int64')

    df = df.drop(columns=['SMR_x', 'SMR_y']) \
        .sort_values(['Unit', 'DateAdded']) \
        .reset_index(drop=True)
    
    return df

def load_processed_excel():
    # reload processed excel file
    p = Path.home() / 'desktop/FH Frame Cracks History.xlsx'
    df = pd.read_excel(p)
    df = df[df.Location != 'x']
    df['Month'] = df.Date.dt.to_period('M')

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
