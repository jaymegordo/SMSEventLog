from collections import OrderedDict

from . import utils as utl
from .__init__ import *

log = getlog(__name__)

def date_from_title(title) -> dt:
    """Parse date obj from date in folder title"""
    date_reg_exp = re.compile('(\d{4}[-]\d{2}[-]\d{2})')
    ans = re.search(date_reg_exp, title)

    if not ans or len(ans.groups()) < 1: return

    d = dt.strptime(ans.group(1), '%Y-%m-%d')
    return d

def is_year(name : str) -> bool:
    """Check if passed in string is a 4 digit year, eg '2020'

    Parameters
    ----------
    name : str
        String to check

    Returns
    -------
    bool
    """
    exp = re.compile('^[2][0-9]{3}$')
    ans = re.search(exp, name)
    return not ans is None

def recurse_dsc(p_search : Path, d_lower=dt(2020,1,1), depth=0, maxdepth=5) -> list:
    """Recurse and find any file/folder paths containing 'dsc'"""
    lst = []

    if depth <= maxdepth:
        for p in p_search.iterdir():
            if 'dsc' in p.name:
                lst.append(p) # end recursion
            elif (p.is_dir() and fl.date_modified(p) > d_lower):
                lst.extend(recurse_dsc(
                    p_search=p,
                    depth=depth + 1,
                    maxdepth=maxdepth,
                    d_lower=d_lower))
    
    return lst

def get_recent_dls_unit(unit : str) -> Path:
    """Get most recent dls folder for single unit

    Parameters
    ----------
    unit : str

    Returns
    -------
    Path
        Path to most recent dls folder
    """    
    from ...gui.dialogs import msg_simple

    p_unit = efl.UnitFolder(unit=unit).p_unit
    p_dls = p_unit / 'Downloads'

    # get all downloads/year folders
    lst_year = [p for p in p_dls.iterdir() if p.is_dir() and is_year(p.name)]

    if not lst_year:
        msg_simple(msg='No download folders found.', icon='warning')
        return

    # sort year folders by name, newest first, select first
    lst_year_sorted = sorted(lst_year, key=lambda p: p.name, reverse=True) # sort by year
    p_year = lst_year_sorted[0]

    try:
        # sort all dls folders on date from folder title
        lst_dls = [p for p in p_year.iterdir() if p.is_dir()]
        lst_dls_sorted = sorted(filter(lambda p: date_from_title(p.name) is not None, lst_dls), key=lambda p: date_from_title(p.name), reverse=True)
        return lst_dls_sorted[0]
    except:
        er.log_error(log=log, msg='Couldn\'t find recent dls folder.')
        return None

def zip_recent_dls_unit(unit :str, _zip=True) -> Path:
    """Func for gui to find (optional zip) most recent dls folder by parsing date in folder title"""
    from ...gui.dialogs import msg_simple, msgbox

    p_dls = get_recent_dls_unit(unit=unit)

    if not p_dls is None:
        msg = f'Found dls folder:\n\n{p_dls.name}\n\nZip now?'
        if not msgbox(msg=msg, yesno=True): return
    else:
        msg = f'Couldn\'t find recent DLS folder, check folder structure for issues.'
        msg_simple(msg=msg, icon='critical')
        return

    if _zip:
        p_zip = fl.zip_folder(p=p_dls, delete=False)
        return p_zip
    else:
        return p_dls

def fix_dsc(p : Path, p_unit : Path, zip_=False):
    """Process/fix single dsc/dls folder"""
    start = timer()
    unit = p_unit.name.split(' - ')[0]

    p_parent = p.parent
    d = date_from_dsc(p=p)

    # rename dls folder: UUU - YYYY-MM-DD - DLS
    newname = '{} - {} - DLS'.format(unit, d.strftime('%Y-%m-%d'))

    p_new = p_unit / f'Downloads/{d.year}/{newname}'

    # need to make sure there is only one _dsc_ folder in path
    # make sure dsc isn't within 2 levels of 'Downloads' fodler
    dsccount = sum(1 for _ in p_parent.glob('*dsc*'))

    if dsccount > 1 or check_parents(p=p, depth=2, names=['downloads']):
        # just move dsc folder, not parent and contents
        p_src = p
        p_dst = p_new / p.name
    else:
        p_src = p_parent # folder above _dsc_
        p_dst = p_new

    # zip and move datapack, then move anything else remaining in the parent dir
    print(f'\nsrc: {p_src}\ndest: {p_dst}')
    try:
        if zip_ and \
            not str(p).endswith('.zip') and \
            not str(p).endswith('.tar'):
            # p_datapack = p / 'datapack'

            p_zip = fl.zip_folder(
                p=p,
                delete=True,
                p_new=p_new / p.name,
                calculate_size=False)

        fl.move_folder(p_src=p_src, p_dst=p_dst)
    except:
        print(f'Error fixing dsc folder: {str(p_src)}')

    print('Elapsed time: {}s'.format(f.deltasec(start, timer())))

def fix_dls_all_units(d_lower=None):
    if d_lower is None:
        d_lower = dt.now() + delta(days=-30)

    units = utl.all_units()
    
    result = Parallel(n_jobs=-1, verbose=11)(delayed(utl.process_files)(
        ftype='dsc',
        units=unit,
        d_lower=d_lower) for unit in units)

def date_from_dsc(p : Path) -> dt:
    """Parse date from dsc folder name, eg 328_dsc_20180526-072028
    - if no dsc, use date created"""
    try:
        sdate = p.name.split('_dsc_')[-1].split('-')[0]
        d = dt.strptime(sdate, '%Y%m%d')
    except:
        d = fl.date_created(p)
    
    return d

def get_recent_dsc_single(p_unit=None, d_lower=dt(2020,1,1), unit=None):
    """Return list of most recent dsc folder from each unit\n
    TODO fix this to use get_list

    Parameters
    ----------
    p_unit : Path, optional
        default None\n
    d_lower : datetime, optional,
        limit search by date, default dt(2020,1,1)\n
    unit : str, optional

    Returns
    -------
    list
    """
    df = pd.DataFrame
    lst = []
    if p_unit is None:
        p_unit = efl.UnitFolder(unit=unit).p_unit

    p_dls = p_unit / 'Downloads'
    lst_unit = recurse_dsc(p_search=p_dls, maxdepth=3, d_lower=d_lower)
    
    if lst_unit:
        lst_unit.sort(key=lambda p: date_from_dsc(p), reverse=True)
        lst.append(lst_unit[0])
    
    return lst

def get_recent_dsc_all(d_lower=dt(2020,1,1)):
    """Return list of most recent dsc folders for all units"""
    p_units = utl.get_unitpaths()
    lst = []
    
    for p_unit in p_units:
        lst.extend(get_recent_dsc_single(p_unit=p_unit, d_lower=d_lower))

    return lst

def move_tr3(p):
    unit = utl.unit_from_path(p) # assuming in unit folder

    p_dst_base = Path('/Users/Jayme/OneDrive/SMS Equipment/Share/tr3 export')
    p_dst = p_dst_base / f'{unit}/{p.name}'

    fl.copy_file(p_src=p, p_dst=p_dst)

def check_parents(p : Path, depth : int, names : list) -> bool:
    """Check path to make sure parents aren't top level folders

    Parameters
    ----------
    p : Path
        Path to check\n
    depth : int
        From start of folder path to this folder level\n
    names : list
        Names to check

    Returns
    -------
    bool
        If path checked is top level folder
    """
    names = [n.lower() for n in names]

    for parent in list(p.parents)[:depth]:
        if parent.name.lower() in names:
            return True
    
    return False

def zip_recent_dls(units, d_lower=dt(2020,1,1)):
    # get most recent dsc from list of units and zip parent folder for attaching to TSI
    if not isinstance(units, list): units = [units]
    lst = []
    for unit in units:
        lst.extend(get_recent_dsc_single(unit=unit, d_lower=d_lower))
        
    lst_zip = [fl.zip_folder(p=p.parent, delete=False, calculate_size=True) for p in lst]

    return lst_zip

# STATS csv
def stats_from_dsc(p):
    # get stats file path from dsc path
    try:
        return list(Path(p/'stats').glob('SERIAL*csv'))[0]
    except:
        return None
        print(f'Couldn\'t read stats: {p}')

def import_stats(lst=None):
    # use list of most recent dsc and combine into dataframe

    if lst is None:
        lst = get_recent_dsc_all(d_lower=dt(2020,1,1))

    df = pd.concat([get_stats(stats_from_dsc(p)) for p in lst])

    return df

def get_stats(p):
    # read stats csv and convert to single row df, to be combined
    cols = ['Unit', 'Today\'s date / time', 'PSC code version', 'TCI code version', 'FB187 Serial Number', 'FB187/197 Serial Number', 'Inv 1 Serial number', 'Inv 2 Serial number']

    # dict to convert messy to nice names
    m = {
        'Unit': 'Unit',
        'Today\'s date / time': 'Timestamp',
        'PSC code version': 'PSC ver',
        'TCI code version': 'TSC ver',
        'FB187 Serial Number': 'FB187/197 SN',
        'FB187/197 Serial Number': 'FB187/197 SN',
        'Inv 1 Serial number': 'Inv 1 SN',
        'Inv 2 Serial number': 'Inv 2 SN'}

    cols = list(m.keys())

    try:
        df = pd.read_csv(p, index_col=0)
        df = df[df.iloc[:,0].isin(cols[1:])] # exclude unit from find cols
        df['Unit'] = utl.unit_from_path(p)

        df = df.pivot(index='Unit', columns=df.columns[0], values=df.columns[1])
        df.rename_axis('Unit', inplace=True, axis=1)
        df.reset_index(inplace=True)

        df.columns = [m[col] for col in df.columns] # rename to nice cols
        df = df[list(OrderedDict.fromkeys(m.values()))] # reorder, keeping original
        df.Timestamp = pd.to_datetime(df.Timestamp)
    except:
        print(f'Error getting stats: {p}')
        df = pd.DataFrame()

    return df
