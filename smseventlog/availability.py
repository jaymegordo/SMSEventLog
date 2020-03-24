import io
from datetime import datetime as date
from datetime import timedelta as delta
from pathlib import Path

import exchangelib as ex
import numpy as np
import pandas as pd
import pypika as pk
import yaml
from pypika import Case, Criterion
from pypika import CustomFunction as cf
from pypika import Order
from pypika import functions as fn

import emails as em
import functions as f
from database import db


def import_single(p):
    df = pd.read_csv(p, header=2)
    df = process_df(df=df)
    import_downtime(df=df, notification=False)

def import_downtime(df=None, notification=True):
    print('RUNNING import_downtime')
    try:
        if df is None:
            df = combine_email_data()
            if df is None:
                f.discord(msg='No rows in email', channel='sms')
                return

            df = process_df(df=df)
        df.to_sql('DowntimeImport', con=db.engine, if_exists='append', index=False)

        cursor = db.get_cursor()
        rowsadded = cursor.execute('ImportDowntimeTable').rowcount
        cursor.commit()
    except:
        f.senderror()

    msg = 'Imported from email: {}\nAdded to database: {}'.format(rowsadded, len(df))
    print(msg)

    if notification:
        f.discord(msg=msg, channel='sms')

def combine_email_data():
    maxdate = max_date_db() + delta(days=2)
    a = em.get_account()
    fldr = a.root / 'Top of Information Store' / 'Downtime'
    tz = ex.EWSTimeZone.localzone()

    # filter downtime folder to emails with date_received 2 days greater than max shift date in db
    fltr = fldr.filter(
        datetime_received__range=(
            tz.localize(ex.EWSDateTime.from_datetime(maxdate)),
            tz.localize(ex.EWSDateTime.now())))
    try:
        df = pd.concat([parse_attachment(item.attachments[0]) for item in fltr])
    except:
        df = None

    return df

def process_df(df):
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

def parse_attachment(attachment):
    result = str(attachment.content, 'UTF-8')
    data = io.StringIO(result)
    df = pd.read_csv(data, header=2)
    return df

def max_date_db():
    minesite = 'FortHills'
    a = pk.Table('Downtime')
    b = pk.Table('UnitID')

    sql = a.select(fn.Max(a.ShiftDate)) \
        .left_join(b).on_field('Unit') \
        .where(b.MineSite == minesite)
    
    try:
        cursor = db.get_cursor()
        val = cursor.execute(sql.get_sql()).fetchval()
    finally:
        cursor.close()
    
    return date.combine(val, date.min.time())
