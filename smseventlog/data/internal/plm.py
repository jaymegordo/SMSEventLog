from .__init__ import *
from . import utils as utl

log = getlog(__name__)

global m_equip, m_cols, good_cols
m_equip = f.inverse(f.config['EquipPaths'])

m_cols = {
    'Date': 'date',
    'Time': 'time',
    'Payload(Net)': 'payload',
    'Swingloads': 'swingloads',
    'Status Flag': 'statusflag',
    'Carry Back': 'carryback',
    'TotalCycle Time': 'cycletime',
    'L-Haul Distance': 'l_hauldistance',
    'L-Max Speed': 'l_maxspeed',
    'E MaxSpeed': 'e_maxspeed',
    'Max Sprung': 'maxsprung',
    'Truck Type': 'trucktype',
    'Tare Sprung Weight': 'sprungweight',
    'Payload Est.@Shovel(Net)': 'payload_est',
    'Quick Payload Estimate(Net)': 'payload_quick',
    'Gross Payload': 'payload_gross'}

good_cols = ['unit', 'datetime']
good_cols.extend([col for col in m_cols.values() if not col in ('date', 'time')])

# PLM
def update_plm_all_units(minesite='FortHills', model='980'):
    units = db.unique_units(minesite=minesite, model=model)

    # multiprocess
    result = Parallel(n_jobs=-1, verbose=11)(delayed(update_plm_single_unit)(unit=unit, import_=False) for unit in units)

    config = utl.get_config()['plm']

    # could have duplicates from file in wrong unit path, drop again to be safe
    df = pd.concat(m['df'] for m in result) \
        .drop_duplicates(subset=config['duplicate_cols'])
   
    rowsadded = db.import_df(df=df, imptable=config['imptable'], impfunc=config['impfunc'], prnt=True, chunksize=10000)

    new_result = []
    for m in result:
        df = m['df']
        # rowsadded = db.import_df(df=df, imptable=config['imptable'], impfunc=config['impfunc'], prnt=True, chunksize=10000)

        new_result.append(dict(unit=m['unit'], maxdate=m['maxdate'].strftime('%Y-%m-%d'), numrows=len(df)))

    return new_result

def import_plm_csv(lst_csv: list):
    """Convenience func to import list of plm cycle csvs to db
    
    Parameters
    ---
    lst_csv : list,
        List of csvs to combine and import
    
    Returns
    ---
        number of rows successfully added to db.
    """
    ftype = 'plm'
    config = utl.get_config()[ftype]

    df = utl.combine_csv(lst_csv=lst_csv, ftype=ftype)
    rowsadded = db.import_df(df=df, imptable=config['imptable'], impfunc=config['impfunc'], prnt=True, notification=False)

    return rowsadded

def update_plm_single_unit(unit, import_=True, maxdate=None):
    # get max date db
    print(f'starting unit: {unit}')

    if maxdate is None:
        a = T('PLM')
        q = a.select(fn.Max(a.DateTime)) \
            .where(a.Unit == unit)
        
        maxdate = db.max_date_db(q=q)
        if maxdate is None: maxdate = dt.now() + delta(days=-731)
   
    result = utl.process_files(ftype='plm', units=unit, d_lower=maxdate, import_=import_)

    # kinda sketch... bad design here
    if import_:
        rowsadded = result
        df = None
    else:
        rowsadded = None
        df = result

    m = dict(unit=unit, maxdate=maxdate, rowsadded=rowsadded, df=df)
    return m

def get_minesite_from_path(p : Path) -> str:
    """Parse file path, check if in equip paths"""
    if not isinstance(p, Path): p = Path(p)
    lst = list(filter(lambda x: x[0] in p.as_posix(), m_equip.items()))
    if lst:
        return lst[0][1]
    else:
        log.warning(f'Couldn\'t get minesite in path: {p}')

def read_plm(p):
    """Wrap import_plm for errors"""
    try:
        return import_plm(p)
    except Exception as e:
        msg = f'Failed plm import, {e.args[0]}: {p}'
        log.warning(msg)
        utl.write_import_fail(msg)
        return pd.DataFrame(columns=good_cols)

def import_plm(p):
    """Load single plmcycle file to dataframe"""

    # header, try unit, then try getting unit with serial
    df_head = pd.read_csv(p, nrows=6, header=None)
    unit = df_head[0][1].split(':')[1].strip()
    
    minesite = get_minesite_from_path(p)
    if minesite == 'FortHills':
        unit = unit.upper().replace('O','0').replace('F-','F').replace('F0','F')

    if unit == '' or not db.unit_exists(unit):
        # try to get unit from serial/minesite
        if minesite is None:
            raise Exception('Couldn\'t get minesite from unit path.')

        serial = df_head[0][0].split(':')[1].strip().upper()

        if serial.strip() == '':
            # fallback to getting unit from path
            unit = utl.unit_from_path(p)
            if not unit is None:
                log.warning(f'Falling back to unit from path: {unit}, {p}')
            else:
                raise Exception('Couldn\'t read serial from plm file.')
        
        if unit == '':
            unit = db.get_unit(serial=serial, minesite=minesite)
    
    if not db.unit_exists(unit):
        raise Exception(f'Unit: {unit} does not exist in db.')

    return pd.read_csv(p, engine='c', header=8, usecols=m_cols, parse_dates=[['Date', 'Time']]) \
        .iloc[:-2] \
        .dropna(subset=['Date_Time']) \
        .rename(columns=m_cols) \
        .assign(
            unit=unit,
            datetime=lambda x: pd.to_datetime(x['Date_Time'], format='%m/%d/%y %H:%M:%S'),
            cycletime=lambda x: x['cycletime'].apply(utl.to_seconds),
            carryback=lambda x: x['carryback'].str.replace(' ', '').astype(float)) \
        [good_cols]