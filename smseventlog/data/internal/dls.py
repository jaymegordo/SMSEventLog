from collections import OrderedDict
from zipfile import ZipFile
from tarfile import TarFile

from pandas.core.algorithms import isin

from . import utils as utl
from .__init__ import *

log = getlog(__name__)

dsc_exclude = ['fr', 'data', 'dnevent', 'sfevent', 'chk', 'plm', 'vhms', 'pic', 'events', 'stats', 'system']

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
    """Recurse and find any file/folder paths containing 'dsc'
    - Sometimes dsc folder are renamed to 'GE'
    """
    lst = []
    # print(p_search)
    
    for p in p_search.iterdir():
        # 'dsc' is always a dir or zipped dir
        # this is ~2x faster if we didn't have to check all filenames (eg for .zip)
        name = p.name.lower()

        if 'dsc' in name or name == 'ge':
            lst.append(p) # end recursion
        elif (
            p.is_dir() and
            fl.date_modified(p) > d_lower and
            not any(exclude in name for exclude in dsc_exclude) and
            not re.match(r'^a\d{5}$', name)):
            # ^ exclude SN folders

            if depth < maxdepth:
                lst.extend(recurse_dsc(
                    p_search=p,
                    depth=depth + 1,
                    maxdepth=maxdepth,
                    d_lower=d_lower))
    
    return lst

@er.errlog(msg='Couldn\'t find recent dls folder.', err=False)
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
    if not p_dls.exists():
        log.warning(f'Download folder doesn\'t exist: {p_dls}')
        return

    # get all downloads/year folders
    lst_year = [p for p in p_dls.iterdir() if p.is_dir() and is_year(p.name)]

    if not lst_year:
        log.warning('No download year folders found.')
        return

    # sort year folders by name, newest first, select first
    lst_year_sorted = sorted(lst_year, key=lambda p: p.name, reverse=True) # sort by year
    p_year = lst_year_sorted[0]

    # sort all dls folders on date from folder title
    lst_dls = [p for p in p_year.iterdir() if p.is_dir()]
    lst_dls_sorted = sorted(filter(lambda p: date_from_title(p.name) is not None, lst_dls), key=lambda p: date_from_title(p.name), reverse=True)
    return lst_dls_sorted[0]

def zip_recent_dls_unit(unit :str, _zip=True) -> Path:
    """Func for gui to find (optional zip) most recent dls folder by parsing date in folder title"""
    from ...gui.dialogs import msg_simple, msgbox
    from ...gui import _global as gbl

    p_dls = get_recent_dls_unit(unit=unit)

    if not p_dls is None:
        msg = f'Found DLS folder: {p_dls.name}, calculating size...'
        gbl.update_statusbar(msg)
        gbl.get_mainwindow().app.processEvents()

        size = fl.calc_size(p_dls)
        msg = f'Found DLS folder:\n\n{p_dls.name}\n{size}\n\nZip now?'
        if not msgbox(msg=msg, yesno=True): return
    else:
        msg = f'Couldn\'t find recent DLS folder, check folder structure for issues.'
        msg_simple(msg=msg, icon='warning')
        return

    if _zip:
        p_zip = fl.zip_folder(p=p_dls, delete=False)
        return p_zip
    else:
        return p_dls

def fix_dsc(p : Path, zip_=False):
    """Process/fix single dsc/dls folder"""
    start = timer()
    unit = utl.unit_from_path(p)
    uf = efl.UnitFolder(unit=unit)
    # unit = p_unit.name.split(' - ')[0]

    p_parent = p.parent
    d = date_from_dsc(p=p)

    # rename dls folder: UUU - YYYY-MM-DD - DLS
    newname = '{} - {} - DLS'.format(unit, d.strftime('%Y-%m-%d'))

    p_new = uf.p_dls / f'{d.year}/{newname}'

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

def get_recent_dsc_single(unit, d_lower=dt(2020,1,1), year=None, all_files=False, ftype: str='dls', maxdepth=3):
    """Return list of most recent dsc folder from each unit
    - OR most recent fault... could extend this for any filetype

    Parameters
    ----------
    d_lower : datetime, optional,
        limit search by date, default dt(2020,1,1)
    unit : str, optional
    all_files: bool
        return dict of unit: list of all sorted files

    Returns
    -------
    list | dict
    """
    lst = []
    uf = efl.UnitFolder(unit=unit)

    p_dls = uf.p_dls

    if not year is None:
        p_year = p_dls / year
        if p_year.exists():
            p_dls = p_year

    if ftype == 'dls':
        lst_unit = recurse_dsc(p_search=p_dls, maxdepth=maxdepth, d_lower=d_lower)

    elif ftype == 'fault':
        lst_unit = utl.recurse_folders(
            p_search=p_dls,
            d_lower=d_lower,
            ftype=ftype,
            maxdepth=maxdepth,
            exclude=utl.get_config()[ftype]['exclude'])
    
    if lst_unit:
        lst_unit.sort(key=lambda p: date_from_dsc(p), reverse=True)

        if not all_files:
            lst.append(lst_unit[0])
        else:
            lst.extend(lst_unit)
    
    return lst

def get_recent_dsc_all(minesite='FortHills', model='980E', all_files=True, **kw):
    """Return list of most recent dsc folders for all units"""
    lst = []

    # keep all files to try and import next most recent if file fails
    if all_files:
        lst = {}

    units = db.unique_units(minesite=minesite, model=model)
    
    for unit in tqdm(units):
        recent_dsc = get_recent_dsc_single(unit=unit, all_files=all_files, **kw)

        if not recent_dsc:
            print(f'\n\nNo recent dsc for: {unit}')

        if not all_files:
            lst.extend(recent_dsc)
        else:
            lst[unit] = recent_dsc

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
    if p.is_dir():
        try:
            return list((p / 'stats').glob('SERIAL*csv'))[0]
        except:
            return None
            print(f'Couldn\'t read stats: {p}')
    elif p.suffix == '.zip':
        return ZipFile(p)
    elif p.suffix == '.tar':
        return TarFile(p)

def import_stats(lst=None, d_lower=dt(2021,1,1)):
    # use list of most recent dsc and combine into dataframe

    if lst is None:
        lst = get_recent_dsc_all(d_lower=d_lower)
    
    if isinstance(lst, dict):
        dfs = []
        for unit, lst_csv in tqdm(lst.items()):

            # try to find/load csv, or move to next if fail
            for p in lst_csv:
                try:
                    p_csv = stats_from_dsc(p)
                    df_single = get_stats(p=p_csv)
                    dfs.append(df_single)
                    break
                except Exception as e:
                    log.warning(f'Failed to load csv: {p}, \n{str(e)}')

        df = pd.concat(dfs)

    else:
        df = pd.concat([get_stats(stats_from_dsc(p)) for p in lst])

    return df

def get_list_stats(unit):
    """Return list of STATS csvs for specific unit"""
    from ...eventfolders import UnitFolder
    uf = UnitFolder(unit=unit)

    p_dls = uf.p_dls

    return p_dls.glob('SERIAL*csv')

def smr_from_stats(lst):

    return pd.concat([get_stats(p) for p in lst])

def get_stats(p, all_cols=False):
    """
    Read stats csv and convert to single row df of timestamp, psc/tsc versions + inv SNs, to be combined
    Can read zip or tarfiles"""

    # dsc folder could be zipped, just read zipped csv, easy!
    # super not dry
    # print(p)
    if isinstance(p, ZipFile):
        zf = p
        p = Path(zf.filename)
        csv = [str(file.filename) for file in zf.filelist if re.search(r'serial.*csv', str(file), flags=re.IGNORECASE)][0]
        with zf.open(csv) as reader:
            df = pd.read_csv(reader, index_col=0)

    elif isinstance(p, TarFile):
        tf = p
        p = Path(tf.name)
        csv = [file for file in tf.getnames() if re.search(r'serial.*csv', file, flags=re.IGNORECASE)][0]
        df = pd.read_csv(tf.extractfile(csv), index_col=0)

    else:
        df = pd.read_csv(p, index_col=0)
    
    df = df \
        .applymap(lambda x: str(x).strip())

    # need to keep original order after pivot
    orig_cols = df[df.columns[0]].unique().tolist()
    
    df = df \
        .assign(unit=utl.unit_from_path(p)) \
        .pipe(lambda df: df.drop_duplicates(subset=df.columns[0], keep='first')) \
        .pipe(lambda df: df.pivot(index='unit', columns=df.columns[0], values=df.columns[1])) \
        [orig_cols] \
        .pipe(lambda df: df[[col for col in df.columns if not '-' in col]]) \
        .pipe(f.lower_cols) \
        .assign(todays_date_time=lambda x: pd.to_datetime(x.todays_date_time).dt.date) \
        .rename_axis('', axis=1)

    # shorten column names
    m_rename = dict(
        serial_number='sn',
        number='no',
        code_version='ver',
        version='ver',
        hours='hrs',
        inverter='inv')
    
    # need to loop instead of dict comp so can update multiple times
    rename_cols = {}
    for col in df.columns:
        orig_col = col
        for orig, new in m_rename.items():
            if orig in col:
                col = col.replace(orig, new)
        
        rename_cols[orig_col] = col

    rename_cols.update({
        'todays_date_time': 'date',
        'total_hours': 'engine_hrs',
        'model++': 'wm_model'})

    drop_cols = [
        'unit',
        'truck_identification',
        'end',
        'model',
        'model+',
        'model+++',
        'mine_dos_filename',
        'oem_dos_filename',
        'ge_dos_filename']

    df = df \
        .rename(columns=rename_cols) \
        .drop(columns=drop_cols) \
        .rename(columns=dict(truck_model='model'))
        # .assign(truck_model=lambda x: x.truck_model.str.replace("'", '')) \ # keep ' for excel model

    # df = df[list(OrderedDict.fromkeys(m.values()))] # reorder, keeping original

    return df
