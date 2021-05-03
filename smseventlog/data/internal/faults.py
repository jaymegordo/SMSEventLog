from .__init__ import *
from . import utils as utl

def parse_fault_time(tstr):
    arr = tstr.split('|')
    t, tz = int(arr[0]), int(arr[1])
    return dt.fromtimestamp(t) + delta(seconds=tz)

def read_fault(p : Path) -> pd.DataFrame:
    """Return dataframe from fault.csv path
    - NOTE need to handle minesites other than forthills

    Parameters
    ----------
    p : Path
    """    
    newcols = ['unit', 'code', 'time_from', 'time_to', 'faultcount', 'message']

    try:
        # read header to get serial
        serial = pd.read_csv(p, skiprows=4, nrows=1, header=None)[1][0]
        unit = db.get_unit(serial=serial, minesite='FortHills')

        df = pd.read_csv(p, header=None, skiprows=28, usecols=(0, 1, 3, 5, 7, 8))
        df.columns = newcols
        df.unit = unit
        df.code = df.code.str.replace('#', '')
        df.time_from = df.time_from.apply(parse_fault_time)
        df.time_to = df.time_to.apply(parse_fault_time)
        
        return df
    except:
        print(f'Failed: {p}')
        return pd.DataFrame(columns=newcols)

def combine_fault_header(m_list: dict):
    dfs = []

    for unit, lst in m_list.items():
        for p in lst:
            try:
                df = read_fault_header(p)
                dfs.append(df)
                break
            except:
                print(f'failed import: {p}')

    return pd.concat(dfs)

def read_fault_header(p):
    df = pd.read_csv(p, nrows=12, names=[i for i in range(5)])
    unit = utl.unit_from_path(p)

    m = dict(
        serial_no=df.loc[4, 1],
        eng_model=df.loc[5, 1],
        eng_sn_1=df.loc[5, 2],
        eng_sn_2=df.loc[5, 4],
        prog_ver_1=df.loc[11, 1],
        prog_ver_2=df.loc[11, 2],
    )

    return pd.DataFrame \
        .from_dict(m, orient='index', columns=[unit]).T \
        .rename_axis('unit')