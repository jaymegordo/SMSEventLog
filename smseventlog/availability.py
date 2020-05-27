import exchangelib as ex
import numpy as np
import pandas as pd
import pypika as pk
import yaml
from pypika import Case, Criterion
from pypika import CustomFunction as cf
from pypika import Order
from pypika import functions as fn

from . import emails as em
from . import functions as f
from .__init__ import *
from .database import db


def import_single(p):
    df = pd.read_csv(p, header=2)
    df = process_df_downtime(df=df)
    db.import_df(df=df, imptable='DowntimeImport', impfunc='ImportDowntimeTable', notification=False)

def import_downtime_email():
    maxdate = db.max_date_db(table='Downtime', field='ShiftDate') + delta(days=2)
    df = em.combine_email_data(folder='Downtime', maxdate=maxdate, subject='Equipment Downtime')
    df = process_df_downtime(df=df)
    db.import_df(df=df, imptable='DowntimeImport', impfunc='ImportDowntimeTable')

def import_dt_exclusions_email():
    maxdate = db.max_date_db(table='DowntimeExclusions', field='Date') + delta(days=2)
    df = em.combine_email_data(folder='Downtime', maxdate=maxdate, subject='Equipment Availability', header=0)  
    df = process_df_exclusions(df=df)
    return df
    db.import_df(df=df, imptable='DowntimeExclusionsImport', impfunc='ImportDowntimeExclusions')

def process_df_exclusions(df):
    if df is None: return None

    df = df[['EqmtUnit', 'TC08', 'Duration', 'DateEmail']]
    df.columns = ['Unit', 'OutOfSystem', 'Total', 'Date']
    df.Unit = df.Unit.str.replace('F0', 'F')
    df.Date = pd.to_datetime(df.Date)
    df['Hours'] = 24 - (df.Total - df.OutOfSystem) # hours = actual out of system hrs
    df = df[df.Hours > 0] # units can only have MAX 24 hrs out of system
    df['MA'] = 1 # assume all exclusions always apply to MA and PA, will have to manually change when needed
    df.drop(columns=['OutOfSystem', 'Total'], inplace=True)
    return df

def process_df_downtime(df):
    if df is None: return None
    df = df[df.EqmtModel=='Komatsu 980E-OS'] # filter haul trucks only

    # convert fullshiftname, moment, duration to startdate, enddate, duration
    df['ShiftDate'] = pd.to_datetime(df.FullShiftName.str.split(' ', expand=True)[0], format='%d-%b-%Y')
    df.Moment = pd.to_timedelta(df.Moment)
    df.Duration = pd.to_timedelta(df.Duration)
    df['StartDate'] = df.apply(lambda x: parse_date(x.ShiftDate, x.Moment), axis=1)
    df['EndDate'] = df.StartDate + df.Duration
    df.Duration = df.Duration.dt.total_seconds() / 3600 # convert to hours, eg 1.03

    if not 'Origin' in df.columns:
        df['Origin'] = 'Staffed'

    cols = ['FieldId', 'StartDate', 'EndDate', 'Duration', 'Reason', 'FieldComment', 'ShiftDate', 'Origin']
    df = df[cols]
    df.columns = ['Unit', 'StartDate', 'EndDate', 'Duration', 'DownReason', 'Comment', 'ShiftDate', 'Origin']

    df.Unit = df.Unit.str.replace('F0', 'F')

    return df

def parse_date(shiftdate, timedelta):
    # if timedelta is < 6am, shift day is next day
    if timedelta.total_seconds() < 3600 * 6:
        shiftdate += delta(days=1)
    
    return shiftdate + timedelta

def ahs_pa_monthly():

    df = pd.read_sql_table(table_name='viewPAMonthly', con=db.get_engine())
    df = df.pivot(index='Unit', columns='MonthStart', values='Sum_DT')
    return df
