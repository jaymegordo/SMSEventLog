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