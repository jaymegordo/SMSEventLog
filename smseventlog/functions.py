from collections import defaultdict
import base64
import json
import os
import sys
from datetime import (datetime as dt, timedelta as delta)
from pathlib import Path

import pandas as pd
import six
import yaml
import sqlalchemy as sa

try:
    from IPython.display import display
except ModuleNotFoundError:
    pass

global drive, config, topfolder, azure_env, datafolder

azure_env = os.getenv("AZURE_FUNCTIONS_ENVIRONMENT")
    
topfolder = Path(__file__).parent
if getattr(sys, 'frozen', False):
    topfolder = topfolder.parent
datafolder = topfolder / 'data'

if sys.platform.startswith('win'):
    drive = Path('P:')
else:
    drive = Path('/Volumes/Public')
    
def setconfig():
    p = Path(datafolder / 'config.yaml')
    with open(p) as file:
        m = yaml.full_load(file)
    
    return m

# DICT & CONVERSIONS
def inverse(m):
    return {v: k for k, v in m.items()}

def convert_dict_db_view(title, m):
    # convert dict of db cols to view cols
    dbcols = list(m.keys())
    viewcols = convert_list_db_view(title=title, cols=dbcols)
    return {view:m[db] for view, db in zip(viewcols, dbcols) if view is not None}

def convert_list_db_view(title, cols):
    # convert list of db cols to view cols, remove cols not in the view?
    # m = defaultdict(type(None), inverse(config['Headers'][title]))
    m = inverse(config['Headers'][title])
    return [m[c] if c in m.keys() else c for c in cols]

def convert_list_view_db(title, cols):
    # convert list of view cols to db cols
    m = config['Headers'][title]
    return [m[c] if c in m.keys() else c for c in cols]

def get_default_headers(title):
    return list(config['Headers'][title].keys())

def convert_header(title, header):
    try:
        return config['Headers'][title][header]
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



def is_win():
    ans = True if sys.platform.startswith('win') else False
    return ans

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
    from . import gui as ui
    p = Path(datafolder) / 'db.yaml'
    if p.exists():
        return True
    else:
        p2 = Path(datafolder) / 'db_secret.txt'

        # Prompt user for pw
        msg = 'Database credentials encrypted, please enter password.\n(Contact {} if you do not have password).\n\nPassword:'.format(config['Email'])
        ok, key = ui.inputbox(msg=msg)
        if ok:
            with open(p2, 'rb') as file:
                secret_encrypted = file.read()
            
            secret_decrypted = decode(key=key, string=secret_encrypted)
            
            try:
                m2 = json.loads(secret_decrypted)

            except:
                ui.msg_simple(msg='Incorrect password!', icon='Critical')
                return

            with open(p, 'w+') as file:
                yaml.dump(m2, file)

            return True

def get_db():
    p = Path(datafolder) / 'db.yaml'
    with open(p) as file:
        m = yaml.full_load(file)
    return m

def encode_db(key):
    m = get_db()
    p = Path(datafolder) / 'db_secret.txt'
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

def senderror(msg='', prnt=False):
    import traceback
    err = traceback.format_exc().replace('Traceback (most recent call last):\n', '')

    if not msg == '':
        err = '{}:\n{}'.format(msg, err).replace(':\nNoneType: None', '')
    
    err = '*------------------*\n{}'.format(err)

    if prnt or not 'linux' in sys.platform:
        print(err)
    else:
        discord(msg=err, channel='err')

config = setconfig()
