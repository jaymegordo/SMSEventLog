

import pandas as pd
import pypika as pk
import sqlalchemy as sa
# from pypika import Case, Criterion
# from pypika import CustomFunction as cf
# from pypika import Order, Query
# from pypika import functions as fn
from sqlalchemy import and_, literal

from . import functions as f
from .__init__ import *
from .database import db

try:
    from IPython.display import display
except ModuleNotFoundError:
    pass

log = logging.getLogger(__name__)

class Row():
    def __init__(self, tbl=None, i=None, keys=None, dbtable=None):
        # create with either: 1. gui.Table + row, or 2. dbtable + keys/values
        # tbl = gui.Table class > the 'model' in mvc
        if keys is None: keys = {} # don't know why, but set_self doesnt work if keys={}
        
        if not tbl is None:
            df = tbl.df
            title = tbl.title
            if dbtable is None:
                dbtable = tbl.dbtable # dbm.TableName = table definition, NOT table object (eg TableName())
        
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