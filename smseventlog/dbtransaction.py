from logging import warn
import sqlalchemy as sa
from sqlalchemy import and_, literal
from sqlalchemy.orm.exc import NoResultFound

from . import functions as f
from . import errors as er
from .__init__ import *
from .database import db
from .utils import dbmodel as dbm

log = getlog(__name__)

class DBTransaction():
    def __init__(self, table_model=None, dbtable=None, title=None, table_view=True, table_widget=None, **kw):
        """Database transaction object for bulk updates/deletes etc
        - need dbtable, df or list of dicts containing appropriate pks and vals to update

        Parameters
        ----------
        table_model : smseventlog.gui.tables.TableWidget, optional
            table model from tables.py, default None
        dbtable : dbm.Base, optional
            dbtable definition not instance, default None
        title : str, optional
            table view title used for converting between db and table_view column names, default None
        table_view : bool, optional
            pass in False if cols are already in db view, default True

        Raises
        ------
        AttributeError
            [description]
        """
        
        update_items = []

        if not table_model is None:
            table_widget = table_model.table_widget
            title = table_widget.title
            dbtable = table_widget.get_dbtable()
        
        if dbtable is None: raise AttributeError('dbtable cannot be none!')

        pks = get_dbtable_keys(dbtable)

        # convert db to view cols first
        all_cols = f.convert_list_db_view(title=title, cols=pks) if table_view else pks
        
        f.set_self(vars())

    def update_statusbar(self, msg, *args, **kw):
        if not self.table_widget is None:
            self.table_widget.mainwindow.update_statusbar(msg=msg, *args, **kw)
            
        print(msg)

    def add_df(self, df, update_cols=None):
        """Add full or sliced df to update queue"""
        if not update_cols is None:
            if not isinstance(update_cols, list): update_cols = [update_cols]
            self.all_cols.extend(update_cols)

        # pass in df with all rows to update, then filter update_cols + pk_cols
        df = df[self.all_cols]

        if self.table_view:
            df = f.convert_df_db_cols(title=self.title, df=df)

        self.update_items = df.to_dict(orient='records')

        return self
    
    def add_items(self, update_items):
        # update_items is list of dicts
        # convert all view cols to db cols
        self.update_items = [f.convert_dict_db_view(title=self.title, m=item, output='db') for item in update_items]

        return self

    def add_row(self, irow):
        """Add single row by index number from table
        - NOTE probably need to work with values passed in manually, maybe won't use this, df is pretty gr8"""
        df = self.df

        # convert all col_ixs to db_field names and attach values to update
        m = {}
        for icol in self.col_nums:
            view_header = df.columns[icol]
            db_field = f.convert_header(title=self.title, header=view_header, inverse_=True)
            m[db_field] = df.iloc[irow, icol]
        
        self.update_items.append(m)
    
    def update_all(self, operation_type='update'):
        s = db.session
        txn_func = getattr(s, f'bulk_{operation_type}_mappings')
        txn_func(self.dbtable, self.update_items)

        num_recs = len(self.update_items)
        if num_recs == 0:
            log.info(f'No records to update.')
            return
            
        msg = f'Bulk {operation_type} records: {num_recs}'

        if db.safe_commit():
            self.update_statusbar(msg, success=True)
        else:
            msg = f'Failed: {msg}'
            self.update_statusbar(msg, warn=True)

        return self
    
    def print_items(self):
        print(self.update_items)
        return self

class Row():
    def __init__(self, table_model=None, i=None, col=None, keys=None, dbtable=None, df=None, title=None):
        # create with either: 1. gui.Table + row, or 2. dbtable + keys/values
        # tbl = gui.Table class > the 'model' in mvc
        if keys is None: keys = {} # don't know why, but set_self doesnt work if keys={}
        
        if not table_model is None:
            df = table_model.df
            title = table_model.table_widget.title
            if dbtable is None:
                dbtable = table_model.table_widget.get_dbtable() # dbm.TableName = table definition, NOT table object (eg TableName())
        
        if dbtable is None:
            raise AttributeError('db model table not set!')
        
        pks = get_dbtable_keys(dbtable) # list of pk field names eg ['UID']

        if not (i is None and col is None): # update keys from df
            if df is None:
                raise AttributeError('df not set!')

            for pk in pks:
                if not i is None:
                    header = f.convert_header(title=title, header=pk, inverse_=True)
                    keys[pk] = df.iloc[i, df.columns.get_loc(header)] # get key value from df, key must exist in df
                elif col:
                    keys[pk] = df.loc[pk, col] # transposed df from Details dialog, all fields are db_cols eg 'FCNumber' not 'FC Number'

        f.set_self(vars())

    @classmethod
    def example(cls, uid=None, e=True):
        """Create instance of self with uid, only for EventLog table"""
        if uid is None:
            uid = 12602260565

        row = cls(keys=dict(UID=uid), dbtable=dbm.EventLog)

        if e:
            return row.create_model_from_db()
        else:
            return row

    def update_single(self, val, header=None, field=None, check_exists=False):
        # convenience func to update single field/header: val in db
        # convert table header to db field name
        if field is None:
            field = f.convert_header(title=self.title, header=header)
        
        self.update(vals={field: val}, check_exists=check_exists)

    def update(self, vals=None, delete=False, check_exists=False):
        """Update (multiple) values in database, based on unique row, field, value, and primary keys(s)
        - key must either be passed in manually or exist in current table's df"""
        t, keys = self.dbtable, self.keys

        if len(keys) == 0:
            raise AttributeError('Need to set keys before update!')
        
        session = db.session
        cond = [getattr(t, pk)==keys[pk] for pk in keys] # list of multiple key:value pairs for AND clause

        if not delete:
            if vals is None: raise AttributeError('No values to update!')
            sql = sa.update(t).values(vals).where(and_(*cond))
            print(sql)
        else:
            sql = sa.delete(t).where(and_(*cond)) # kinda sketch to even have this here..

        if not check_exists:
            session.execute(sql)
        else:
            # Check if row exists, if not > create new row object, update it, add to session, commit
            q = session.query(t).filter(and_(*cond))
            exists = session.query(literal(True)).filter(q.exists()).scalar()

            if not exists:
                e = t(**keys, **vals)
                session.add(e)
            else:
                session.execute(sql)
            
        return db.safe_commit() # True if transaction succeeded
    
    def create_model_from_db(self):
        """Query sqalchemy orm session using model eg dbo.EventLog, and keys eg {UID=123456789}

        Returns
        ------
            instance of model
        """
        return db.session.query(self.dbtable).get(self.keys)

    def printself(self):
        m = dict(
            title=self.tbl.title,
            table=self.tbl.tablename,
            pk=self.pk,
            id=self.id)
        # display(m)
        print(m)

def select_row_by_secondary(dbtable, col, val):
    # select single row from table by attr other than pk
    try:
        return db.session.query(dbtable).filter(getattr(dbtable, col)==val).one()
    except NoResultFound:
        return None

def get_dbtable_key_vals(dbtable, vals):
    # return tuple of one or more keys in dbtable, given dict of all vals (including keys)
    # used for update queue so far
    pks = get_dbtable_keys(dbtable)
    key_tuple = tuple(vals[k] for k in pks)
    key_dict = {k:vals[k] for k in pks}
    return key_tuple, key_dict

def get_dbtable_keys(dbtable : dbm.Base) -> list:
    """Get list of dbtable keys

    Parameters
    ----------
    dbtable : dbm.Base
        eg dbm.FactoryCampaign

    Returns
    -------
    list
        list of dbtable pks eg ['Unit', 'FCNumber']
    """    
    return dbtable.__table__.primary_key.columns.keys()

def print_model(model, include_none=False):
    m = model_dict(model, include_none=include_none)
    try:
        # display(m)
        print(m)
    except:
        pass

def model_dict(model, include_none=False):
    # create dict from table model
    m = {a.key:getattr(model, a.key) for a in sa.inspect(model).mapper.column_attrs}
    if not include_none:
        m = {k:v for k,v in m.items() if v is not None}
    
    return m

def df_from_row(model):
    # convert single row model from db to df with cols as index (used to display all data single row)
    m = model_dict(model, include_none=True)
    df = pd.DataFrame.from_dict(m, orient='index', columns=['Value']) \
    
    df.index.rename('Fields', inplace=True)
    return df

def join_query(tables, keys, join_field):
    # pretty ugly, but used to use an sqlachemy join query and merge dict of results
    # tables is tuple/list of 2 tables
    # NOTE not actually used yet
    if not len(tables) == 2: raise AttributeError('"tables" must have 2 tables')

    session = db.session
    a, b = tables[0], tables[1]
    cond = getattr(a, join_field) == getattr(b, join_field) # condition for join eg a.Unit==b.Unit
    
    key = list(keys.keys())[0] # NOTE sketch, needs to be changed for multiple keys
    fltr_ = getattr(a, key) == keys[key] # eg a.UID==uid

    res = session.query(a, b).join(b, cond).filter(fltr_).one()

    m = {}
    for item in res:
        m.update(model_dict(item, include_none=True))

    return m
