from urllib import parse

import pyodbc
import yaml
from sqlalchemy import create_engine, exc
from sqlalchemy.engine.base import Connection  # just to wrap errors
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool.base import Pool

from . import functions as f
from .__init__ import *

global db
log = logging.getLogger(__name__)
# DATABASE

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
    # if not check_db(): return
    p = f.datafolder / 'db.yaml'
    with open(p) as file:
        m = yaml.full_load(file)
    
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
    
    # raise error to user
    if not m['driver'] is None:
        print(m['driver'])
        return m
    else:
        from .gui.dialogs import msg_simple
        msg_simple(icon='critical', msg="No database drivers available, please download 'ODBC Driver 17 for SQL Server' (or newer) from:\n\nhttps://www.microsoft.com/en-us/download/details.aspx?id=56567\n\n(msodbcsql.msi - 4.5mb file is 64bit driver installer)")

        return None

def str_conn():
    m = get_db_creds()
    db_string = ';'.join('{}={}'.format(k, v) for k, v in m.items())
    params = parse.quote_plus(db_string)
    return f'mssql+pyodbc:///?odbc_connect={params}'
    
def _create_engine():
    # sqlalchemy.engine.base.Engine
    # connect_args = {'autocommit': True}
    # , isolation_level="AUTOCOMMIT"
    try:
        wrap_connection_funcs()
        engine = create_engine(str_conn(), fast_executemany=True, pool_pre_ping=True)   
        return engine
    except:
        # any errors reading db_creds results in None engine
        return None

def e(func):
    # NOTE not sure if any of these work yet
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (exc.StatementError, exc.InvalidRequestError) as e:
            # rollback invalid transaction
            log.warning(f'Rollback and retry operation: {type(e)}')
            session = db.session # this is pretty sketch
            session.rollback() # NOTE doesn't seem to actually work, gets called 10 times
            return func(*args, **kwargs)
            
        except (exc.OperationalError, exc.DBAPIError, exc.ResourceClosedError) as e:
            log.warning(f'Handling {type(e)}')
            db.reset()
            return func(*args, **kwargs)
        
        except exc.IntegrityError:
            raise

        except Exception as e:
            log.warning(f'Handling other errors: {type(e)}')
            db.reset()
            return func(*args, **kwargs)

    return wrapper

class DB(object):
    def __init__(self):
        __name__ = 'SMS Event Log Database'
        self.reset(False)
        
        # TODO: should put these into a better table store
        df_unit = None
        df_fc = None
        df_component = None
        dfs = {}
        domain_map = dict(Cummins='CED', Komatsu='KOMATSU', Suncor='NETWORK')
        domain_map_inv = f.inverse(m=domain_map)
        f.set_self(vars())
    
    def reset(self, warn=True):
        # set engine objects to none to force reset, not ideal
        if warn: log.warning('Resetting database')
        self._engine, self._session, self._cursor = None, None, None
    
    def clear_saved_tables(self):
        # reset dfs so they are forced to reload from the db
        from .gui._global import update_statusbar
        self.dfs = {}
        update_statusbar('Saved database tables cleared.')
        
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
                log.error(e, exc_info=True)
        
        return self._cursor

    @property
    def session(self):
        if self._session is None:
            try:
                # create session, this is for the ORM part of sqlalchemy
                self._session = sessionmaker(bind=self.engine)()
            except:
                msg = 'Couldnt create session'
                f.send_error(msg=msg, logger=log)

        return self._session

    def close(self):
        if self._engine is None: return

        try:
            self._engine.raw_connection().close()
        except:
            log.error('Error closing raw_connection', exc_info=True)

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
    
    def add_row(self, row):
        # simple add single row to database. row must be created with sqlalchemy model
        self.session.add(row)
        self.session.commit()
        
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

    def get_df(self, query, refresh=True, default=False, prnt=False):
        # get df by name and save for later reuse
        dfs = self.dfs
        title = query.title
        df = dfs.get(title, None)

        if default and hasattr(query, 'set_default_filter'):
            query.set_default_filter()

        if df is None or refresh:
            try:
                sql = query.get_sql()
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
            except:
                msg = f'Couldn\'t get dataframe: {query.name}'
                f.send_error(msg=msg, logger=log)
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
        return df.loc[model].ModelBase
    
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
        """Get list of emails from db for specified name eg 'WO Request'"""
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
            df = pd.read_csv(f.datafolder / 'csv/issue_categories.csv')
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
        a = T('FactoryCampaign')
        b = T('FCSummary')
        c = T('UnitID')

        subject = Case().when(b.SubjectShort.notnull(), b.SubjectShort).else_(b.Subject).as_('Subject')

        cols = [a.FCNumber, a.Unit, c.MineSite, subject]
        q = Query.from_(a).select(*cols) \
            .left_join(b).on_field('FCNumber') \
            .left_join(c).on_field('Unit')
        
        df = self.read_query(q=q)
        df['Title'] = df.FCNumber + ' - ' + df.Subject
        self.df_fc = df
    
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
        except:
            f.send_error()
        finally:
            cursor.close()
    
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

print(f'{__name__}: loading db')
db = DB()
