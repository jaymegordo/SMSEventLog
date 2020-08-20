from .__init__ import *
from .__init__ import __version__
from . import functions as f
from . import dbtransaction as dbt
from .dbmodel import UserSettings
from .database import db

# TODO drop hours/filepath/Version from UserSettings table

class User():
    def __init__(self, username, mainwindow=None):
        row, _e = None, None
        dbtable = UserSettings
        domain = os.environ.get('userdomain', None)
        new_user = False

        if not mainwindow is None:
            s = mainwindow.settings
            email = s.value('email')
        else:
            email = ''

        f.set_self(vars())
    
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
        e.Ver = __version__ # NOTE this might move
        e.NumOpens += 1
        e.Domain = self.domain
    
    def login(self):
        # create user row in UserSettings if doesn't exist
        e = self.e
        self.update_vals(e=e)

        # no user in db
        if self.new_user:
            db.session.add(e)

        db.session.commit()

        return self


        
