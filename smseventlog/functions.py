# from collections import defaultdict
import base64
import functools
import json
import os
import sys
from datetime import (datetime as date, timedelta as delta)
from pathlib import Path

import pandas as pd
import six
import yaml
import logging

try:
    from IPython.display import display
except ModuleNotFoundError:
    pass

global drive, config, topfolder, azure_env, datafolder

azure_env = os.getenv("AZURE_FUNCTIONS_ENVIRONMENT")
if azure_env is None and not 'linux' in sys.platform:
    from . import gui as ui
    
topfolder = Path(__file__).parent
if getattr(sys, 'frozen', False):
    topfolder = topfolder.parent
datafolder = topfolder / 'data'

if sys.platform.startswith('win'):
    drive = 'P:/'
else:
    drive = '/Volumes/Public/'
    
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# for root, dirs, files in os.walk(resource_path('')):
#     print(root)
#     for file in files:
#         print( ' ', file)


def setconfig():
    p = Path(datafolder / 'config.yaml')
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

def discord(msg, channel='jambot'):
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
