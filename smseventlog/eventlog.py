

import pandas as pd
import pypika as pk
import sqlalchemy as sa
from sqlalchemy import and_, literal

from . import functions as f
from .__init__ import *
from .database import db

try:
    from IPython.display import display
except ModuleNotFoundError:
    pass

log = logging.getLogger(__name__)

class DBTransaction():
    def __init__(self, table_model, update_cols):
        # bulk update values from table_model to database
        # need dbtable, df or list of dicts containing appropriate pks and vals to update
        if not isinstance(update_cols, list): update_cols = [update_cols]
        update_vals = []

        table_widget = table_model.table_widget
        title = table_widget.title
        dbtable = table_widget.get_dbtable()
        pks = dbtable.__table__.primary_key.columns.keys()

        all_cols = f.convert_list_db_view(title=title, cols=pks) # convert db to view cols first
        all_cols.extend(update_cols)

        f.set_self(self, vars())

    def add_df(self, df):
        # pass in df with all rows to update, then filter update_cols + pk_cols
        df = df[self.all_cols]
        df = f.convert_df_db_cols(title=self.title, df=df)
        self.update_vals = df.to_dict(orient='records')

    def add_row(self, row_ix):
        # TODO probably need to work with values passed in manually, maybe won't use this, df is pretty gr8
        df = self.df

        # convert all col_ixs to db_field names and attach values to update
        m = {}
        for col_ix in self.col_nums:
            view_header = df.columns[col_ix]
            db_field = f.convert_header(title=self.title, header=view_header, inverse_=True)
            m[db_field] = df.iloc[row_ix, col_ix]
        
        self.update_vals.append(m)
    
    def update_all(self):
        s = db.session
        s.bulk_update_mappings(self.dbtable, self.update_vals)
        s.commit()
        print(f'bulk update: {len(self.update_vals)}')

class Row():
    def __init__(self, table_model=None, i=None, keys=None, dbtable=None):
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

        pks = dbtable.__table__.primary_key.columns.keys() # list of pk field names eg ['UID']

        if not i is None: # update keys from df
            for pk in pks:
                header = f.convert_header(title=title, header=pk, inverse_=True)
                keys[pk] = df.iloc[i, df.columns.get_loc(header)] # get key value from df, key must exist in df

        f.set_self(self, vars())

    def update_single(self, val, header=None, field=None, check_exists=False):
        # convenience func to update single field/header: val in db
        
        # convert table header to db field name
        if field is None:
            field = f.convert_header(title=self.title, header=header)
        
        self.update(vals={field: val}, check_exists=check_exists)

    def update(self, vals={}, delete=False, check_exists=False):
        # update (multiple) values in database, based on unique row, field, value, and primary keys(s)
        # key must either be passed in manually or exist in current table's df
        try:
            t, keys = self.dbtable, self.keys

            if len(keys) == 0:
                raise AttributeError('Need to set keys before update!')
            
            session = db.session
            cond = [getattr(t, pk)==keys[pk] for pk in keys] # list of multiple key:value pairs for AND clause

            if not delete:
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
                
            session.commit()
        except:
            msg = f'Couldn\'t update value: {vals}'
            f.send_error(msg)
            log.error(msg)
    
    def create_model_from_db(self):
        # query sqalchemy orm session using model eg dbo.EventLog, and keys eg {UID=123456789}
        # return instance of model
        session = db.session
        e = session.query(self.dbtable).get(self.keys)

        return e

    def printself(self):
        m = dict(
            title=self.tbl.title,
            table=self.tbl.tablename,
            pk=self.pk,
            id=self.id)
        display(m)


def print_model(model, include_none=False):
    m = f.model_dict(model, include_none=include_none)
    display(m)