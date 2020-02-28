import os
import shutil
import subprocess
import time
from datetime import datetime as date
from datetime import timedelta as delta
from pathlib import Path

import pandas as pd

import functions as f
from database import db


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
    return date.fromtimestamp(t) + delta(seconds=tz)

def toSeconds(t):
    x = time.strptime(t, '%H:%M:%S')
    return int(delta(hours=x.tm_hour, minutes=x.tm_min, seconds=x.tm_sec).total_seconds())


# FOLDERS
def unitfolders():
    p = Path(f.config['FilePaths']['980E FH'])
    return [x for x in p.iterdir() if x.is_dir() and 'F3' in x.name]

def recursefolders(searchfolder, exclude, tslower=None, ftype='haul'):
    lst = []
    if tslower is None: tslower = date(2016, 1, 1).timestamp()
    # if tsupper is None: tsupper = date.now().timestamp()

    # p is Path object
    for p in searchfolder.iterdir():
        if p.is_dir():
            lst.extend([f for f in p.glob(f'*{ftype}*.csv')])

            if (not (any(s in p.name for s in exclude)
                    or (ftype=='haul' and len(p.name) == 8 and p.name.isdigit()))
                and p.stat().st_mtime > tslower):
                
                lst.extend(recursefolders(p, exclude, tslower=tslower, ftype=ftype))

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
    tslower = date(2017, 1, 1).timestamp()

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
        files.extend(recursefolders(p, exclude, tslower=tslower, ftype=ftype))
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
    tslower = date(2019, 9, 1).timestamp()
    
    for p in folders:
        files.extend(recursefolders(p, exclude, tslower))
    
    return files

def what():
    # not used
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
    print(f'+ {directory}')
    for path in sorted(directory.rglob('*')):
        depth = len(path.relative_to(directory).parts)
        spacer = '    ' * depth
        print(f'{spacer}+ {path.name}')
