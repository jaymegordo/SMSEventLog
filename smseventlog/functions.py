import base64
import functools
import inspect
import json
import pickle
import re
from distutils.util import strtobool
from importlib import import_module
from pkgutil import iter_modules
import pkgutil

import six
import yaml

from .__init__ import *

log = getlog(__name__)

global drive, config, config_platform, platform, topfolder, projectfolder, temp, desktop, buildfolder, resources, secret, frozen

if sys.platform.startswith('win'):
    drive = Path('P:\\')
    platform = 'win'
else:
    drive = Path('/Volumes/Public')
    platform = 'mac'

temp = applocal / 'temp'    
p_ext = applocal / 'extensions'
topfolder = Path(__file__).parent # smseventlog
projectfolder = topfolder.parent # SMS
buildfolder = Path.home() / 'Documents/smseventlog'
desktop = Path.home() / 'Desktop'
p_sql = projectfolder / 'SQL'

def add_to_path(p):
    os.environ['PATH'] = os.pathsep.join([os.environ['PATH'], str(p)])

if SYS_FROZEN:
    topfolder = projectfolder

    if platform == 'win':
        # add manual gtk path to PATH for weasyprint/cairo if windows
        gtk_path = projectfolder / 'GTK3-Runtime Win64/bin'
        add_to_path(gtk_path)

    # Add this to path so plotly can find Kaleido executable
    # win is actually path to kaleido.cmd
    kaleido_path = p_ext / 'kaleido/kaleido'
    add_to_path(kaleido_path)
    kaleido_path = str(kaleido_path)

resources = topfolder / '_resources' # data folder location is shifted out of smseventlog for frozen build
secret = resources / 'secret'

# copy sql files to resources when frozen
if SYS_FROZEN:
    p_sql = resources / 'SQL'

def set_config():
    # config is yaml file with config details, dictionary conversions etc
    p = Path(resources / 'config.yaml')
    with open(p, encoding='utf8') as file:
        m = yaml.full_load(file)
    
    return m

config = set_config()
config_platform = config['Platform'][platform]


# DICT & CONVERSIONS
def inverse(m : dict) -> dict:
    """Return inverse of dict"""
    return {v: k for k, v in m.items()}

def get_dict_view_db(title):
    # return dict of {view_col: db_col}
    return config['Headers'].get(title, {})

def get_dict_db_view(title):
    # return dict of {db_col: view_col}
    return inverse(get_dict_view_db(title))

def convert_df_view_cols(df, m):
    # convert db cols to view cols from dict of conversions. keep original if new col not in dict
    df.columns = [m[c] if c in m.keys() else c for c in df.columns]
    return df

def convert_df_db_cols(title : str, df : pd.DataFrame):
    """Convert df with view_cols to db_cols from dict of conversions. keep original if new col not in dict

    Parameters
    ----------
    title : str
        table title
    df : pd.DataFrame

    Returns
    -------
    pd.DatFrame
        dataframe with cols converted to db cols
    """
    m = get_dict_view_db(title)
    df.columns = [m[c] if c in m.keys() else c for c in df.columns]
    return df

def convert_dict_db_view(title : str, m : dict, output : str='view'):
    """Convert dict with from either db or view, to output type cols
    - NOTE only converts columns which exist in the given table view eg 'Work Orders' or 'Event Log'"""
    func_name = 'convert_list_db_view' if output == 'view' else 'convert_list_view_db'
    func = getattr(sys.modules[__name__], func_name)
    initial_cols = list(m.keys())
    final_cols = func(title=title, cols=initial_cols)

    return {final:m[initial] for final, initial in zip(final_cols, initial_cols) if final is not None}

def convert_list_db_view(title, cols):
    # convert list of db cols to view cols, remove cols not in the view?
    m = config['Headers'].get(title, None)
    if not m is None:
        m = inverse(m)
        return [m[c] if c in m.keys() else c for c in cols]
    else:
        return cols

def convert_list_view_db(title, cols):
    # convert list of view cols to db cols
    m = config['Headers'][title]
    return [m[c] if c in m.keys() else c for c in cols]

def get_default_headers(title):
    return list(config['Headers'][title].keys())

def convert_header(title, header, inverse_=False):
    m = config['Headers'][title]
    if inverse_: m = inverse(m)

    try:
        return m[header]
    except:
        return header

def copy_model_attrs(model, target):
    from . import dbtransaction as dbt
    m = dbt.model_dict(model=model, include_none=True)
    copy_dict_attrs(m=m, target=target)

def copy_dict_attrs(m : dict, target: object):
    """Copy dict items to target object (lowercase)"""
    for k, v in m.items():
        setattr(target, k.lower(), v)

def two_col_list(m) -> str:
    """Create two col css list from dict, used in reports

    Parameters
    ----------
    m : dict
        Dict to convert\n
    """
    body = ''
    for name, val in m.items():
        body = f'{body}<li><span>{name}:</span><span>{val}</span></li>'
    
    return f'<ul class="two_col_list_narrow">{body}</ul>'

def pretty_dict(m : dict, html=False) -> str:
    """Return dict converted to newlines
    Paramaters
    ----
    m : dict\n
    html: bool
        Use <br> instead of html
    Returns
    -------
    str\n
        'Key 1: value 1\n
        'Key 2: value 2"
    """
    newline_char = '\n' if not html else '<br>'
    return str(m).replace('{', '').replace('}', '').replace(', ', newline_char).replace("'", '')

def first_n(m: dict, n: int):
    """Return first n items of dict"""
    return {k:m[k] for k in list(m.keys())[:n]}

def set_self(m, prnt=False, exclude=()):
    """Convenience func to assign an object's func's local vars to self"""
    if not isinstance(exclude, tuple): exclude = (exclude, )
    exclude += ('__class__', 'self') # always exclude class/self
    obj = m.get('self', None) # self must always be in vars dict

    if obj is None:
        return

    for k, v in m.items():
        if prnt:
            print(f'\n\t{k}: {v}')

        if not k in exclude:
            setattr(obj, k, v)

def truncate(val, max_len):
    val = str(val)
    s = val[:max_len]
    if len(val) > max_len: s = f'{s}...'
    return s

def is_win():
    ans = True if sys.platform.startswith('win') else False
    return ans

def is_mac():
    return sys.platform.startswith('dar')

def bump_version(ver, vertype='patch'):
    if not isinstance(ver, str): ver = ver.base_version

    m = dict(zip(['major', 'minor', 'patch'], [int(i) for i in ver.split('.')]))
    m[vertype] += 1
    
    return '.'.join((str(i) for i in m.values()))

def deltasec(start, end=None):
    """Return difference from time object formatted as seconds

    Parameters
    ----------
    start : time.time
        start time obj
    end : time.time, optional
        end time, by default None

    Returns
    -------
    str
        time formatted as seconds string
    Examples
    --------
    >>> start = time()
    >>> f.deltasec(start)
    >>> '00:00:13'
    """    
    if end is None:
        end = time.time()

    return str(delta(seconds=end - start)).split('.')[0]

def cursor_to_df(cursor):
    data = (tuple(t) for t in cursor.fetchall())
    cols = [column[0] for column in cursor.description]
    return pd.DataFrame(data=data, columns=cols)

def isnum(val):
    return str(val).replace('.', '', 1).isdigit()

def conv_int_float_str(val):
    expr = r'^\d+$' # int
    expr2 = r'^\d+\.\d+$' # float

    if re.match(expr, val):
        return int(val)
    elif re.match(expr2, val):
        return float(val)
    else:
        return str(val)

def greeting():
    val = 'Morning' if dt.now().time().hour < 12 else 'Afternoon'
    return f'Good {val},<br><br>'

def getattr_chained(obj, methods):
    # return value from chained method calls
    # eg a = 'A Big Thing' > getattr_chained(a, 'str.lower')
    try:
        for method in methods.split('.'):
            obj = getattr(obj, method)()

        return obj
    except:
        return None

def remove_bad_chars(w : str):
    """Remove any bad chars " : < > | . \\ / * ? in string to make safe for filepaths"""
    return re.sub(r'[\\":<>|.\/\*\?{}]', '', str(w))

def nice_title(title: str) -> str:
    """Remove slashes, capitalize first letter, avoid acronyms"""
    if pd.isnull(title):
        return ''
        
    if title.strip() == '':
        return title
        
    excep = 'the a on in of an is'.split(' ')
    title = remove_bad_chars(w=title).strip()

    return ' '.join(
        f'{w[0].upper()}{w[1:]}' if not w.lower() in excep else w for w in title.split())  
    
def str_to_bool(val):
    if isinstance(val, (np.bool_, np.bool)):
        return bool(val)

    return bool(strtobool(val))

def convert_date(val):
    """Convert string date or datetime,  or date obj, to datetime object"""
    try:
        if isinstance(val, date):
            return dt.combine(val, dt.min.time())
        elif isinstance(val, str):
            try:
                return dt.strptime(val, '%Y-%m-%d')
            except:
                return dt.strptime(val, '%Y-%m-%d %H:%M:%S')
        else:
            return val # already a date
    except:
        log.warning(f'Couldn\'t convert val to date: {val}')
        return val

def _input(msg):
    # get yes/no answer from user in terminal
    reply = str(input(msg + ' (y/n): ')).lower().strip()
    if len(reply) <= 0: return False
    if reply[0] == 'y':
        return True
    elif reply[0] == 'n':
        return False
    else:
        return False

def save_pickle(obj, p):
    """Save object to pickle file"""
    with open(p, 'wb') as file:
        pickle.dump(obj, file)
    
    log.info(f'Saved pickle: {p}')

def iter_namespace(name):
    """Get module names from top level package name
    - Used when app is frozen with PyInstaller
    - Make sure to add module to pyi's collect_submodules so they're available from it's importer"""
    prefix = name + '.'
    toc = set()

    for importer in pkgutil.iter_importers(name.partition('.')[0]):
        if hasattr(importer, 'toc'):
            toc |= importer.toc

    for name in toc:
        if name.startswith(prefix):
            yield name

def import_submodule_classes(name, filename, gbls, parent_class):
    """Import all Query objects into top level namespace for easier access
    - eg query = qr.EventLog() instead of qr.el.EventLog()
    - NOTE issubclass doesn't work when class is defined in __init__"""

    if not '__init__' in name:
        package_dir = Path(filename).resolve().parent

        if not SYS_FROZEN:
            module_names = [f'{name}.{module_name}' for (_, module_name, _) in iter_modules([package_dir])]
        else:
            module_names = [n for n in iter_namespace(name) if not 'init' in n]

        for module_name in module_names:
            # import the module and iterate through its attributes
            module = import_module(module_name)

            for cls_name, cls in inspect.getmembers(module, inspect.isclass):

                if parent_class in str(cls):
                    gbls[cls_name] = cls

# PANDAS
def multiIndex_pivot(df, index=None, columns=None, values=None):
    # https://github.com/pandas-dev/pandas/issues/23955
    output_df = df.copy(deep=True)

    if index is None:
        names = list(output_df.index.names)
        output_df = output_df.reset_index()
    else:
        names = index

    output_df = output_df.assign(tuples_index=[tuple(i) for i in output_df[names].values])

    if isinstance(columns, list):
        output_df = output_df.assign(tuples_columns=[tuple(i) for i in output_df[columns].values])  # hashable
        output_df = output_df.pivot(index='tuples_index', columns='tuples_columns', values=values) 
        output_df.columns = pd.MultiIndex.from_tuples(output_df.columns, names=columns)  # reduced
    else:
        output_df = output_df.pivot(index='tuples_index', columns=columns, values=values)
         
    output_df.index = pd.MultiIndex.from_tuples(output_df.index, names=names)
    
    return output_df

def flatten_multiindex(df):
    """Flatten multi index columns and join with '_' unless second level is blank '' """
    df.columns = df.columns.map(lambda x: '_'.join(x) if not x[1] == '' else x[0])
    return df

def sort_df_by_list(df, lst, lst_col, sort_cols=[]):
    # sort specific column by list, with option to include other columns first
    sorterIndex = dict(zip(lst, range(len(lst))))
    df['sort'] = df[lst_col].map(sorterIndex)

    if not isinstance(sort_cols, list): sort_cols = [sort_cols]
    sort_cols.insert(0, 'sort')
    
    df.sort_values(sort_cols, inplace=True)
    df.drop(columns=['sort'], inplace=True)
    return df

def parse_datecols(df):
    """Convert any columns with 'date' or 'time' in header name to datetime"""
    datecols = list(filter(lambda x: any(s in x.lower() for s in ('date', 'time')) , df.columns))
    df[datecols] = df[datecols].apply(pd.to_datetime, errors='coerce')
    return df

def dtypes_dict(dtype, cols):
    return {col: dtype for col in cols}

def set_default_dtypes(df, m):
    """Set column dtype based on dict of defaults"""
    for col, dtype in m.items():
        if col in df.columns:
            df[col] = df[col].astype(dtype)
            
    return df

def read_excel(p, **kw):
    return pd.read_excel(p, **kw) \
        .pipe(default_data)

def read_csv(p, **kw):
    return pd.read_csv(p, **kw) \
        .pipe(default_data)

def default_data(df):
    """Default func to read csv and apply transforms"""
    return df \
        .pipe(lower_cols) \
        .pipe(parse_datecols) \
        .pipe(convert_int64)

def default_df(df):
    """Simple df date/int conversions to apply to any df"""
    return df \
        .pipe(parse_datecols) \
        .pipe(convert_int64)

def terminal_df(df, date_only=True, show_na=False):
    """Display df in terminal with better formatting"""
    from tabulate import tabulate

    if date_only:
        m = {col: lambda x: x[col].dt.date for col in df.select_dtypes('datetime').columns}
        df = df.assign(**m)
        # for col in df.select_dtypes('datetime').columns:
        #     df.loc[:, col] = df.loc[:, col].dt.date

    s = tabulate(df, headers=df.columns)

    if not show_na:
        s = s.replace('nan', '   ')
    
    print(s)

def convert_dtypes(df, cols, col_type):
    if not isinstance(cols, list): cols = [cols]
    for col in cols:
        df[col] = df[col].astype(col_type)
    return df

def convert_int64(df, all_numeric=False):
    """Convert all int64 (numpy) to Int64 (pandas) to better handle null values"""
    for col, dtype in df.dtypes.items():
        if dtype == 'int64' or (all_numeric and dtype == 'float64'):
            df[col] = df[col].astype(pd.Int64Dtype())

    return df

def format_int64(df):
    """Get dict for formatting all ints with commas"""
    m = {col: '{:,.0f}' for col, dtype in df.dtypes.items() if str(dtype).lower() == 'int64'}
    return m

def clean_series(s, convert_str=False):
    if convert_str:
        s = s.astype(str)
        
    return sorted(list(s.replace('', pd.NA).dropna().unique()))

def append_default_row(df):
    # ensure df dtypes aren't changed when appending new row by creating a blank row of defaults, then filling after
    # return {col: val} for all columns in df
    defaults = {
        'int64': pd.NA,
        'float64': pd.NA,
        'datetime64[ns]': pd.NaT,
        'bool': None, # False makes 'truth value of array ambiguous issues'
        'object': None}
    
    dtypes = {k: str(v).lower() for k, v in df.dtypes.items()} # convert dtypes to lowercase strings
    m = {col: defaults[dtype] if dtype in defaults else np.nan for col, dtype in dtypes.items()}
    return df \
        .append(m, ignore_index=True) \
        .astype(df.dtypes)

def df_to_strings(df, formats):
    """Convert df values to string values for faster display in table.

    Example
    -------
    >>> formats = {
        'StartDate': '{:%Y-%m-%d %H:%M}',
        'Total': '{:,.2f}',
    """
    df = df.copy()
    for col, fmt in formats.items():
        if col in df.columns:
            df[col] = df[col].apply(lambda x: fmt.format(x) if not pd.isnull(x) else '')

    return df.astype('object').fillna('')

def df_to_color(df, highlight_funcs : dict, role):
    """Convert df of values to QColor for faster display in table.

    Parameters
    ----------
    df : pd.DataFrame

    highlight_funcs : dict
        {col_name: func_to_apply}
    """
    df_out = pd.DataFrame(data=None, index=df.index, columns=df.columns)
    for col, func in highlight_funcs.items():
        try:
            if not func is None:
                df_out[col] = df[col].apply(lambda x: func(val=x, role=role))
        except:
            pass

    return df_out

def convert_stylemap_index(style):
    """**NOT USED** convert irow, icol stylemap to df named index
    m is dict of eg {(0, 4): ['background-color: #fef0f0', 'color: #000000']}
    NOTE styler saves everything, so if multiple styles are applied, this would only use the first"""
    stylemap = style.ctx
    df = style.data
    m = {(df.index[k[0]], df.columns[k[1]]):v for k, v in stylemap.items()}

    return m

def convert_stylemap_index_color(style, as_qt=True, first_val: bool=True):
    """Convert (irow, icol) stylemap to dict of {col: {row: QColor(value)}}
    
    eg stylemap = {(0, 4): ['background-color: #fef0f0', 'color: #000000']}


    Parameters
    ----------
    style: pd.Styler
    as_qt: bool
        return QColor or just hex
    first_val: bool
        style.ctx could have had multiple style_vals set for eg background-color
        allow selecting first or last val

    Returns
    -------
    tuple
        (background, text) of
            {col: {row: QColor}}
    """
    from PyQt5.QtGui import QColor

    m_background = dd(dict)
    m_text = dd(dict)
    df = style.data

    if len(style.ctx) == 0:
        style._compute()

    def set_color(style_vals, i):
        # may only have background-color, not color
        try:
            color = style_vals[i].split(' ')[1]
            color_out = color if not color == '' else None
            return QColor(color_out) if as_qt and not color_out is None else color_out
        except:
            return None

    first_last = 0 if first_val else -1

    for k, style_vals in style.ctx.items():
        row, col = df.index[k[0]], df.columns[k[1]]

        # need to filter style_vals to only include one background-color and one color
        bg_vals = [item for item in style_vals if item.split(':')[0] == 'background-color']

        text_vals = list(set(style_vals) - set(bg_vals))
        
        # NOTE this might fail if two 'inherit'
        if len(bg_vals) > 1:
            bg_vals = [item for item in bg_vals if not item.split(': ')[1] == 'inherit']


        m_background[col][row] = set_color(bg_vals, i=first_last)
        m_text[col][row] = set_color(text_vals, i=first_last)

    return m_background, m_text

def from_snake(s: str):
    """Convert from snake case cols to title"""
    return s.replace('_', ' ').title()

def to_snake(s: str):
    """Convert messy camel case to lower snake case
    
    Parameters
    ----------
    s : str
        string to convert to special snake case

    Examples
    --------
    """
    s = remove_bad_chars(s).strip() # get rid of /<() etc
    s = re.sub(r'[\]\[()]', '', s) # remove brackets/parens
    s = re.sub(r'[\n-]', '_', s) # replace newline/dash with underscore
    s = re.sub(r'[%]', 'pct', s)

    # split on capital letters
    expr = r'(?<!^)((?<![A-Z])|(?<=[A-Z])(?=[A-Z][a-z]))(?=[A-Z])'

    return re \
        .sub(expr, '_', s) \
        .lower() \
        .replace(' ', '_') \
        .replace('__', '_')

def lower_cols(df, title=False):
    """Convert df columns to snake case and remove bad characters"""
    is_list = False

    if isinstance(df, pd.DataFrame):
        cols = df.columns
    else:
        cols = df
        is_list = True

    func = to_snake if not title else from_snake

    m_cols = {col: func(col) for col in cols}
    
    if is_list:
        return list(m_cols.values())

    return df.pipe(lambda df: df.rename(columns=m_cols))

def sql_from_file(p : Path) -> str:
    """Read sql string from .sql file

    Parameters
    ----------
    p : Path
        Path to .sql file

    Returns
    -------
    str
        sql string
    """    
    with open(p, 'r') as file:
        return file.read()

def get_sql_filepath(name: str):
    """Find sql file in sql dir for frozen vs not frozen"""
    return list(p_sql.rglob(f'*{name}.sql'))[0]


# simple obfuscation for db connection string
def encode(key, string):
    encoded_chars = []
    for i in range(len(string)):
        key_c = key[i % len(key)]
        encoded_c = chr(ord(string[i]) + ord(key_c) % 256)
        encoded_chars.append(encoded_c)
    encoded_string = ''.join(encoded_chars)
    encoded_string = encoded_string.encode('latin') if six.PY3 else encoded_string
    return base64.urlsafe_b64encode(encoded_string).rstrip(b'=')

def decode(key, string):
    string = base64.urlsafe_b64decode(string + b'===')
    string = string.decode('latin') if six.PY3 else string
    encoded_chars = []
    for i in range(len(string)):
        key_c = key[i % len(key)]
        encoded_c = chr((ord(string[i]) - ord(key_c) + 256) % 256)
        encoded_chars.append(encoded_c)
    encoded_string = ''.join(encoded_chars)
    return encoded_string

def check_db():
    # Check if db.yaml exists, if not > decrypt db_secret and create it
    # NOTE not used anymore, just using stored keyfile
    p = resources / 'db.yaml'
    if p.exists():
        return True
    else:
        from .gui import dialogs as dlgs
        p2 = resources / 'db_secret.txt'

        # Prompt user for pw
        msg = 'Database credentials encrypted, please enter password.\n(Contact {} if you do not have password).\n\nPassword:'.format(config['Email'])
        ok, key = dlgs.inputbox(msg=msg)
        if ok:
            with open(p2, 'rb') as file:
                secret_encrypted = file.read()
            
            secret_decrypted = decode(key=key, string=secret_encrypted)
            
            try:
                m2 = json.loads(secret_decrypted)

            except:
                log.error('incorrect password!')
                dlgs.msg_simple(msg='Incorrect password!', icon='Critical')
                return False

            with open(p, 'w+') as file:
                yaml.dump(m2, file)

            return True

def discord(msg, channel='orders'):
    import discord
    import requests
    from discord import File, RequestsWebhookAdapter, Webhook

    from .utils.secrets import SecretsManager

    df = SecretsManager('discord.csv').load.set_index('channel')
    r = df.loc[channel]
    if channel == 'err': msg += '@here'

    # Create webhook
    webhook = Webhook.partial(r.id, r.token, adapter=RequestsWebhookAdapter())
    
    # split into strings of max 2000 char for discord
    n = 2000
    out = [(msg[i:i+n]) for i in range(0, len(msg), n)]
    
    for msg in out:
        webhook.send(msg)
