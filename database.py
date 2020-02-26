import sys
from urllib import parse

import pandas as pd
import pypika as pk
import sqlalchemy as sa

import pyodbc

global db

# DATABASE

def strConn():
    # TODO: import this from config file and encrypt
    driver = '{ODBC Driver 17 for SQL Server}'
    server = 'tcp:jgazure1.database.windows.net,1433'
    database = 'db1'
    username = 'jgordon@jgazure1'
    password = 'Z%^7wdpf%Nai=^ZFy-U.'
    return 'DRIVER={};SERVER={};DATABASE={};UID={};PWD={}'.format(driver, server, database, username, password)

def engine():
    # sqlalchemy.engine.base.Engine
    params = parse.quote_plus(strConn())
    return sa.create_engine(f'mssql+pyodbc:///?odbc_connect={params}', fast_executemany=True, pool_pre_ping=True)

class DB(object):
    def __init__(self):
        self.df_unit = None
        self.engine = engine()
        
        # self.conn.raw_connection().autocommit = True  # doesn't seem to work rn
        # self.cursor = self.conn.raw_connection().cursor()
        self.__name__ = 'SMS Event Log Database'
        
    def close(self):
        try:
            self.engine.raw_connection().close()
            # self.conn.close()
            # self.cursor.close()
        except:
            pass
            # try:
            #     self.engine.raw_connection().close()
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
            return self.engine.raw_connection().cursor()

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
            
        self.df_unit = pd.read_sql(sql=q.get_sql(), con=self.engine)
        
    # def dfUnit(self):
    #     # old?
    #     import sqlalchemy as sa
    #     engine = db.conn
    #     metadata = sa.MetaData()

    #     tbl = sa.Table('UnitID', metadata, autoload_with=engine)

    #     cl = tbl.columns
    #     sql = sa.select([cl.MineSite, cl.Model, cl.Unit, cl.Serial, cl.DeliveryDate]) \
    #         .where(sa.and_(cl.MineSite=='FortHills', cl.Model.like('%980E%')))
    #     df = pd.read_sql_query(sql=sql, con=engine)
        
    # def columns(self, tbl, cols):
    #     # return tbl column objects from list of col names
    #     return [col for col in tbl.columns if col.key in cols]

# check if db connection is still open
print('{}: loading db'.format(__name__))
db = DB()
