# from collections import defaultdict
import base64
import functools
import json
import sys
from datetime import datetime as date
from datetime import timedelta as delta
from pathlib import Path

import pandas as pd
import six
import yaml

import gui as ui

try:
    from IPython.display import display
except ModuleNotFoundError:
    pass


global drive, config, topfolder

topfolder = Path(__file__).parent
if sys.platform.startswith('win'):
    drive = 'P:/'
else:
    drive = '/Volumes/Public/'

def setconfig():
    p = Path(topfolder / 'data/config.yaml')
    with open(p) as file:
        m = yaml.full_load(file)
    
    return m

def inverse(m):
    return {v: k for k, v in m.items()}

def convert_headers(title, cols):
    # convert db cols to view cols
    m = inverse(config['Headers'][title])
    return [m[c] for c in cols]

def get_default_headers(title):
    return list(config['Headers'][title].keys())

def convert_header(title, header):
    try:
        return config['Headers'][title][header]
    except:
        return header

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

def left_justified(df, header=False):
    formatters = {}
    for li in list(df.columns):
        max = df[li].str.len().max()
        form = "{{:<{}s}}".format(max)
        formatters[li] = functools.partial(str.format, form)
    # display(formatters)
    return df.to_string(formatters=formatters, index=False, header=header)

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
    p = Path(topfolder) / 'data/db.yaml'
    if p.exists():
        return True
    else:
        p2 = Path(topfolder) / 'data/db_secret.txt'

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
    p = Path(topfolder) / 'data/db.yaml'
    with open(p) as file:
        m = yaml.full_load(file)
    return m

def encode_db(key):
    m = get_db()
    p = Path(topfolder) / 'data/db_secret.txt'
    with open(p, 'wb') as file:
        file.write(encode(key=key, string=json.dumps(m)))
    return True


config = setconfig()
