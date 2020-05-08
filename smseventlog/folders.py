import shutil
import subprocess
import time
from collections import OrderedDict
from distutils import dir_util
from timeit import default_timer as timer

import pandas as pd
from hurry.filesize import size

from . import functions as f
from .__init__ import *
from .database import db
from .gui import dialogs as dlgs

log = logging.getLogger(__name__)

def get_config():
    return {
        'fault': dict(
            exclude=['dsc'],
            duplicate_cols=['unit', 'code', 'time_from'],
            imptable='FaultImport',
            impfunc='ImportFaults'),
        'haul': dict(
            exclude=['dsc', 'chk', 'CHK', 'Pictures'],
            duplicate_cols=['unit', 'datetime'],
            imptable='PLMImport',
            impfunc='ImportPLM'),
        'dsc': dict(
            exclude=[]),
        'tr3': dict(
            exclude=['dsc', 'chk', 'CHK', 'Pictures'])}

class EventFolder(object):
    def __init__(self, e):
        self.dt_format = '%Y-%m-%d'

        f.copy_model_attrs(model=e, target=self)

        # get unit's row from unit table, save to self attributes
        m = db.get_df_unit().loc[self.unit]
        f.copy_dict_attrs(m=m, target=self)

        self.set_modelpath() # just needs model and minesite
        self.year = self.dateadded.year

        wo_blank = 'WO' + ' ' * 14
        if not self.workorder:
            self.workorder = wo_blank

        # confirm unit, date, title exist?
        self.folder_title = self.get_folder_title(self.unit, self.dateadded, self.workorder, self.title)

        unitpath = f'{self.unit} - {self.serial}'

        # TODO: need to get basepaths from db based on minesite
            # create FilePaths table in db
            # FortHills - 'Fort Hills/ 02. Equipment Files'
        self.p_base = f.drive / f'{self.get_basepath()}/{self.modelpath}/{unitpath}/events/{self.year}'
        self.p_event = self.p_base / self.folder_title
        self.p_event_blank = self.p_base / self.get_folder_title(self.unit, self.dateadded, wo_blank, self.title)

    def get_basepath(self):
        return f'Fort Hills/02. Equipment Files'

    def get_folder_title(self, unit, d, wo, title):
        d_str = d.strftime(self.dt_format)
        return f'{unit} - {d_str} - {wo} - {title}'

    def show(self):
        if not drive_exists():
            return
            
        p = self.p_event
        p_blank = self.p_event_blank

        if not p.exists():
            if p_blank.exists():
                # if wo_blank stills exists but event now has a WO, automatically rename
                move_folder(p_src=p_blank, p_dst=p)
            else:
                # show folder picker dialog
                msg = f'Can\'t find folder:\n\'{p.name}\'\n\nWould you like to link it?'
                if dlgs.msgbox(msg=msg, yesno=True):
                    p_old = dlgs.get_filepath_from_dialog(p_start=p.parent)
                    
                    # if user selected a folder
                    if p_old:
                        move_folder(p_src=p_old, p_dst=p)
                    
                if not p.exists():
                    # if user declined to create OR failed to chose a folder, ask to create
                    msg = f'Folder:\n\'{p.name}\' \n\ndoesn\'t exist, create now?'
                    if dlgs.msgbox(msg=msg, yesno=True):
                        self.create_folder()
        
        if p.exists():
            open_folder(p=p, check_drive=False)
    
    def create_folder(self, show=True, ask_show=False):
        if not drive_exists():
            return
            
        try:
            p = self.p_event
            p_pics = p / 'Pictures'
            p_dls = p / 'Downloads'

            if not p.exists():
                p_pics.mkdir(parents=True)
                p_dls.mkdir(parents=True)

                if ask_show:
                    msg = 'Event folder created. Would you like to open?'
                    if dlgs.msgbox(msg=msg, yesno=True):
                        self.show()
                elif show:
                    self.show()
        except:
            msg = 'Can\'t create folder!'
            dlgs.msg_simple(msg=msg, icon='critical')
            log.error(msg)

    def set_modelpath(self):
        model = self.model
        minesite = self.minesite

        # TODO: this is messy, need a better way to map vals
        if '930' in model:
            if minesite == 'BaseMine':
                v = '1. 930E'
            elif minesite == 'FortHills':
                v = '2. 930E Trucks'
        elif '980' in model:
            if minesite == 'BaseMine':
                v = '2. 980E'
            elif minesite == 'FortHills':
                v = '1. 980E Trucks'
        elif 'HD1500' in model:
            v = '3. HD1500'
        else:
            v = 'temp'
            
        self.modelpath = v
        

def combine_csv(lst_csv, ftype):
    # combine list of csvs into single and drop duplicates, based on duplicate cols
    func = getattr(sys.modules[__name__], f'read_{ftype}')

    df = pd.concat([func(p=p) for p in lst_csv], sort=False)
    df.drop_duplicates(subset=get_config()[ftype]['duplicate_cols'], inplace=True)
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
        print(f'Failed: {p}')
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
        print(f'Failed: {p}')
        write_import_fail(p)
        return pd.DataFrame(columns=newcols)

def parse_fault_time(tstr):
    arr = tstr.split('|')
    t, tz = int(arr[0]), int(arr[1])
    return dt.fromtimestamp(t) + delta(seconds=tz)

def toSeconds(t):
    x = time.strptime(t, '%H:%M:%S')
    return int(delta(hours=x.tm_hour, minutes=x.tm_min, seconds=x.tm_sec).total_seconds())


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
        df['Unit'] = unit_from_path(p)

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

# FOLDERS
def get_unitpaths():
    p = f.drive / f.config['FilePaths']['980E FH']
    return [x for x in p.iterdir() if x.is_dir() and 'F3' in x.name]

def unitpath_from_unit(unit, unitpaths=None):
    if unitpaths is None:
        unitpaths = get_unitpaths()

    return list(filter(lambda x: unit in str(x), unitpaths))[0]

def unit_from_path(p):
    parentname = '1. 980E Trucks'

    for i, val in enumerate(p.parts):
        if val == parentname:
            return p.parts[i + 1].split(' - ')[0]
    
    return None

def recurse_folders(p_search, d_lower=dt(2016, 1, 1), depth=0, maxdepth=5, ftype='haul', exclude=[]):
    # recurse and find fault/haulcycle csv files
    lst = []

    if depth == 0 and ftype == 'tr3':
        # this is sketch, but need to find files in top level dir too
        lst.extend([f for f in p_search.glob(f'*.tr3')])

    if depth <= maxdepth:
        for p in p_search.iterdir():
            if p.is_dir():
                if ftype in ('fault', 'haul'):
                    lst.extend([f for f in p.glob(f'*{ftype}*.csv')])
                elif ftype == 'tr3':
                    lst.extend([f for f in p.glob(f'*.tr3')])

                if (not (any(s in p.name for s in exclude)
                        or (ftype=='haul' and len(p.name) == 8 and p.name.isdigit()))
                    and date_modified(p) > d_lower):
                    
                    lst.extend(recurse_folders(
                        p_search=p,
                        depth=depth + 1,
                        maxdepth=maxdepth,
                        d_lower=d_lower,
                        ftype=ftype,
                        exclude=exclude))

    return lst

def recurse_dsc(p_search, d_lower=dt(2020,1,1), depth=0, maxdepth=5):
    # recurse and find any file/folder paths containing 'dsc'
    lst = []

    if depth <= maxdepth:
        for p in p_search.iterdir():
            if 'dsc' in p.name:
                lst.append(p) # end recursion
            elif (p.is_dir() and date_modified(p) > d_lower):
                lst.extend(recurse_dsc(
                    p_search=p,
                    depth=depth + 1,
                    maxdepth=maxdepth,
                    d_lower=d_lower))
    
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
    ts = st.st_ctime if f.is_win() else st.st_birthtime
    
    return dt.fromtimestamp(ts)

def date_modified(p):
    return dt.fromtimestamp(p.stat().st_mtime)

def move_folder(p_src, p_dst):
    # copy folder or file (more like a move/rename)
    try:
        if p_src.exists() and not p_src == p_dst:
            src, dst = str(p_src), str(p_dst)

            # if dest folder already exists, need to copy then remove
            if p_dst.exists() and p_src.is_dir():
                dir_util.copy_tree(src, dst)
                shutil.rmtree(src)
            else:
                shutil.move(src, dst)
    except:
        print(f'Error copying folder: {str(p_src)}')

def copy_file(p_src, p_dst):
    p = p_dst.parent
    if not p.exists():
        p.mkdir(parents=True)

    if not p_dst.exists():
        shutil.copyfile(str(p_src), str(p_dst))
    else:
        print(f'File already exists: {p_dst.name}')

def zip_folder(p, delete=False, calculate_size=False, p_new=None):
    # zips target folder in place, optional delete original
    
    # zip folder into a new target dir
    # if p_new is none, just zip in place
    p_dst = p if p_new is None else p_new

    try:
        if p.exists():
            p_zip = shutil.make_archive(
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
        print(f'Error zipping folder: {p}')
    
    return Path(p_zip)

def remove_files(lst):
    for p in lst:
        if p.exists():
            p.unlink()

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

def get_recent_dsc_single(p_unit=None, d_lower=dt(2020,1,1), unit=None):
    # return list of most recent dsc folder from each unit
    # pass in d_lower to limit search
    # TODO: fix this to use get_list
    lst = []
    if p_unit is None:
        p_unit = unitpath_from_unit(unit=unit)

    p_dls = p_unit / 'Downloads'
    lst_unit = recurse_dsc(p_search=p_dls, maxdepth=3, d_lower=d_lower)
    
    if lst_unit:
        lst_unit.sort(key=lambda p: date_from_dsc(p), reverse=True)
        lst.append(lst_unit[0])
    
    return lst

def get_recent_dsc_all(d_lower=dt(2020,1,1)):
    # return list of most recent dsc folders for all units
    p_units = get_unitpaths()
    lst = []
    
    for p_unit in p_units:
        lst.extend(get_recent_dsc_single(p_unit=p_unit, d_lower=d_lower))

    return lst

def move_tr3(p):
    unit = unit_from_path(p) # assuming in unit folder

    p_dst_base = Path('/Users/Jayme/OneDrive/SMS Equipment/Share/tr3 export')
    p_dst = p_dst_base / f'{unit}/{p.name}'

    copy_file(p_src=p, p_dst=p_dst)

def fix_dsc(p, p_unit, zip_=False):
    # process/fix single dsc/dls folder
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

            p_zip = zip_folder(
                p=p,
                delete=True,
                p_new=p_new / p.name,
                calculate_size=False)

        move_folder(p_src=p_src, p_dst=p_dst)
    except:
        print(f'Error fixing dsc folder: {str(p_src)}')

    print('Elapsed time: {}s'.format(f.deltasec(start, timer())))

def zip_recent_dls(units, d_lower=dt(2020,1,1)):
    # get most recent dsc from list of units and zip parent folder for attaching to TSI
    if not isinstance(units, list): units = [units]
    lst = []
    for unit in units:
        lst.extend(get_recent_dsc_single(unit=unit, d_lower=d_lower))
        
    lst_zip = [zip_folder(p=p.parent, delete=False, calculate_size=True) for p in lst]

    return lst_zip


def process_files(ftype, units=[], search_folders=['downloads'], d_lower=dt(2020,1,1), maxdepth=4):
    # top level control function - pass in single unit or list of units
        # 1. get list of files (haul, fault, dsc)
        # 2. Process - import haul/fault or 'fix' dsc eg downloads folder structure
    
    if ftype == 'tr3': search_folders.append('vibe tests') # bit sketch

    if not units: # assume ALL units # TODO: make this work for all minesites?
        units = [f'F{n}' for n in range(300, 348)]
    elif not isinstance(units, list):
        units = [units]

    unitpaths = get_unitpaths() # save so don't need to call multiple times
    search_folders = list(map(lambda x: x.lower(), search_folders))

    lst = []
    config = get_config()[ftype]

    for unit in units:
        p_unit = unitpath_from_unit(unit=unit, unitpaths=unitpaths)
        lst_search = [x for x in p_unit.iterdir() if x.is_dir() and x.name.lower() in search_folders] # start at downloads

        # could search more than just downloads folder (eg event too)
        for p_search in lst_search:
            lst.extend(get_list_files(ftype=ftype, p_search=p_search, d_lower=d_lower, maxdepth=maxdepth))

        # process all dsc folders per unit as we find them
        if ftype == 'dsc':
            print(f'\n\nProcessing dsc, unit: {unit}\ndsc folders found: {len(lst)}')
            for p in lst: fix_dsc(p=p, p_unit=p_unit, zip_=True)
            lst = [] # need to reset list, only for dsc, this is a bit sketch
        elif ftype == 'tr3':
            for p in lst: move_tr3(p=p)
            lst = []

    # collect all csv files for all units first, then import together
    if ftype in ('haul', 'fault'):
        if lst:
            df = combine_csv(lst_csv=lst, ftype=ftype)
            db.import_df(df=df, imptable=config['imptable'], impfunc=config['impfunc'], prnt=True)

def get_list_files(ftype, p_search, d_lower=dt(2020,1,1), maxdepth=4):
    # return list of haulcycle, fault, tr3, or dsc files/folders
    print(p_search)
    
    lst = []
    # recurse and find all other folders inside
    if ftype in ('haul', 'fault', 'tr3'):
        lst = recurse_folders(p_search=p_search, maxdepth=maxdepth, d_lower=d_lower, exclude=get_config()[ftype]['exclude'], ftype=ftype)
    elif ftype == 'dsc':
        lst = recurse_dsc(p_search=p_search, maxdepth=maxdepth, d_lower=d_lower)
    
    unit = unit_from_path(p=p_search)
    print(f'fType: {ftype}, Unit: {unit}, files: {len(lst)}')
    
    return lst

def write_import_fail(p):
    failpath = Path().home() / 'OneDrive/Desktop/importfail.txt'
    with open(failpath, 'a') as f:
        f.write(f'{p}\n')
    


# OTHER
def drive_exists():
    if f.drive.exists():
        return True
    else:
        msg = 'Cannot connect to network drive. \
            \n\nCheck: \n\t1. VPN is connected\n\t2. Drive is activated \
            \n\n(To activate drive, open any folder on the drive).'
        dlgs.msg_simple(msg=msg, icon='warning')
        return False

def open_folder(p, check_drive=False):
    if check_drive and not drive_exists():
        return
    
    if not p.exists():
        return

    platform = sys.platform
    if platform.startswith('win'):
        os.startfile(p)
    elif platform.startswith('dar'):
        subprocess.Popen(['open', p])
    else:
        subprocess.Popen(['xdg-open', p])

def get_app_name(appNamesList, app):
    for appName in appNamesList:
        if app in appName:
            return appName
    return ""


def open_app(name):
    # p = subprocess.Popen(["ls",  "/Applications/"], stdout=subprocess.PIPE)
    # appNames = p.communicate()[0].split('\n')
    # appName = get_app_name(appNames, name)

    if not name == '':
        p = subprocess.Popen(["open", "-n", "/Applications/" + name], stdout=subprocess.PIPE)
    else:
        print('No app with that name installed')

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
            f.send_error(prnt=True)

def tree(directory):
    # TODO: maybe move this to functions
    print(f'+ {directory}')
    for path in sorted(directory.rglob('*')):
        depth = len(path.relative_to(directory).parts)
        spacer = '    ' * depth
        print(f'{spacer}+ {path.name}')
