from datetime import (datetime as dt, timedelta as delta)
from pathlib import Path

import exchangelib as ex
import numpy as np
import pandas as pd
import pypika as pk
import yaml
from pypika import (
    Case,
    Criterion,
    CustomFunction as cf,
    Order,
    functions as fn)

from . import (
    emails as em,
    functions as f)
from .database import db


def import_single(p):
    df = pd.read_csv(p, header=2)
    df = process_df(df=df)
    db.import_df(df=df, imptable='DowntimeImport', impfunc='ImportDowntimeTable', notification=False)

def import_downtime_email():
    maxdate = db.max_date_db(table='Downtime', field='ShiftDate') + delta(days=2)
    df = em.combine_email_data(folder='Downtime', maxdate=maxdate)
    df = process_df(df=df)
    db.import_df(df=df, imptable='DowntimeImport', impfunc='ImportDowntimeTable')

def process_df(df):
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