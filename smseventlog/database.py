import json
import sys
from pathlib import Path
from urllib import parse

import pandas as pd
import pypika as pk
import sqlalchemy as sa
import yaml

import functions as f
import pyodbc
import userforms as uf

global db

# DATABASE

def strConn():
    if not f.check_db():
        return
    m = f.get_db()
    return ';'.join('{}={}'.format(k, v) for k, v in m.items())
    
def engine():
    # sqlalchemy.engine.base.Engine
    params = parse.quote_plus(strConn())
    return sa.create_engine(f'mssql+pyodbc:///?odbc_connect={params}', fast_executemany=True, pool_pre_ping=True)

class DB(object):
    def __init__(self):
        self.__name__ = 'SMS Event Log Database'
        self.df_unit = None
        self.engine = None

        try:
            self.engine = engine()
        except:
            pass
        
    def get_engine(self):
        if not self.engine is None:
            return self.engine
        else:
            uf.msg_simple(msg='Database not initialized.', icon='Critical')
        
    def close(self):
        try:
            self.get_engine().raw_connection().close()
            # self.conn.close()
            # self.cursor.close()
        except:
            pass
            # try:
            #     self.get_engine().raw_connection().close()
            # except:
            #     pass

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        
    def get_cursor(self):
        def setcursor():
            return self.get_engine().raw_connection().cursor()

        try:
            cursor = setcursor()
        except:
            e = sys.exc_info()[0]
            if e.__class__ == pyodbc.ProgrammingError:
                print(e)
                self.__init__()
                cursor = setcursor()
            elif e.__class__ == pyodbc.OperationalError:
                print(e)
                self.__init__()
                cursor = setcursor()
            else:
                print(e)
        
        return cursor


    def getUnit(self, serial, minesite=None):
        df = self.get_df_unit(minesite=minesite)
        
        return df.Unit.loc[df.Serial == serial].values[0]
    
    def get_df_unit(self, minesite=None):
        if self.df_unit is None:
            self.set_df_unit(minesite=minesite)
        
        return self.df_unit

    def set_df_unit(self, minesite=None):
        a = pk.Table('UnitID')
        cols = ['MineSite', 'Customer', 'Model', 'Unit', 'Serial']
        q = pk.Query.from_(a).select(*cols)
        
        if not minesite is None:
            q = q.where(a.MineSite == minesite)
            
        self.df_unit = pd.read_sql(sql=q.get_sql(), con=self.get_engine())
        

# check if db connection is still open
print('{}: loading db'.format(__name__))
db = DB()
