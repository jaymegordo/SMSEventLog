import base64
import functools
import json
import re
import traceback
from distutils.util import strtobool

import pandas as pd
import six
import sqlalchemy as sa
import yaml

from .__init__ import *

try:
    from IPython.display import display
except ModuleNotFoundError:
    pass

log = logging.getLogger(__name__)

global drive, config, config_platform, platform, topfolder, projectfolder, buildfolder, datafolder, frozen, azure_env

azure_env = os.getenv("AZURE_FUNCTIONS_ENVIRONMENT")
    
topfolder = Path(__file__).parent
projectfolder = topfolder.parent
buildfolder = Path.home() / 'Documents/smseventlog'
frozen = False

if getattr(sys, 'frozen', False):
    frozen = True
    topfolder = topfolder.parent

datafolder = topfolder / 'data'
orca_path = topfolder.parent / 'orca' # for using orca to save plotly images when frozen
os.environ['PATH'] = os.pathsep.join([os.environ['PATH'], str(orca_path)])

if sys.platform.startswith('win'):
    drive = Path('P:')
    platform = 'win'
else:
    drive = Path('/Volumes/Public')
    platform = 'mac'

def set_config():
    # config is yaml file with config details, dictionary conversions etc
    p = Path(datafolder / 'config.yaml')
    with open(p, encoding='utf8') as file:
        m = yaml.full_load(file)
    
    return m

config = set_config()
config_platform = config['Platform'][platform]

# DICT & CONVERSIONS
def inverse(m):
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

def convert_df_db_cols(title, df):
    # convert df with view_cols to db_cols from dict of conversions. keep original if new col not in dict
    m = get_dict_view_db(title)
    df.columns = [m[c] if c in m.keys() else c for c in df.columns]
    return df

def convert_dict_db_view(title, m, output='view'):
    # convert dict with from either db or view, to output type cols
    # NOTE only converts columns which exist in the given table view eg 'Work Orders' or 'Event Log'
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

def model_dict(model, include_none=False):
    # create dict from table model
    m = {a.key:getattr(model, a.key) for a in sa.inspect(model).mapper.column_attrs}
    if not include_none:
        m = {k:v for k,v in m.items() if v is not None}
    
    return m

def copy_model_attrs(model, target):
    m = model_dict(model=model, include_none=True)
    copy_dict_attrs(m=m, target=target)

def copy_dict_attrs(m, target):
    for k, v in m.items():
        setattr(target, k.lower(), v)

def pretty_dict(m):
    return str(m).replace('{', '').replace('}', '').replace(', ', '\n').replace("'", '')

def first_n(m, n):
    # return first n items of dict

    return {k:m[k] for k in list(m.keys())[:n]}

def set_self(m, prnt=False, exclude=()):
    # convenience func to assign an object's func's local vars to self
    if not isinstance(exclude, tuple): exclude = (exclude, )
    exclude += ('__class__', 'self') # always exclude class/self
    obj = m.get('self', None) # self must always be in vars dict
    if obj is None: return

    for k, v in m.items():
        if prnt:
            print(f'\n\t{k}: {v}')

        if not k in exclude:
            setattr(obj, k, v)



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

def deltasec(start, end):
    return str(delta(seconds=end - start)).split('.')[0]

def cursor_to_df(cursor):
    data = (tuple(t) for t in cursor.fetchall())
    cols = [column[0] for column in cursor.description]
    return pd.DataFrame(data=data, columns=cols)

def isnum(val):
    return str(val).replace('.', '', 1).isdigit()

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

def nice_title(title):
    # Remove slashes, capitalize first letter, avoid acronyms
    excep = 'the a on in of an'.split(' ')
    title = re.sub('[\\\/.]', '', title)

    return ' '.join(f'{w[0].upper()}{w[1:]}' if not w.lower() in excep else w for w in title.split(' '))  
    
def str_to_bool(val):
    return bool(strtobool(val))

def convert_date(val):
    try:
        if isinstance(val, date):
            return dt.combine(val, dt.min.time())
        elif isinstance(val, str):
            return dt.strptime(val, '%Y-%m-%d')
        else:
            return val
    except:
        return val

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
    # convert any columns with 'date' or 'time' in header name to datetime
    datecols = list(filter(lambda x: any(s in x.lower() for s in ('date', 'time')) , df.columns))
    df[datecols] = df[datecols].apply(pd.to_datetime)
    return df

def dtypes_dict(dtype, cols):
    return {col: dtype for col in cols}

def set_default_dtypes(df, m):
    # set column dtype based on dict of defaults
    for col, dtype in m.items():
        if col in df.columns:
            df[col] = df[col].astype(dtype)
    return df

def convert_dtypes(df, cols, col_type):
    if not isinstance(cols, list): cols = [cols]
    for col in cols:
        df[col] = df[col].astype(col_type)
    return df

def convert_int64(df):
    # convert all int64 (numpy) to Int64 (pandas) to better handle null values
    for col, dtype in df.dtypes.items():
        if dtype == 'int64':
            df[col] = df[col].astype('Int64')

    return df

def clean_series(s, convert_str=False):
    if convert_str:
        s = s.astype(str)
        
    return sorted(list(s.replace('', pd.NA).dropna().unique()))

def convert_stylemap_index(style):
    # convert irow, icol stylemap to df index
    # m is dict of eg {(0, 4): ['background-color: #fef0f0', 'color: #000000']}
    # NOTE styler saves everything, so if multiple styles are applied, this would only use the first
    stylemap = style.ctx
    df = style.data
    m = {(df.index[k[0]], df.columns[k[1]]):v for k, v in stylemap.items()}

    return m

def append_default_row(df):
    # ensure df dtypes aren't changed when appending new row by creating a blank row of defaults, then filling after
    # return {col: val} for all columns in df
    defaults = {
        'int64': pd.NA,
        'float64': pd.NA,
        'datetime64[ns]': pd.NaT,
        'bool': None,
        'object': None}
    
    dtypes = {k: str(v).lower() for k, v in df.dtypes.items()} # convert dtypes to lowercase strings
    m = {col: defaults[dtype] if dtype in defaults else np.nan for col, dtype in dtypes.items()}
    return df \
        .append(m, ignore_index=True) \
        .astype(df.dtypes)

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
    p = datafolder / 'db.yaml'
    if p.exists():
        return True
    else:
        from .gui import dialogs as dlgs
        p2 = datafolder / 'db_secret.txt'

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

def encode_db(key):
    m = get_db_creds()
    p = datafolder / 'db_secret.txt'
    with open(p, 'wb') as file:
        file.write(encode(key=key, string=json.dumps(m)))
    return True

def discord(msg, channel='orders'):
    import requests
    import discord
    from discord import Webhook, RequestsWebhookAdapter, File

    p = Path(datafolder) / 'apikeys/discord.csv'
    r = pd.read_csv(p, index_col='channel').loc[channel]
    if channel == 'err': msg += '@here'

    # Create webhook
    webhook = Webhook.partial(r.id, r.token, adapter=RequestsWebhookAdapter())
    
    # split into strings of max 2000 char for discord
    n = 2000
    out = [(msg[i:i+n]) for i in range(0, len(msg), n)]
    
    for msg in out:
        webhook.send(msg)

def format_traceback():
    msg = traceback.format_exc() \
        .replace('Traceback (most recent call last):\n', '')
    
    if '*split' in msg:
        msg = ''.join(msg.split('*split')[1:]) # split here to remove the @e wrapper warning
    
    check_text = 'During handling of the above exception, another exception occurred:\n'
    if check_text in msg:
        msg = ''.join(msg.split(check_text)[1:])
    
    return msg

def send_error(msg='', prnt=False, func=None, display=False, logger=None):   
    # send error to discord, print, or log error
    err = format_traceback()

    if not msg == '':
        err = f'{msg}:\n{err}'.replace(':\nNoneType: None', '')
    
    err = f'*------------------*\n{err}'

    if prnt or not 'linux' in sys.platform:
        print(err)
    else:
        discord(msg=err, channel='err')

    if display:
        from . import errors as er
        er.display_error()
    
    if not logger is None:
        log.error(msg)

def create_logger(func=None):
    # not used yet
    logger = logging.getLogger("example_logger")
    logger.setLevel(logging.INFO)
    
    fh = logging.FileHandler("/path/to/test.log")
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt)
    fh.setFormatter(formatter)
    # add handler to logger object
    logger.addHandler(fh)
    return logger
