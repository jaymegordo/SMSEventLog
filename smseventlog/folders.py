from collections import OrderedDict
import os
import sys
import shutil
import subprocess
import time
from distutils import dir_util
from datetime import (datetime as dt, timedelta as delta)
from pathlib import Path
from timeit import default_timer as timer

import pandas as pd
from hurry.filesize import size

from . import (
    functions as f)
from .database import db


def import_haul(files):
    units = [f'F{n}' for n in range(300, 348)]

    for unit in units:
        lst = list(filter(lambda p: p.parts[4].split(' - ')[0] == unit, files))

        if lst:
            print(f'Starting: {unit}, files: {len(lst)}')

            df = combine_df(lst, ftype='haul')
            print(f'df: {len(df)}, max: {df.datetime.max()}, min: {df.datetime.min()}')

            df.to_sql(name='PLMImport', con=db.get_engine(), if_exists='append')

            print(unit)

    rows = db.cursor.execute('ImportPLM').rowcount
    db.cursor.commit()
    print(f'Rows imported to PLM table: {rows}')

def import_fault(files):
    if not isinstance(files, list): files = [files]

    df = combine_df(lst=files, ftype='fault')
    df.to_sql(name='FaultImport', con=db.get_engine(), if_exists='append', index=False)

    rows = db.cursor.execute('ImportFaults').rowcount
    db.cursor.commit()
    print(f'Rows imported to fault table: {rows}')

def combine_df(lst, ftype):    
    if ftype == 'haul':
        df = pd.concat([read_haul(p=p) for p in lst], sort=False)
        subset = ['unit', 'datetime']
    elif ftype == 'fault':
        df = pd.concat([read_fault(p=p) for p in lst], sort=False)
        subset = ['unit', 'code', 'time_from']

    df.drop_duplicates(subset=subset, inplace=True)
    return df

def read_fault(p):
    newcols = ['unit', 'code', 'time_from', 'time_to', 'faultcount', 'message']
    # need to handle minesites other than forthills

    try:
        # read header to get serial
        serial = pd.read_csv(p, skiprows=4, nrows=1, header=None)[1][0]
        unit = db.getUnit(serial=serial, minesite='FortHills')

        df = pd.read_csv(p, header=None, skiprows=28, usecols=(0, 1, 3, 5, 7, 8))
        df.columns = newcols
        df.unit = unit
        df.code = df.code.str.replace('#', '')
        df.time_from = df.time_from.apply(parse_fault_time)
        df.time_to = df.time_to.apply(parse_fault_time)
        
        return df
    except:
        print(f'Failed: {str(p)}')
        return pd.DataFrame(columns=newcols)

def read_haul(p):
    # load single haulcycle file to dataframe

    cols = ['Date', 'Time', 'Payload(Net)', 'Swingloads', 'Status Flag', 'Carry Back', 'TotalCycle Time', 'L-Haul Distance', 'L-Max Speed', 'E MaxSpeed', 'Max Sprung', 'Truck Type', 'Tare Sprung Weight', 'Payload Est.@Shovel(Net)', 'Quick Payload Estimate(Net)', 'Gross Payload']

    newcols = ['datetime', 'payload', 'swingloads', 'statusflag', 'carryback', 'cycletime', 'l_hauldistance', 'l_maxspeed', 'e_maxspeed', 'maxsprung', 'trucktype', 'sprungweight', 'payload_est', 'payload_quick', 'payload_gross']

    try:
        # header, try unit, then try getting unit with serial
        df_head = pd.read_csv(p, nrows=6, header=None)
        unit = df_head[0][1].split(':')[1].strip().upper().replace('O','0').replace('F-','F').replace('F0','F')
        if unit == '':
            serial = df_head[0][0].split(':')[1].strip().upper()
            unit = db.getUnit(serial=serial)

        df = pd.read_csv(p, header=8, usecols=cols, parse_dates=[['Date', 'Time']])[:-2]
        df.columns = newcols
        df.insert(0, 'unit', unit)
        df.datetime = pd.to_datetime(df.datetime, format='%m/%d/%y %H:%M:%S')
        df.cycletime = df.cycletime.apply(toSeconds)
        df.carryback = df.carryback.str.replace(' ', '').astype(float)    
        return df
    except:
        print(f'Failed: {str(p)}')
        write_import_fail(p)
        return pd.DataFrame(columns=newcols)

def parse_fault_time(tstr):
    arr = tstr.split('|')
    t, tz = int(arr[0]), int(arr[1])
    return dt.fromtimestamp(t) + delta(seconds=tz)

def toSeconds(t):
    x = time.strptime(t, '%H:%M:%S')
    return int(delta(hours=x.tm_hour, minutes=x.tm_min, seconds=x.tm_sec).total_seconds())

def unit_from_path(p):
    parentname = '1. 980E Trucks'

    for i, val in enumerate(p.parts):
        if val == parentname:
            return p.parts[i + 1].split(' - ')[0]
    
    return None


# STATS csv
def stats_from_dsc(p):
    # get stats file path from dsc path
    try:
        return list(Path(p/'stats').glob('SERIAL*csv'))[0]
    except:
        return None
        print(f'Couldn\'t read stats: {str(p)}')

def import_stats(lst=None):
    # use list of most recent dsc and combine into dataframe

    if lst is None:
        lst = get_recent_dsc(d_lower=dt(2020,1,1))

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
        df['Unit'] = unit_from_path(p)

        df = df.pivot(index='Unit', columns=df.columns[0], values=df.columns[1])
        df.rename_axis('Unit', inplace=True, axis=1)
        df.reset_index(inplace=True)

        df.columns = [m[col] for col in df.columns] # rename to nice cols
        df = df[list(OrderedDict.fromkeys(m.values()))] # reorder, keeping original
        df.Timestamp = pd.to_datetime(df.Timestamp)
    except:
        print(f'Error getting stats: {str(p)}')
        df = pd.DataFrame()

    return df

# FOLDERS
def unitfolders():
    p = Path(f.drive + f.config['FilePaths']['980E FH'])
    return [x for x in p.iterdir() if x.is_dir() and 'F3' in x.name]

def recurse_folders(searchfolder, exclude, d_lower=dt(2016, 1, 1), ftype='haul'):
    lst = []
    # if d_lower is None: d_lower = dt(2016, 1, 1).timestamp()
    # if tsupper is None: tsupper = dt.now().timestamp()

    # p is Path object
    for p in searchfolder.iterdir():
        if p.is_dir():
            lst.extend([f for f in p.glob(f'*{ftype}*.csv')])

            if (not (any(s in p.name for s in exclude)
                    or (ftype=='haul' and len(p.name) == 8 and p.name.isdigit()))
                and date_modified(p) > d_lower):
                
                lst.extend(recurse_folders(p, exclude, d_lower=d_lower, ftype=ftype))

    return lst

def check_parents(p, depth, names):
    # check path to make sure parents aren't top level folders
    names = [n.lower() for n in names]

    for parent in list(p.parents)[:depth]:
        if parent.name.lower() in names:
            return True
    
    return False
        
def date_created(p):
    # get date from folder date created (platform dependent)
    st = p.stat()
    ts = st.st_ctime if sys.platform.startswith('win') else st.st_birthtime
    
    return dt.fromtimestamp(ts)

def date_modified(p):
    return dt.fromtimestamp(p.stat().st_mtime)

def copy_folder(p_src, p_dst):
    # copy folder or file
    try:
        if p_src.exists() and not p_src == p_dst:
            print(f'\nsource: {p_src}')
            print(f'dest: {p_dst}')
            src, dst = str(p_src), str(p_dst)

            # if dest folder already exists, need to copy then remove
            if p_dst.exists() and p_src.is_dir():
                dir_util.copy_tree(src, dst)
                shutil.rmtree(src)
            else:
                shutil.move(src, dst)
    except:
        print(f'Error copying folder: {str(p_src)}')

def zip_folder(p, delete=False, calculate_size=False, p_new=None):
    # zips target folder in place, optional delete original
    
    # zip folder into a new target dir    
    p_dst = p if p_new is None else p_new

    try:
        if p.exists():
            p_new = shutil.make_archive(
                base_name=str(p_dst),
                base_dir=str(p.name),
                root_dir=str(p.parent),
                format='zip')

            # print file size compression savings
            if calculate_size:
                size_pre = sum(f.stat().st_size for f in p.glob('**/*') if f.is_file())
                size_post = sum(f.stat().st_size for f in p_dst.parent.glob('*.zip'))
                size_pct = size_post / size_pre
                print(f'Reduced size to: {size_pct:.1%}\nPre: {size(size_pre)}\nPost: {size(size_post)}')
            
            if delete:
                shutil.rmtree(p)
    except:
        print(f'Error zipping folder: {str(p)}')
    
    return Path(p_new)


# DSC
def date_from_dsc(p):
    # parse date from dsc folder name, eg 328_dsc_20180526-072028
    # if no dsc, use date created
    try:
        sdate = p.name.split('_dsc_')[-1].split('-')[0]
        d = dt.strptime(sdate, '%Y%m%d')
    except:
        d = date_created(p)
    
    return d

def get_recent_dsc(d_lower=dt(2020,1,1)):
    # return list of most recent dsc folder from each unit
    # pass in d_lower to limit search
    p_units = unitfolders()
    lst = []
    
    for p_unit in p_units:
        p_dls = p_unit / 'Downloads'
        lst_unit = recurse_dsc(p_search=p_dls, maxdepth=3, d_lower=d_lower)
        
        if lst_unit:
            lst_unit.sort(key=lambda p: date_from_dsc(p), reverse=True)
            lst.append(lst_unit[0])

    return lst

def fix_dsc(p, p_unit, zip_=False):
    start = timer()
    unit = p_unit.name.split(' - ')[0]

    p_parent = p.parent
    print(p)
    print(p_parent.name)

    d = date_from_dsc(p=p)

    # rename dls folder: UUU - YYYY-MM-DD - DLS
    newname = '{} - {} - DLS'.format(unit, dt.strftime('%Y-%m-%d'))

    p_new = p_unit / f'Downloads/{dt.year}/{newname}'
    print(p_new)

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
    try:
        if zip_ and not str(p).endswith('.zip'):
            p_datapack = p / 'datapack'

            p_zip = zip_folder(
                p=p_datapack,
                delete=True,
                p_new=p_new / p.name / p_datapack.name,
                calculate_size=False)
            print(p_zip)

        copy_folder(p_src=p_src, p_dst=p_dst)
    except:
        print(f'Error fixing dsc folder: {str(p_src)}')

    print('Elapsed time: {}s'.format(f.deltasec(start, timer())))

def recurse_dsc(p_search, depth=0, maxdepth=5, d_lower=None):
    # return list of paths containing 'dsc'
    lst = []

    if depth <= maxdepth:
        for p in p_search.iterdir():
            if 'dsc' in p.name:
                lst.append(p) # end recursion
            elif (p.is_dir() and date_created(p) > d_lower):
                lst.extend(recurse_dsc(
                    p_search=p,
                    depth=depth + 1,
                    maxdepth=maxdepth,
                    d_lower=d_lower))
    
    return lst

def get_dsc(p_unit, maxdepth=3, d_lower=dt(2016,1,1)):
    # find all dsc folders in top level unit folder / downloads
    
    unit = p_unit.name.split(' - ')[0]
    p_dls = p_unit / 'Downloads'
    lst = recurse_dsc(p_search=p_dls, maxdepth=maxdepth, d_lower=d_lower)
    return lst


    
def scanfolders(ftype='haul'):
    if ftype == 'haul':
        folders = ['Downloads']
        exclude = ['dsc', 'chk', 'CHK', 'Pictures']
    elif ftype == 'fault':
        folders = ['Downloads']
        exclude = ['dsc']
    lst1 = unitfolders()
    lst2, files = [], []
    d_lower = dt(2017, 1, 1).timestamp()

    # write list of files to txt file on desktop
    # p = Path().home() / f'OneDrive/Desktop/{ftype}.txt'
    # with open(p, 'w') as f:
    #     for item in lst:
    #         f.write("%s\n" % item)

    # get specific toplevel folders within unit folders
    for p in lst1:
        lst2.extend([x for x in p.iterdir() if x.is_dir() and x.name in folders])

    # recurse and find all other folders inside
    # only return if folder contains csv files?
    for p in lst2:
        unit = p.parts[4].split(' - ')[0]
        files.extend(recurse_folders(p, exclude, d_lower=d_lower, ftype=ftype))
        print(f'Unit: {unit}, files: {len(files)}')
    
    return files

    # load csv with pd.read_csv, import to database
    # for p in lst3:
    #     df = combine_haul(p, unit=unit)

def write_import_fail(p):
    failpath = Path().home() / 'OneDrive/Desktop/importfail.txt'
    with open(failpath, 'a') as f:
        f.write(f'{p}\n')
    


# OTHER
def openfolder(p):
    subprocess.Popen(f'explorer {p}')

# ARCHIVE
def gethaulcycles():
    folders, files = [], []
    # one time function
    # folders.append(Path('P:/Fort Hills/02. Equipment Files/1. 980E Trucks/F301 - A40017/Downloads'))
    folders.append(Path('P:/Fort Hills/02. Equipment Files/1. 980E Trucks/F301 - A40017/Events'))

    exclude = ['dsc', 'chk', 'CHK', 'Pictures']
    d_lower = dt(2019, 9, 1).timestamp()
    
    for p in folders:
        files.extend(recurse_folders(p, exclude, d_lower))
    
    return files

def what():
    # not used
    newestdls = []
    units = ['F{}'.format(n) for n in range(300, 348)]

    basepath = 'P:\\Fort Hills\\02. Equipment Files\\1. 980E Trucks'
    units = [unit for unit in os.listdir(basepath) if 'F3' in unit]


    dlpaths = ['{}\\{}\\Downloads\\2019'.format(basepath, unit) for unit in units]
    dlpath = dlpaths[0]
    checkpaths = list(filter(lambda x: '.zip' not in x, os.listdir(dlpath)))
    checkpaths.sort(key=lambda x: os.path.getctime('{}\\{}'.format(dlpath,x)), reverse=True)
    for path in checkpaths:
        checkpath = '{}\\{}'.format(dlpath,path)
        print(checkpath, os.path.getctime(checkpath))


    haulcycles = list(filter(lambda x: 'haulcycle' in x, os.listdir(newestdls[0])))

    sourcepath = newestdls[0]
    destpath = 'C:\\Users\\jgordon\\Desktop\\PLM'
    unit = units[0]
    for haul in haulcycles:
        sourcefile = os.path.join(sourcepath, haul)
        destfile = os.path.join(destpath, haul)
        shutil.copyfile(sourcefile, destfile)


    for unit, sourcepath in zip(units, newestdls):
        if int(unit[1:]) < 322:
            continue

        try:
            destpath = 'C:\\Users\\jgordon\\Desktop\\PLM\\{}'.format(unit)
            haulcycles = list(filter(lambda x: 'haulcycle' in x, os.listdir(sourcepath)))

            for haul in haulcycles:
                sourcefile = os.path.join(sourcepath, haul)
                destfile = os.path.join(destpath, haul)
                shutil.copyfile(sourcefile, destfile)
            
            print('{}: {}'.format(unit, len(haulcycles)))
        except:
            f.senderror(prnt=True)

def tree(directory):
    # TODO: maybe move this to functions
    print(f'+ {directory}')
    for path in sorted(directory.rglob('*')):
        depth = len(path.relative_to(directory).parts)
        spacer = '    ' * depth
        print(f'{spacer}+ {path.name}')
