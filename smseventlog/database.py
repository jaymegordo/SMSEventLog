import json
import sys
import logging
from datetime import (datetime as dt, timedelta as delta)
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
from . import queries as qr

global db
log = logging.getLogger(__name__)
# DATABASE

def str_conn():
    # if not 'linux' in sys.platform and not f.check_db():
    #     return
    m = f.get_db()
    db_string = ';'.join('{}={}'.format(k, v) for k, v in m.items())
    params = parse.quote_plus(db_string)
    return f'mssql+pyodbc:///?odbc_connect={params}'
    
def get_engine():
    # sqlalchemy.engine.base.Engine
    return sa.create_engine(str_conn(), fast_executemany=True, pool_pre_ping=True)

class DB(object):
    def __init__(self):
        __name__ = 'SMS Event Log Database'
        engine = None
        session = None

        # TODO: should put these into a better table store
        df_unit = None
        df_fc = None
        df_component = None
        dfs = {}
        
        try:
            engine = get_engine()

            # create session, this is for the ORM part of sqlalchemy
            session = sessionmaker(bind=engine)()
        except:
            msg = 'Couldnt create engine'
            f.send_error(msg=msg)
            log.error(msg)
        
        f.set_self(self, vars())
        
    def get_engine(self):
        if not self.engine is None:
            return self.engine
        else:
            msg = 'Database not initialized.'
            # try:
            #     from .gui.dialogs import dialogs as dlgs
            #     dlgs.msg_simple(msg=msg, icon='Critical')
            # except:
            log.error('Engine is None!')
        
    def close(self):
        try:
            self.get_engine().raw_connection().close()
        except:
            log.error('Closing raw_connection')

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
            f.send_error()
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
                log.error(e)
        
        return cursor

    def read_query(self, q):
        return pd.read_sql(sql=q.get_sql(), con=self.get_engine())

    def getUnit(self, serial, minesite=None):
        df = self.get_df_unit(minesite=minesite)
        
        return df.Unit.loc[df.Serial == serial].values[0]
    
    def get_df(self, query, refresh=True, default=False):
        # get df by name and save for later reuse
        dfs = self.dfs
        title = query.title
        df = dfs.get(title, None)

        if default and hasattr(query, 'set_default_filter'):
            query.set_default_filter()

        if df is None or refresh:
            try:
                query.fltr.print_criterion()
                df = pd.read_sql(sql=query.get_sql(), con=self.get_engine()).pipe(f.parse_datecols)
                df.columns = f.convert_list_db_view(title=title, cols=df.columns)

                if hasattr(query, 'process_df'):
                    df = query.process_df(df=df)

                dfs[title] = df
                query.set_fltr() # reset filter after every refresh call
            except:
                msg = 'Couldn\'t get dataframe.'
                f.send_error(msg=msg)
                log.error(msg)
                df = pd.DataFrame()

        return df

    def get_unit_val(self, unit, field):
        # TODO: bit messy, should have better structure to get any val from saved table
        self.set_df_unit()
        dfu = self.df_unit

        return dfu.loc[unit, field]

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
            
        self.df_unit = pd.read_sql(sql=q.get_sql(), con=self.get_engine()).set_index('Unit', drop=False).pipe(f.parse_datecols)

    def get_df_fc(self):
        if self.df_fc is None:
            self.set_df_fc()
        
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
            
        self.df_fc = self.read_query(q=q)
    
    def get_df_component(self):
        if self.df_component is None:    
            a = pk.Table('ComponentType')
            q = Query.from_(a).select('*')
            self.df_component = self.read_query(q=q)

        return self.df_component

    def import_df(self, df, imptable, impfunc, notification=True, prnt=False):
        rowsadded = 0
        if df is None:
            f.discord(msg='No rows to import', channel='sms')
            return

        try:
            df.to_sql(name=imptable, con=self.get_engine(), if_exists='append', index=False)

            cursor = self.get_cursor()
            rowsadded = cursor.execute(impfunc).rowcount
            cursor.commit()
        except:
            f.send_error()

        msg = f'{imptable}: {rowsadded}'
        if prnt: print(msg)
        log.info(msg)

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
        
        return dt.combine(val, dt.min.time())
        

print(f'{__name__}: loading db')
db = DB()
