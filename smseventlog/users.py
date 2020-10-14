from . import dbtransaction as dbt
from . import functions as f
from . import errors as er
from .__init__ import *
from .database import db
from .utils.dbmodel import UserSettings

# TODO drop hours/filepath/Version from UserSettings table

log = getlog(__name__)

class User():
    def __init__(self, username, mainwindow=None):
        row, _e = None, None
        dbtable = UserSettings
        domain = os.getenv('userdomain', None)
        usergroup = db.domain_map_inv.get(domain, 'SMS')
        new_user = False
        admin = True if username in ('Jayme Gordon',) else False

        if not mainwindow is None:
            s = mainwindow.settings
            email = s.value('email', '')
            minesite = mainwindow.minesite
        else:
            email = ''
            minesite = ''

        # Disable everything for those idiots over at cummins
        is_cummins = True if (not domain is None and 'CED' in domain) or 'cummins' in email.lower() or usergroup == 'Cummins' else False
        
        f.set_self(vars())
    
    @classmethod
    def default(cls):
        return cls(username='Jayme Gordon')
    
    @property
    def e(self):
        # get existing user row from db, or create new 
        if self._e is None:
            self._e = self.load()
        
            if self._e is None:
                self._e = self.create_new_user()
                self.new_user = True
        
        return self._e

    def load(self):
        self.row = dbt.Row(dbtable=self.dbtable, keys=dict(UserName=self.username))
        return self.row.create_model_from_db()
    
    def create_new_user(self):
        e = self.dbtable()
        e.UserName = self.username
        e.Email = self.email
        e.NumOpens = 0

        return e
    
    def update_vals(self, e):
        e.LastLogin = dt.now()
        e.Ver = VERSION
        e.NumOpens += 1
        e.Domain = self.domain
        e.UserGroup = self.usergroup
        e.MineSite = self.minesite
    
    def login(self):
        # create user row in UserSettings if doesn't exist
        try:
            e = self.e
            self.update_vals(e=e)

            # no user in db
            if self.new_user:
                db.session.add(e)

            db.session.commit()
        except:
            er.log_error(msg='User failed to login.', log=log)
        finally:
            return self