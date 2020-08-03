from . import dbmodel as dbm
from . import exchange as exh
from . import functions as f
from .__init__ import *
from .database import db


def import_single(p):
    df = pd.read_csv(p, header=2)
    df = process_df_downtime(df=df)
    db.import_df(df=df, imptable='DowntimeImport', impfunc='ImportDowntimeTable', notification=False)

def import_downtime_email():
    maxdate = db.max_date_db(table='Downtime', field='ShiftDate') + delta(days=2)
    df = exh.combine_email_data(folder='Downtime', maxdate=maxdate, subject='Equipment Downtime')
    df = process_df_downtime(df=df)
    db.import_df(df=df, imptable='DowntimeImport', impfunc='ImportDowntimeTable')

def import_dt_exclusions_email():
    maxdate = db.max_date_db(table='DowntimeExclusions', field='Date') + delta(days=2)
    df = exh.combine_email_data(folder='Downtime', maxdate=maxdate, subject='Equipment Availability', header=0)  
    df = process_df_exclusions(df=df)
    import_dt_exclusions(df=df)

def import_dt_exclusions(df):
    db.import_df(df=df, imptable='DowntimeExclusionsImport', impfunc='ImportDowntimeExclusions')

def create_dt_exclusions(dates, rng_unit):
    # manually create exclusion hrs when emails didn't get sent
    # dates is list of dates
    df = pd.concat([create_dt_exclusions_single(date, rng_unit) for date in dates])
    return df

def create_dt_exclusions_single(date, rng_unit, hrs=24):
    df = pd.DataFrame(columns=['Unit', 'Date', 'Hours', 'MA'])
    df.Unit = range_units(rng_unit)
    df.Hours = hrs
    df.MA = 1
    df.Date = date
    return df

def range_units(rng):
    # rng is tuple of first-last units eg (317, 330)
    return tuple([f'F{unit}' for unit in range(rng[0], rng[1] + 1)])

def process_df_exclusions(df):
    # convert csv from suncor to database format
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

def update_dt_exclusions_ma(units, rng_dates=None, dates=None):
    # set MA=0 (False) for units in given date range range

    t = pk.Table('DowntimeExclusions')
    cond = [t.Unit.isin(units)]

    if not rng_dates is None:
        cond.append(t.Date.between(*rng_dates))
    
    if not dates is None:
        cond.append(t.Date.isin(dates))

    q = pk.Query().update(t).set(t.MA, 0).where(pk.Criterion.all(cond))
    sql = q.get_sql()
    
    # print(sql)
    cursor = db.cursor
    cursor.execute(sql)
    cursor.commit()

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
    df.drop_duplicates(subset=['Unit', 'StartDate', 'EndDate'], inplace=True)

    return df

def parse_date(shiftdate, timedelta):
    # if timedelta is < 6am, shift day is next day
    if timedelta.total_seconds() < 3600 * 6:
        shiftdate += delta(days=1)
    
    return shiftdate + timedelta

def ahs_pa_monthly():
    df = pd.read_sql_table(table_name='viewPAMonthly', con=db.engine)
    df = df.pivot(index='Unit', columns='MonthStart', values='Sum_DT')
    return df

def dt_exclusions_ma_example():
    # create all units with MA hrs below hrs in period
    from . import folders as fl
    units = []
    units.extend(fl.all_units(rng=(300,322)))
    units.extend(fl.all_units(rng=(331,348)))

    rng = (dt(2020,7,1), dt(2020,8,1))
    update_dt_exclusions_ma(units=units, rng_dates=rng)