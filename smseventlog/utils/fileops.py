import shutil
import signal
import subprocess
from distutils import dir_util
from io import StringIO

import psutil

try:
    from hurry.filesize import size
except ModuleNotFoundError:
    pass

from .__init__ import *

log = getlog(__name__)

        
def date_created(p) -> dt:
    """Get date from folder date created (platform dependent)

    Parameters
    ----------
    p : Path
        Folder path to check
    """
    st = p.stat()
    ts = st.st_ctime if f.is_win() else st.st_birthtime
    
    return dt.fromtimestamp(ts)

def date_modified(p):
    return dt.fromtimestamp(p.stat().st_mtime)

def move_folder(p_src : Path, p_dst : Path):
    """Move folder or file from p_src to p_dst"""
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

def copy_file(p_src, p_dst, overwrite=False):
    p = p_dst.parent
    if not p.exists():
        p.mkdir(parents=True)

    if not p_dst.exists() or overwrite:
        shutil.copyfile(str(p_src), str(p_dst))
    else:
        print(f'File already exists: {p_dst.name}')

def zip_folder(p, delete=False, calculate_size=False, p_new=None):
    # zips target folder in place, optional delete original
    
    # zip folder into a new target dir
    # if p_new is none, just zip in place
    p_dst = p if p_new is None else p_new

    try:
        if not p.exists(): return

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
    
        return Path(p_zip)
    except:
        print(f'Error zipping folder: {p}')

def unzip(p: Path, p_dst: Path = None, delete=False) -> Path:
    """Simple wrapper for shultil unpack_archive with default unzip dir

    Parameters
    ----------
    p : Path
        File to unzip\n
    p_dst : Path, optional
        Unzip in different dir, by default parent dir\n
    delete : bool, optional
        Delete original zip after unpack, by default False
    """
    if p_dst is None:
        p_dst = p.parent

    shutil.unpack_archive(p, p_dst)

    if delete:
        p.unlink()

    return p

def unzip_pyu_archive():
    """Win only, convenience func to unzip pyu archive to local dir after build"""
    p = f.projectfolder / 'pyu-data/files'
    p = [p for p in p.glob('*zip*')][0]
    p_dst = Path.home() / 'documents/smseventlog_pyu'
    return unzip(p=p, p_dst=p_dst)

def remove_files(lst):
    for p in lst:
        if p.exists():
            p.unlink()

def count_files(p, extensions=None, ftype='pics'):
    if ftype.lower() == 'pics':
        extensions = ['jpeg', 'jpg', 'png', 'tiff']
    
    return len(find_files_ext(p=p, extensions=extensions))

def find_files_ext(p, extensions):
    return [p_ for p_ in p.rglob('*') if p_.suffix.lower().replace('.', '') in extensions and len(p_.suffix) > 0]

def find_files_partial(p, partial_text):
    return [p_ for p_ in p.glob('*') if partial_text.lower() in str(p_).lower()]


# OTHER
def drive_exists():
    if f.drive.exists():
        return True
    else:
        from ..gui import dialogs as dlgs
        msg = 'Cannot connect to network drive. \
            \n\nCheck: \n\t1. VPN is connected\n\t2. Drive is activated \
            \n\n(To activate drive, open any folder on the drive).'
        dlgs.msg_simple(msg=msg, icon='warning')
        return False

def open_folder(p, check_drive=False):
    if check_drive and not drive_exists():
        return
    
    if isinstance(p, str):
        p = Path(p)

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

def tree(directory):
    # TODO: maybe move this to functions
    print(f'+ {directory}')
    for path in sorted(directory.rglob('*')):
        depth = len(path.relative_to(directory).parts)
        spacer = '    ' * depth
        print(f'{spacer}+ {path.name}')

def from_bytes(bytes):
    """Return string from bytes object
    - Useful for reading csv/excel data from bytes so far"""
    result = str(bytes, 'UTF-8')
    return StringIO(result)

def find_procs_by_name(name):
    "Return a list of processes matching 'name'."
    return [p for p in psutil.process_iter(['name']) if name.lower() in p.info['name'].lower()]

def kill_proc(procs):
    """Try to kill locking sms proc
    - Used to stop background processes getting stuck locking the update file"""
    for p in procs:
        try:
            p.kill()
        except:
            log.warning(f'Failed to kill process: {p.name()}')

def get_sms_proc_locking(filename='zip'):
    """Get background SMS Event Log.exe process if locking 'zip' file for update"""
    procs = find_procs_by_name('sms event log')
    pid_self = os.getpid()
    
    # check if each process has any open files containing search filename
    return [p for p in procs if
        not p.pid == pid_self and
        [x for x in [item.path for item in p.open_files()] if x.endswith(filename)]]

def kill_sms_proc_locking(filename='zip'):
    procs = get_sms_proc_locking(filename)
    num_procs = len(procs)

    log.info(f'Found {num_procs} locking processes.')
    if num_procs == 1:
        proc = procs[0]
        try:
            log.info(f'Trying to kill process: {proc.name()}, {proc.pid}')
            return kill_proc_tree(pid=proc.pid)
        except:
            log.error(f'Failed to kill locking process!')
    elif num_procs > 1:
        # will need to figure this out
        log.error('Too many locking procs found to delete!')

def kill_proc_tree(pid, sig=signal.SIGTERM, include_parent=True,
                   timeout=None, on_terminate=None):
    """Kill a process tree (including grandchildren) with signal
    "sig" and return a (gone, still_alive) tuple.
    "on_terminate", if specified, is a callabck function which is
    called as soon as a child terminates.
    """
    assert pid != os.getpid(), "won't kill myself"
    
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    
    if include_parent:
        children.append(parent)
        
    for p in children:
        p.send_signal(sig)

    gone, alive = psutil.wait_procs(children, timeout=timeout,
                                    callback=on_terminate)
    return (gone, alive)
