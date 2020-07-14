from urllib import parse

import pyodbc
from sqlalchemy import exc, create_engine
from sqlalchemy.orm import Session, sessionmaker

from . import functions as f
from .__init__ import *

global db
log = logging.getLogger(__name__)
# DATABASE

def str_conn():
    m = f.get_db()
    db_string = ';'.join('{}={}'.format(k, v) for k, v in m.items())
    params = parse.quote_plus(db_string)
    return f'mssql+pyodbc:///?odbc_connect={params}'
    
def _create_engine():
    # sqlalchemy.engine.base.Engine
    # connect_args = {'autocommit': True}
    # , isolation_level="AUTOCOMMIT"
    engine = create_engine(str_conn(), fast_executemany=True, pool_pre_ping=True)

    # wrap .execute in @e error handler to retry connection after a disconnect
    for func_name in ['execute']:
        func = getattr(engine, func_name)
        setattr(engine, func_name, e(func))
    
    return engine

def e(func):
    # rollback invalid transaction
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (exc.StatementError, exc.InvalidRequestError):
            log.warning('Rollback and retry operation.')
            print('Rollback and retry operation.')
            session = db.session # this is pretty sketch
            session.rollback()
            return func(*args, **kwargs)

    return wrapper

class DB(object):
    def __init__(self):
        __name__ = 'SMS Event Log Database'
        _engine, _session, _cursor = None, None, None

        # TODO: should put these into a better table store
        df_unit = None
        df_fc = None
        df_component = None
        dfs = {}

        f.set_self(self, vars())
        
    @property
    def engine(self):
        if self._engine is None:
            self._engine = _create_engine()
        
        return self._engine

    @property
    def cursor(self):
        def get_cursor():
            return self.engine.raw_connection().cursor()

        try:
            self._cursor = get_cursor()
        except:
            f.send_error()
            e = sys.exc_info()[0]
            if e.__class__ == pyodbc.ProgrammingError:
                print(e)
                self.__init__()
                self._cursor = get_cursor()
            elif e.__class__ == pyodbc.OperationalError:
                print(e)
                self.__init__()
                self._cursor = get_cursor()
            else:
                log.error(e)
        
        return self._cursor

    @property
    def session(self):
        if self._session is None:
            try:
                # create session, this is for the ORM part of sqlalchemy
                self._session = sessionmaker(bind=self.engine)()
            except:
                msg = 'Couldnt create session'
                f.send_error(msg=msg)
                log.error(msg)

        return self._session

    def close(self):
        try:
            self.engine.raw_connection().close()
        except:
            log.error('Error closing raw_connection')

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        
    def read_query(self, q):
        return pd.read_sql(sql=q.get_sql(), con=self.engine)

    def get_unit(self, serial, minesite=None):
        df = self.get_df_unit(minesite=minesite)
        
        return df.Unit.loc[df.Serial == serial].values[0]
    
    def get_minesite(self, unit):
        df = self.get_df_unit()
        return df.loc[unit, 'MineSite']
    
    def get_df(self, query, refresh=True, default=False):
        # get df by name and save for later reuse
        dfs = self.dfs
        title = query.title
        df = dfs.get(title, None)

        if default and hasattr(query, 'set_default_filter'):
            query.set_default_filter()

        if df is None or refresh:
            try:
                # print(query.get_sql())
                df = pd \
                    .read_sql(sql=query.get_sql(), con=self.engine) \
                    .pipe(f.parse_datecols) \
                    .pipe(f.convert_int64) \
                    .pipe(f.convert_df_view_cols, m=query.view_cols) \
                    .pipe(f.set_default_dtypes, m=query.default_dtypes)

                query.fltr.print_criterion()

                if hasattr(query, 'process_df'):
                    df = query.process_df(df=df)

                dfs[title] = df
            except:
                msg = f'Couldn\'t get dataframe: {query.name}'
                f.send_error(msg=msg)
                log.error(msg)
                df = pd.DataFrame()

            query.set_fltr() # reset filter after every refresh call

        return df

    def get_unit_val(self, unit, field):
        # TODO: bit messy, should have better structure to get any val from saved table
        self.set_df_unit()
        dfu = self.df_unit

        return dfu.loc[unit, field]
    
    def unique_units(self):
        df = self.get_df_unit()
        return df.Unit.unique()

    def get_list_minesite(self):
        lst_minesite = getattr(self, 'lst_minesite', None)
        if lst_minesite is None:
            self.lst_minesite = f.clean_series(s=self.get_df_unit().MineSite)

        return self.lst_minesite
    
    def get_df_unit(self, minesite=None):
        if self.df_unit is None:
            self.set_df_unit()
        
        df = self.df_unit

        # sometimes need to filter other minesites due to serial number duplicates
        if not minesite is None:
            df = df[df.MineSite==minesite].copy()
        
        return df

    def set_df_unit(self):
        a = T('UnitID')
        cols = ['MineSite', 'Customer', 'Model', 'Unit', 'Serial', 'DeliveryDate']
        q = Query.from_(a).select(*cols)
            
        self.df_unit = pd.read_sql(sql=q.get_sql(), con=self.engine) \
            .set_index('Unit', drop=False) \
            .pipe(f.parse_datecols)

    def get_df_fc(self):
        if self.df_fc is None:
            self.set_df_fc()
        
        return self.df_fc

    def set_df_fc(self, minesite=None):
        a = T('FactoryCampaign')
        b = T('FCSummary')
        c = T('UnitID')

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
            a = T('ComponentType')
            q = Query.from_(a).select('*')
            df = self.read_query(q=q)
            df['Combined'] = df[['Component', 'Modifier']].apply(lambda x: f'{x[0]}, {x[1]}' if not x[1] is None else x[0], axis=1)

            self.df_component = df

        return self.df_component

    def import_df(self, df, imptable, impfunc, notification=True, prnt=False, chunksize=None, index=False):
        rowsadded = 0
        if df is None or len(df) == 0:
            fmt = '%Y-%m-%d %H:%M'
            f.discord(msg=f'{dt.now().strftime(fmt)} - {imptable}: No rows to import', channel='sms')
            return

        try:
            # .execution_options(autocommit=True)
            df.to_sql(name=imptable, con=self.engine, if_exists='append', index=index, chunksize=chunksize)

            cursor = self.cursor
            rowsadded = cursor.execute(impfunc).rowcount
            cursor.commit()
        except:
            f.send_error()

        msg = f'{imptable}: {rowsadded}'
        if prnt: print(msg)
        log.info(msg)

        if notification:
            f.discord(msg=msg, channel='sms')
        
        return rowsadded
    
    def query_single_val(self, q):
        try:
            cursor = self.cursor
            return cursor.execute(q.get_sql()).fetchval()
        finally:
            cursor.close()
    
    def max_date_db(self, table=None, field=None, q=None):
        minesite = 'FortHills'
        a = T(table)
        b = T('UnitID')

        if q is None:
            q = a.select(fn.Max(a[field])) \
                .left_join(b).on_field('Unit') \
                .where(b.MineSite == minesite)
        
        val = self.query_single_val(q)
        
        return dt.combine(val, dt.min.time())

print(f'{__name__}: loading db')
db = DB()
