from .__init__ import *
from . import utils as utl

# PLM
def update_plm_all_units():
    units = utl.all_units()

    # multiprocess
    result = Parallel(n_jobs=-1, verbose=11)(delayed(update_plm_single_unit)(unit, False) for unit in units)

    config = utl.get_config()['haul']

    df = pd.concat(m['df'] for m in result)
    rowsadded = db.import_df(df=df, imptable=config['imptable'], impfunc=config['impfunc'], prnt=True, chunksize=10000)

    new_result = []
    for m in result:
        df = m['df']
        # rowsadded = db.import_df(df=df, imptable=config['imptable'], impfunc=config['impfunc'], prnt=True, chunksize=10000)

        new_result.append(dict(unit=m['unit'], maxdate=m['maxdate'].strftime('%Y-%m-%d'), numrows=len(df)))

    return new_result

def update_plm_single_unit(unit, import_=True, maxdate=None):
    # get max date db
    print(f'starting unit: {unit}')

    if maxdate is None:
        a = T('PLM')
        q = a.select(fn.Max(a.DateTime)) \
            .where(a.Unit == unit)
        
        maxdate = db.max_date_db(q=q)
    
    df = utl.process_files(ftype='haul', units=unit, d_lower=maxdate, import_=import_)

    m = dict(unit=unit, maxdate=maxdate, df=df)
    return m

def read_haul(p):
    # load single haulcycle file to dataframe
    minesite = 'FortHills' #TODO may need to change this, fix db.get_unit

    cols = ['Date', 'Time', 'Payload(Net)', 'Swingloads', 'Status Flag', 'Carry Back', 'TotalCycle Time', 'L-Haul Distance', 'L-Max Speed', 'E MaxSpeed', 'Max Sprung', 'Truck Type', 'Tare Sprung Weight', 'Payload Est.@Shovel(Net)', 'Quick Payload Estimate(Net)', 'Gross Payload']

    newcols = ['datetime', 'payload', 'swingloads', 'statusflag', 'carryback', 'cycletime', 'l_hauldistance', 'l_maxspeed', 'e_maxspeed', 'maxsprung', 'trucktype', 'sprungweight', 'payload_est', 'payload_quick', 'payload_gross']

    try:
        # header, try unit, then try getting unit with serial
        df_head = pd.read_csv(p, nrows=6, header=None)
        unit = df_head[0][1].split(':')[1].strip().upper().replace('O','0').replace('F-','F').replace('F0','F')
        if unit == '':
            serial = df_head[0][0].split(':')[1].strip().upper()
            unit = db.get_unit(serial=serial, minesite=minesite)

        df = pd.read_csv(p, header=8, usecols=cols, parse_dates=[['Date', 'Time']])[:-2]
        df.columns = newcols
        df.insert(0, 'unit', unit)
        df.datetime = pd.to_datetime(df.datetime, format='%m/%d/%y %H:%M:%S')
        df.cycletime = df.cycletime.apply(utl.to_seconds)
        df.carryback = df.carryback.str.replace(' ', '').astype(float)    
        return df
    except:
        print(f'Failed: {p}')
        write_import_fail(p)
        return pd.DataFrame(columns=newcols)