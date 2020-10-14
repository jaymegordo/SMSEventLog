from . import dls, faults, plm
from .__init__ import *

log = getlog(__name__)

"""Helper funcs to import external data, used by all other modules in /data/internal"""

def get_config():
    return {
        'fault': dict(
            exclude=['dsc', 'dnevent', 'sfevent'],
            duplicate_cols=['unit', 'code', 'time_from'],
            imptable='FaultImport',
            impfunc='ImportFaults',
            read_func=faults.read_fault),
        'haul': dict(
            exclude=['dsc', 'chk', 'pictures', 'dnevent', 'sfevent'],
            duplicate_cols=['unit', 'datetime'],
            imptable='PLMImport',
            impfunc='ImportPLM',
            read_func=plm.read_haul),
        'dsc': dict(
            exclude=[]),
        'tr3': dict(
            exclude=['dsc', 'chk', 'CHK', 'Pictures'])}

def combine_csv(lst_csv, ftype, d_lower=None):
    # combine list of csvs into single and drop duplicates, based on duplicate cols
    # func = getattr(sys.modules[__name__], f'read_{ftype}')
    func = get_config()[ftype].get('read_func')

    # multiprocess reading/parsing single csvs
    dfs = Parallel(n_jobs=-1, verbose=11, prefer='threads')(delayed(func)(csv) for csv in lst_csv)

    df = pd.concat([df for df in dfs], sort=False) \
        .drop_duplicates(subset=get_config()[ftype]['duplicate_cols'])

    # drop old records before importing
    if not d_lower is None:
        df = df[df.datetime >= d_lower]

    return df

def to_seconds(t):
    x = time.strptime(t, '%H:%M:%S')
    return int(delta(hours=x.tm_hour, minutes=x.tm_min, seconds=x.tm_sec).total_seconds())

def get_unitpaths(minesite='FortHills', model_base='980E'):
    # TODO change this to work with other sites
    p = f.drive / f.config['UnitPaths'][minesite][model_base]
    return [x for x in p.iterdir() if x.is_dir() and 'F3' in x.name]

def all_units(rng=None):
    """Return list of FH ONLY unit names 
    - TODO make this all minesites
    
    Returns
    ---
        list
        - eg ['F301', 'F302'...]
    """
    if rng is None:
        rng = (300, 348)
    return [f'F{n}' for n in range(*rng)]

def unit_from_path(p):
    parentname = '1. 980E Trucks'

    for i, val in enumerate(p.parts):
        if val == parentname:
            return p.parts[i + 1].split(' - ')[0]
    
    return None

def recurse_folders(p_search, d_lower=dt(2016, 1, 1), depth=0, maxdepth=5, ftype='haul', exclude=[]):
    # recurse and find fault/haulcycle csv files
    lst = []

    # haul files only need to check date created
    # date_func_name = 'date_created' #if ftype == 'haul' else 'date_modified'
    # date_func = getattr(sys.modules[__name__], date_func_name)

    if depth == 0 and ftype == 'tr3':
        # this is sketch, but need to find files in top level dir too
        lst.extend([f for f in p_search.glob(f'*.tr3')])

    if depth <= maxdepth:
        for p in p_search.iterdir():
            if p.is_dir():
                if ftype in ('fault', 'haul'):
                    lst.extend([f for f in p.glob(f'*{ftype}*.csv') if fl.date_created(f) > d_lower])
                elif ftype == 'tr3':
                    lst.extend([f for f in p.glob(f'*.tr3') if fl.date_created(f) > d_lower])

                # exclude vhms folders (8 digits) from haul file search
                if (not (any(s in p.name.lower() for s in exclude)
                        or (ftype=='haul' and len(p.name) == 8 and p.name.isdigit()))
                    and fl.date_modified(p) > d_lower):
                    
                    lst.extend(recurse_folders(
                        p_search=p,
                        depth=depth + 1,
                        maxdepth=maxdepth,
                        d_lower=d_lower,
                        ftype=ftype,
                        exclude=exclude))

    return lst

def process_files(ftype, units=[], search_folders=['downloads'], d_lower=dt(2020,1,1), maxdepth=4, import_=True):
    """Top level control function - pass in single unit or list of units
        1. Get list of files (haul, fault, dsc)
        2. Process - import haul/fault or 'fix' dsc eg downloads folder structure"""
    
    if ftype == 'tr3': search_folders.append('vibe tests') # bit sketch

    if not units: # assume ALL units # TODO: make this work for all minesites?
        units = all_units()
    elif not isinstance(units, list):
        units = [units]

    search_folders = list(map(lambda x: x.lower(), search_folders))

    lst = []
    config = get_config()[ftype]

    for unit in units:
        if not fl.drive_exists(): return
        p_unit = efl.UnitFolder(unit=unit).p_unit
        lst_search = [x for x in p_unit.iterdir() if x.is_dir() and x.name.lower() in search_folders] # start at downloads

        # could search more than just downloads folder (eg event too)
        for p_search in lst_search:
            lst.extend(get_list_files(ftype=ftype, p_search=p_search, d_lower=d_lower, maxdepth=maxdepth))

        # process all dsc folders per unit as we find them
        if ftype == 'dsc':
            print(f'\n\nProcessing dsc, unit: {unit}\ndsc folders found: {len(lst)}')
            Parallel(n_jobs=-1, verbose=11)(delayed(dls.fix_dsc)(p=p, p_unit=p_unit, zip_=True) for p in lst)

            lst = [] # need to reset list, only for dsc, this is a bit sketch
        elif ftype == 'tr3':
            for p in lst: dls.move_tr3(p=p)
            lst = []

    # collect all csv files for all units first, then import together
    if ftype in ('haul', 'fault'):
        print(f'num files: {len(lst)}')
        if lst:
            df = combine_csv(lst_csv=lst, ftype=ftype, d_lower=d_lower)
            # print(f'rows in df: {len(df)}')
            if import_:
                rowsadded = db.import_df(df=df, imptable=config['imptable'], impfunc=config['impfunc'], prnt=True, notification=False)
                return rowsadded
            else:
                return df
        else:
            return pd.DataFrame() # return blank dataframe

def get_list_files(ftype, p_search, d_lower=dt(2020,1,1), maxdepth=4):
    # return list of haulcycle, fault, tr3, or dsc files/folders
    print(p_search)
    
    lst = []
    # recurse and find all other folders inside
    if ftype in ('haul', 'fault', 'tr3'):
        lst = recurse_folders(p_search=p_search, maxdepth=maxdepth, d_lower=d_lower, exclude=get_config()[ftype]['exclude'], ftype=ftype)
    elif ftype == 'dsc':
        lst = dls.recurse_dsc(p_search=p_search, maxdepth=maxdepth, d_lower=d_lower)
    
    unit = unit_from_path(p=p_search)
    print(f'fType: {ftype}, Unit: {unit}, files: {len(lst)}')
    
    return lst

def write_import_fail(msg):
    if not sys.platform == 'darwin': return
    failpath = Path().home() / 'Desktop/importfail.txt'
    with open(failpath, 'a') as f:
        f.write(f'{msg}\n')
