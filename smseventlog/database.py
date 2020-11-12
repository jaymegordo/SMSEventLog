import socket
from urllib import parse

import pyodbc
import yaml
from sqlalchemy import create_engine, exc
from sqlalchemy.engine.base import Connection  # just to wrap errors
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool.base import Pool

from . import errors as er
from . import functions as f
from .__init__ import *
from .utils.secrets import SecretsManager

global db
log = getlog(__name__)
# DATABASE

# TODO Need to re implement error wrapping. Need to either only wrap specific high-level session funcs, or call everything through a custom db method.

def wrap_single_class_func(cls, func_name, err_func):
    func = getattr(cls, func_name)
    setattr(cls, func_name, err_func(func))

def wrap_connection_funcs():
    # try to wrap specific sqlalchemy class funcs in error handler to reset db connection on disconnects
    # NOTE may need to wrap more than just this
    
    funcs = [
        (Connection, 'execute'),
        (Pool, 'connect')]
    
    for cls, func_name in funcs:
        wrap_single_class_func(cls=cls, func_name=func_name, err_func=e)

def get_db_creds():
    m = SecretsManager('db.yaml').load
    
    m['driver'] = None
    avail_drivers = pyodbc.drivers()
    preferred_drivers = [
        'ODBC Driver 17 for SQL Server',
        'SQL Server',
        'SQL Server Native Client 11.0']  

    # compare preferred drivers with existing, loop until match
    for driver in preferred_drivers:
        if driver in avail_drivers:
            m['driver'] = f'{{{driver}}}'
            break
    
    if not m['driver'] is None:
        log.info(f"driver: {m['driver']}")
        return m
    else:
        # raise error to user
        from .gui.dialogs import msg_simple
        msg_simple(icon='critical', msg="No database drivers available, please download 'ODBC Driver 17 for SQL Server' (or newer) from:\n\nhttps://www.microsoft.com/en-us/download/details.aspx?id=56567\n\n(NOTE: msodbcsql.msi - 4.5mb file is 64bit driver installer)")

        return None

def str_conn():
    m = get_db_creds()
    db_string = ';'.join('{}={}'.format(k, v) for k, v in m.items())
    params = parse.quote_plus(db_string)
    return f'mssql+pyodbc:///?odbc_connect={params}'

def _create_engine():
    """Create sqla engine object
    - sqlalchemy.engine.base.Engine
    - Used in DB class and outside, eg pd.read_sql
    - any errors reading db_creds results in None engine"""

    # connect_args = {'autocommit': True}
    # , isolation_level="AUTOCOMMIT"

    return create_engine(
        str_conn(),
        fast_executemany=True,
        pool_pre_ping=True,
        pool_timeout=5,
        pool_recycle=3600)
        # connect_args={'Remote Query Timeout': 5})

def e(func):
    # exc.IntegrityError, 
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except exc.IntegrityError as e:
            log.warning(f'***** Re-raising: {type(e)}')
            raise
        except (exc.IntegrityError, exc.ProgrammingError, exc.StatementError, pyodbc.ProgrammingError) as e:
            log.warning(f'***** Not handling error: {type(e)}')

            # print(f'Error message:\n\n{e}') # sqlalchemy wraps pyodbc.IntegreityError and returns msg as string

            db.rollback()
            return None # re raising the error causes sqlalchemy to catch it and raise more errors

        except exc.InvalidRequestError as e:
            # rollback invalid transaction
            log.warning(f'Rollback and retry operation: {type(e)}')
            db.rollback()
            return func(*args, **kwargs)
            
        except (exc.OperationalError, exc.DBAPIError, exc.ResourceClosedError) as e:
            log.warning(f'Handling {type(e)}')
            db.reset()
            return func(*args, **kwargs)

        except Exception as e:
            log.warning(f'Handling other errors: {type(e)}')
            db.reset()
            return func(*args, **kwargs)

    return wrapper

class DB(object):
    def __init__(self):
        __name__ = 'SMS Event Log Database'
        print(f'Initializing database')
        self.reset(False)
        
        df_unit = None
        df_fc = None
        df_component = None
        dfs = {}
        domain_map = dict(SMS='KOMATSU', Cummins='CED', Suncor='NETWORK')
        domain_map_inv = f.inverse(m=domain_map)
        last_internet_success = dt.now() + delta(seconds=-61)
        f.set_self(vars())
    
    def check_internet(self, host="8.8.8.8", port=53, timeout=3, recheck_time=60):
        """
        Test if internet connection exists before attempting any database operations
        Host: 8.8.8.8 (google-public-dns-a.google.com)
        OpenPort: 53/tcp
        Service: domain (DNS/TCP)
        recheck_time : int, default 60
            only re-check every x seconds
        """
        # raise er.NoInternetError() # testing

        # Kinda sketch, but just avoid re-checking too frequently
        if (dt.now() - self.last_internet_success).seconds < recheck_time:
            return True

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, port))
            s.shutdown(socket.SHUT_RDWR)
            s.close()
            self.last_internet_success = dt.now()
            return True
        except socket.error as ex:
            raise er.NoInternetError()

    def rollback(self):
        """Wrapper for session rollback"""
        try:
            self.session.rollback()
        except Exception as e:
            # not sure if this would be critical or can just be ignored yet
            log.warning(f'Failed to rollback session.: {type(e)}')
    
    def reset(self, warn=True):
        # set engine objects to none to force reset, not ideal
        if warn:
            log.warning('Resetting database.')

        self._engine, self._session, self._cursor = None, None, None
    
    def clear_saved_tables(self):
        # reset dfs so they are forced to reload from the db
        from .gui._global import update_statusbar
        self.dfs = {}
        update_statusbar('Saved database tables cleared.')
        
    @property
    def engine(self):
        self.check_internet()

        if self._engine is None:
            self._engine = _create_engine()
        
        if self._engine is None:
            raise er.SMSDatabaseError('Can\'t connect to database.')

        return self._engine

    @property
    def cursor(self):
        """Raw cursor used for db operations other than refreshing main tables"""
        def _get_cursor():
            return self.engine.raw_connection().cursor()

        try:
            try:
                self._cursor = _get_cursor()
            except (pyodbc.ProgrammingError, pyodbc.OperationalError) as e:
                self.reset() # retry onece to clear everything then try again
                self._cursor = _get_cursor()
        except Exception as e:
            raise er.SMSDatabaseError('Couldn\'t create cursor.') from e
        
        return self._cursor

    @property
    def session(self):
        self.check_internet() # need to call every time in case using _session
        if self._session is None:
            try:
                # create session, this is for the ORM part of sqlalchemy
                self._session = sessionmaker(bind=self.engine)()
                # TODO wrap session methods to retry?

            except Exception as e:
                raise er.SMSDatabaseError('Couldn\'t create session.') from e

        return self._session

    @er.errlog('Error closing raw_connection')
    def close(self):
        if self._engine is None: return
        self._engine.raw_connection().close()

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
    
    def safe_commit(self, fail_msg=None):
        session = self.session
        try:
            session.commit()
            return True
        except Exception as e:
            # wrapping all sqla funcs causes this error to be exc.ResourceClosedError, not IntegrityError
            if isinstance(e, pyodbc.IntegrityError):
                fail_msg = f'Can\'t add row to database, already exists!'

            if fail_msg is None:
                fail_msg = f'Failed to commit database transaction | {type(e)}'

            er.log_error(msg=fail_msg, log=log, display=True)
            session.rollback()
            return False

    def add_row(self, row):
        """Simple add single row to database.
        - Row must be created with sqlalchemy model"""
        self.session.add(row)
        return self.safe_commit()
        
    def read_query(self, q):
        return pd.read_sql(sql=q.get_sql(), con=self.engine)

    def get_unit(self, serial, minesite=None):
        df = self.get_df_unit(minesite=minesite)
        
        return df.Unit.loc[df.Serial == serial].values[0]
    
    def get_minesite(self, unit):
        df = self.get_df_unit()
        return df.loc[unit, 'MineSite']
    
    def get_smr(self, unit, date):
        a = T('UnitSMR')
        q = Query().from_(a).select('SMR') \
            .where(a.DateSMR==date) \
            .where(a.Unit==unit)
        return self.query_single_val(q)
    
    def get_smr_prev_co(self, unit, date, floc):
        a = T('EventLog')
        # cols = [a.Unit, a.Floc, a.SMR, a.DateAdded]
        q = Query().from_(a).select(a.SMR) \
            .where(a.Unit==unit) \
            .where(a.DateAdded<=date) \
            .where(a.Floc==floc) \
            .orderby(a.DateAdded, order=Order.desc)
        
        return self.query_single_val(q)

    def get_df_saved(self, name):
        # Return df from saved, TODO load if doesn't exist?
        return self.dfs.get(name, None)
    
    def save_df(self, df, name):
        self.dfs[name] = df

    def get_df(self, query, refresh=True, default=False, base=False, prnt=False, **kw) -> pd.DataFrame:
        """Load df from database, must call with query object.

        Parameters
        ----------
        query : QueryBase\n
        refresh : bool, optional
        
        - Not used, by default True\n
        default : bool, optional
        - Pass **kw through to query.set_default_filter if default=True, by default False\n
        base : bool, optional
            [description], by default False\n
        prnt : bool, optional
            Print query sql, by default False\n

        Returns
        -------
        pd.DataFrame
        """
        dfs = self.dfs
        title = query.title
        df = dfs.get(title, None)

        if default and hasattr(query, 'set_default_filter'):
            query.set_default_filter(**kw)

        if base and hasattr(query, 'set_base_filter'):
            query.set_base_filter(**kw)

        if df is None or refresh:
            try:
                sql = query.get_sql(**kw)
                if sql is None:
                    log.warning('No sql to get dataframe.')
                    return
                
                if prnt: print(sql)

                df = pd \
                    .read_sql(sql=sql, con=self.engine) \
                    .pipe(f.parse_datecols) \
                    .pipe(f.convert_int64) \
                    .pipe(f.convert_df_view_cols, m=query.view_cols) \
                    .pipe(f.set_default_dtypes, m=query.default_dtypes)

                query.fltr.print_criterion()

                if hasattr(query, 'process_df'):
                    df = query.process_df(df=df)

                dfs[title] = df
            except Exception as e:
                msg = f'Couldn\'t get dataframe: {query.name}'
                er.log_error(msg=msg, exc=e, log=log, display=True)
                df = pd.DataFrame()

            query.set_fltr() # reset filter after every refresh call

        return df

    def get_unit_val(self, unit, field):
        # TODO bit messy, should have better structure to get any val from saved table
        self.set_df_unit()

        try:
            return self.df_unit.loc[unit.strip(), field]
        except KeyError:
            log.warning(f'Couldn\'t get unit "{unit}" in unit table.')
            return None
    
    def unit_exists(self, unit):
        self.set_df_unit()
        return unit in self.df_unit.Unit
    
    def get_modelbase(self, model):
        df = self.get_df_equiptype()
        try:
            return df.loc[model].ModelBase
        except KeyError:
            # model not in database
            return None
    
    def get_df_equiptype(self):
        if not hasattr(self, 'df_equiptype') or self.df_equiptype is None:
            self.set_df_equiptype()
        
        return self.df_equiptype

    def unique_units(self):
        df = self.get_df_unit()
        return df.Unit.unique()
    
    def filter_database_units(self, df, col='Unit'):
        """Filter dataframe to only units in database"""
        return df[df[col].isin(self.unique_units())]

    def get_df_emaillist(self, force=False):
        name = 'emaillist'
        df = self.get_df_saved(name)

        if df is None or force:
            from .queries import EmailList
            query = EmailList()
            df = query.get_df()
            self.save_df(df, name)
        
        return df

    def get_email_list(self, name, minesite, usergroup=None):
        """Get list of emails from db for specified name eg 'WO Request'
        - NOTE not used, just use EmailListShort to refresh on every call"""
        if usergroup is None: usergroup = 'SMS'
        df = self.get_df_emaillist()
        
        return list(df[
            (df.MineSite==minesite) &
            (df.UserGroup==usergroup) &
            (df[name].str.lower()=='x')].Email)

    def get_df_issues(self, force=False):
        name = 'issues'
        df = self.get_df_saved(name)

        if df is None or force:
            df = pd.read_csv(f.resources / 'csv/issue_categories.csv')
            self.save_df(df, name)
        
        return df
    
    def get_issues(self):
        df = self.get_df_issues()
        return f.clean_series(df.category)
    
    def get_sub_issue(self, issue):
        df = self.get_df_issues()
        return list(df.sub_category[df.category==issue])

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
        a, b = pk.Tables('UnitID', 'EquipType')
        cols = [a.MineSite, a.Customer, a.Model, a.Unit, a.Serial, a.DeliveryDate, b.EquipClass, b.ModelBase]
        q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('Model')
            
        self.df_unit = pd.read_sql(sql=q.get_sql(), con=self.engine) \
            .set_index('Unit', drop=False) \
            .pipe(f.parse_datecols)
        
    def set_df_equiptype(self):
        a = T('EquipType')
        q = Query().from_(a).select(a.star)
        self.df_equiptype = pd.read_sql(sql=q.get_sql(), con=self.engine) \
            .set_index('Model', drop=False)

    def get_df_fc(self):
        if self.df_fc is None:
            self.set_df_fc()
        
        return self.df_fc

    def set_df_fc(self):
        from .queries import FCOpen
        self.df_fc = FCOpen().get_df()
    
    def get_df_component(self):
        name = 'component'
        df = self.get_df_saved(name)

        if df is None:    
            a = T('ComponentType')
            q = Query.from_(a).select('*')
            df = self.read_query(q=q)
            df['Combined'] = df[['Component', 'Modifier']].apply(
                lambda x: f'{x[0]}, {x[1]}' if not x[1] is None else x[0], axis=1)
            
            self.save_df(df, name)

        return df

    @er.errlog('Failed to import dataframe')
    def import_df(self, df, imptable, impfunc, notification=True, prnt=False, chunksize=None, index=False):
        rowsadded = 0
        if df is None or len(df) == 0:
            fmt = '%Y-%m-%d %H:%M'
            f.discord(msg=f'{dt.now().strftime(fmt)} - {imptable}: No rows to import', channel='sms')
            return

        # .execution_options(autocommit=True)
        df.to_sql(name=imptable, con=self.engine, if_exists='append', index=index, chunksize=chunksize)

        cursor = self.cursor
        rowsadded = cursor.execute(impfunc).rowcount
        cursor.commit()

        msg = f'{imptable}: {rowsadded}'
        if prnt: print(msg)
        log.info(msg)

        if notification:
            f.discord(msg=msg, channel='sms')
        
        return rowsadded
    
    def query_single_val(self, q):
        return self.cursor.execute(q.get_sql()).fetchval()
    
    def max_date_db(self, table=None, field=None, q=None, join_minesite=True, minesite='FortHills'):
        a = T(table)
        b = T('UnitID')

        if q is None:
            q = a.select(fn.Max(a[field]))
        
            if join_minesite:
                q = q.left_join(b).on_field('Unit') \
                .where(b.MineSite == minesite)
        
        val = self.query_single_val(q)
        
        return f.convert_date(val)

db = DB()
