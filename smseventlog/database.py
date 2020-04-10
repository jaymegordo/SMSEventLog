import json
import sys
from datetime import (datetime as date, timedelta as delta)
from pathlib import Path
from urllib import parse

import pandas as pd
import pyodbc
import pypika as pk
from pypika import (
    Case,
    Criterion,
    CustomFunction as cf,
    Order,
    functions as fn,
    Query)
import sqlalchemy as sa
import yaml
from sqlalchemy.orm import sessionmaker

from . import functions as f

global db

# DATABASE

def strConn():
    if f.azure_env is None and not f.check_db():
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
        self.engine = None
        self.session = None
        self.df_unit = None
        self.df_fc = None

        try:
            self.engine = engine()

            # create session, this is for the ORM part of sqlalchemy
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
        except:
            print('error setting engine')
        
    def get_engine(self):
        if not self.engine is None:
            return self.engine
        else:
            msg = 'Database not initialized.'
            try:
                from . import gui as ui
                ui.msg_simple(msg=msg, icon='Critical')
            except:
                print('error setting engine')
        
    def close(self):
        try:
            self.get_engine().raw_connection().close()
            # self.conn.close()
            # self.cursor.close()
        except:
            print('error closing raw_connection')

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
        cols = ['MineSite', 'Customer', 'Model', 'Unit', 'Serial', 'DeliveryDate']
        q = Query.from_(a).select(*cols)
        
        if not minesite is None:
            q = q.where(a.MineSite == minesite)
            
        self.df_unit = pd.read_sql(sql=q.get_sql(), con=self.get_engine())

    def get_df_fc(self, minesite=None):
        if self.df_fc is None:
            self.set_df_fc(minesite=minesite)
        
        return self.df_fc

    def set_df_fc(self, minesite=None):
        a = pk.Table('FactoryCampaign')
        b = pk.Table('FCSummary')
        c = pk.Table('UnitID')

        subject = Case().when(b.SubjectShort.notnull(), b.SubjectShort).else_(b.Subject).as_('Subject')

        cols = [a.FCNumber, a.Unit, c.MineSite, subject]
        q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('FCNumber') \
            .left_join(c).on_field('Unit')
        
        if not minesite is None:
            q = q.where(c.MineSite == minesite)
            
        self.df_fc = pd.read_sql(sql=q.get_sql(), con=self.get_engine())

    def import_df(self, df, imptable, impfunc, notification=True):
        if df is None:
            f.discord(msg='No rows in email', channel='sms')
            return

        try:
            df.to_sql(imptable, con=self.get_engine(), if_exists='append', index=False)

            cursor = self.get_cursor()
            rowsadded = cursor.execute(impfunc).rowcount
            cursor.commit()
        except:
            f.senderror()
        finally:
            cursor.close()

        msg = '{} imported: {}\nAdded to database: {}'.format(imptable, len(df), rowsadded)
        print(msg)

        if notification:
            f.discord(msg=msg, channel='sms')
    
    def max_date_db(self, table, field):
        minesite = 'FortHills'
        a = pk.Table(table)
        b = pk.Table('UnitID')

        sql = a.select(fn.Max(a[field])) \
            .left_join(b).on_field('Unit') \
            .where(b.MineSite == minesite)
        
        try:
            cursor = db.get_cursor()
            val = cursor.execute(sql.get_sql()).fetchval()
        finally:
            cursor.close()
        
        return date.combine(val, date.min.time())
        

print('{}: loading db'.format(__name__))
db = DB()
