from pathlib import Path

import exchangelib as ex
import yaml

import functions as f

def get_credentials():
    p = Path(f.topfolder / 'data/email.yaml')
    with open(p) as file:
        m = yaml.full_load(file)
    return m

def create_account(failcount=0):
    try:
        m = get_credentials()
        credentials = ex.Credentials(m['email'], m['password'])
        account = ex.Account(m['email'], credentials=credentials, autodiscover=True)
    except:
        print(f'Failed creating account: {failcount}')
        failcount +=1
        if failcount <=3:
            account = create_account(failcount=failcount)
    
    return account

def get_account():
    account = create_account()
    return account
