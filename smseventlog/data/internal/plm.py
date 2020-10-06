from .__init__ import *
from . import utils as utl

log = logging.getLogger(__name__)

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
        if maxdate is None: maxdate = dt.now() + delta(days=-731)
   
    rowsadded = utl.process_files(ftype='haul', units=unit, d_lower=maxdate, import_=import_)

    m = dict(unit=unit, maxdate=maxdate, rowsadded=rowsadded)
    return m

def get_minesite_from_path(p : Path) -> str:
    """Parse file path, check if in equip paths"""
    lst = list(filter(lambda x: x[0] in str(p), m_equip.items()))
    if lst:
        return lst[0][1]

def read_haul(p):
    """Wrap import_haul for errors"""
    try:
        return import_haul(p)
    except:
        log.warning(f'Failed plm import: {p}')
        return pd.DataFrame(columns=good_cols)

def import_haul(p):
    """Load single haulcycle file to dataframe"""

    # header, try unit, then try getting unit with serial
    df_head = pd.read_csv(p, nrows=6, header=None)
    unit = df_head[0][1].split(':')[1].strip().upper().replace('O','0').replace('F-','F').replace('F0','F')
    if unit == '':
        minesite = get_minesite_from_path(p)
        if minesite is None:
            raise Exception('Couldn\'t get minesite from unit path.')

        serial = df_head[0][0].split(':')[1].strip().upper()
        unit = db.get_unit(serial=serial, minesite=minesite)

    return pd.read_csv(p, header=8, usecols=m_cols, parse_dates=[['Date', 'Time']]) \
        [:-2] \
        .dropna(subset=['Date_Time']) \
        .rename(columns=m_cols) \
        .assign(
            unit=unit,
            datetime=lambda x: pd.to_datetime(x['Date_Time'], format='%m/%d/%y %H:%M:%S'),
            cycletime=lambda x: x['cycletime'].apply(utl.to_seconds),
            carryback=lambda x: x['carryback'].str.replace(' ', '').astype(float)) \
        [good_cols]