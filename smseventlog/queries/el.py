from .__init__ import *

log = getlog(__name__)


class EventLogBase(QueryBase):
    def __init__(self, da=None, **kw):
        super().__init__(da=da, **kw)
        a, b, c = self.select_table, T('UnitID'), T('UserSettings')
        date_col = 'DateAdded'

        q = Query.from_(a) \
            .left_join(b).on_field('Unit') \
            .left_join(c).on(a.CreatedBy==c.UserName)

        f.set_self(vars())

        self.default_dtypes.update(
            **f.dtypes_dict('Int64', ['SMR', 'Unit SMR', 'Comp SMR', 'Part SMR', 'Pics']),
            **f.dtypes_dict('bool', ['Comp CO']))
    
    def set_base_filter(self, **kw):
        self.set_minesite()
        self.set_usergroup(**kw)

    def set_default_filter(self, **kw):
        self.set_base_filter(**kw)
        self.set_allopen(**kw)
    
    def set_usergroup(self, usergroup=None, **kw):
        if usergroup is None: return
        self.fltr.add(field='UserGroup', val=usergroup, table='UserSettings')

class EventLog(EventLogBase):
    def __init__(self, **kw):
        super().__init__(**kw)
        a, b = self.a, self.b

        cols = [a.UID, a.PassoverSort, a.StatusEvent, a.Unit, a.Title, a.Description, a.FailureCause, a.DateAdded, a.DateCompleted, a.IssueCategory, a.SubCategory, a.Cause, a.CreatedBy, a.TimeCalled]

        q = self.q \
            .orderby(a.DateAdded, a.Unit)
        
        f.set_self(vars())
    
    def set_allopen(self, **kw):
        a = self.a
        ct = ((a.StatusEvent != 'complete') | (a.PassoverSort.like('x')))
        self.fltr.add(ct=ct)

class WorkOrders(EventLogBase):
    def __init__(self, **kw):
        super().__init__(**kw)
        a, b = self.a, self.b

        cols = [a.UID, a.StatusWO, a.WarrantyYN, a.WorkOrder, a.Seg, a.SuncorWO, a.SuncorPO, b.Model, a.Unit, b.Serial, a.Title, a.PartNumber, a.SMR, a.DateAdded, a.DateCompleted, a.CreatedBy, a.WOComments, a.ComponentCO, a.Pictures]

        q = self.q \
            .orderby(a.DateAdded, a.Unit)

        f.set_self(vars())    
   
    def set_allopen(self, **kw):
        self.fltr.add(field='StatusWO', val='open')

class TSI(EventLogBase):
    def __init__(self, **kw):
        super().__init__(**kw)
        a, b = self.a, self.b

        cols = [a.UID, a.StatusTSI, a.DateAdded, a.TSINumber, a.WorkOrder, b.Model, a.Unit, b.Serial, a.Title, a.SMR, a.ComponentSMR, a.TSIPartName, a.PartNumber, a.SNRemoved, a.FailureCause, a.TSIDetails, a.TSIAuthor, a.Pictures]
        
        q = self.q \
            .orderby(a.DateAdded, a.Unit)

        f.set_self(vars())

    def set_allopen(self, **kw):
        self.fltr.add(field='StatusTSI', val='closed', opr=op.ne)
    
    def set_fltr(self):
        super().set_fltr()
        self.fltr.add(field='StatusTSI', term='notnull')

class UnitInfo(QueryBase):
    def __init__(self, **kw):
        super().__init__(**kw)
        a = self.select_table
        isNumeric = cf('ISNUMERIC', ['val'])
        left = cf('LEFT', ['val', 'num'])

        c, d = pk.Tables('UnitSMR', 'EquipType')

        days = fn.DateDiff(PseudoColumn('day'), a.DeliveryDate, fn.CurTimestamp())
        remaining = Case().when(days<=365, 365 - days).else_(0).as_('Remaining')
        remaining2 = Case().when(days<=365*2, 365*2 - days).else_(0)

        ge_remaining = Case().when(isNumeric(left(a.Model, 1))==1, remaining2).else_(None).as_('GE_Remaining')

        b = c.select(c.Unit, fn.Max(c.SMR).as_('CurrentSMR'), fn.Max(c.DateSMR).as_('DateSMR')).groupby(c.Unit).as_('b')

        cols = [a.MineSite, a.Customer, d.EquipClass, a.Model, a.Serial, a.Unit, b.CurrentSMR, b.DateSMR, a.DeliveryDate, remaining, ge_remaining]

        q = Query.from_(a) \
            .left_join(b).on_field('Unit') \
            .left_join(d).on_field('Model') \
            .orderby(a.MineSite, a.Model, a.Unit)
        
        f.set_self(vars())

    def set_default_filter(self, **kw):
        self.fltr.add(vals=dict(MineSite=self.minesite))

class EmailList(QueryBase):
    def __init__(self, **kw):
        """Full table for app display/editing, NOT single list for emailing"""
        super().__init__(**kw)
        a = self.select_table
        cols = [a.UserGroup, a.MineSite, a.Email, a.Passover, a.WORequest, a.FCCancelled, a.PicsDLS, a.PRP, a.FCSummary, a.TSI, a.RAMP, a.Service, a.Parts, a.AvailDaily, a.AvailReports]

        q = Query.from_(a) \
            .orderby(a.UserGroup, a.MineSite, a.Email)
        
        f.set_self(vars())

    def set_default_filter(self, usergroup=None, **kw):
        self.fltr.add(vals=dict(MineSite=f'{self.minesite}*')) # TODO remove 'like' eventually
        
        if usergroup is None: usergroup = 'SMS'
        self.fltr.add(field='UserGroup', val=usergroup)
    
    def process_df(self, df):
        # TODO remove this replace, temp till _cwc can be removed
        if not 'MineSite' in df.columns:
            return df # EmailListShort doesnt use this col

        df.MineSite = df.MineSite.replace(dict(_CWC='', _AHS=''), regex=True)
        return df

class EmailListShort(EmailList):
    def __init__(self, col_name: str, minesite: str, usergroup: str='SMS', **kw):
        """Just the list we actually want to email

        Parameters
        ---
        name : str,
            column name to filter for 'x'\n
        minesite : str\n
        usergroup : str, default SMS\n

        Examples
        ---
        >>> email_list = EmailListShort(col_name='Passover', minesite='FortHills', usergroup='SMS').emails
        >>> ['johnny@smsequip.com', 'timmy@cummins.com']
        """
        super().__init__(**kw)
        a = self.a
        cols = [a.Email]

        q = Query.from_(a)

        f.set_self(vars())
    
    def set_default_filter(self, **kw):
        # Convert view headers to db headers before query
        col_name = f.convert_header(title=self.title, header=self.col_name)
        self.fltr.add(vals={col_name: 'x'})
        
        super().set_default_filter(usergroup=self.usergroup, **kw)
    
    @property
    def emails(self) -> list:
        """Return the actual list of emails"""
        self.set_default_filter() # calling manually instead of passing default=True to be more explicit here
        df = self.get_df(prnt=True)
        try:
            return list(df.Email)
        except:
            log.warning('Couldn\'t get email list from database.')
            return []

class UserSettings(QueryBase):
    def __init__(self, parent=None, **kw):
        super().__init__(parent=parent, **kw)
        a = self.select_table
        cols = [a.UserName, a.Email, a.LastLogin, a.Ver, a.Domain, a.UserGroup, a.MineSite]
        q = Query.from_(a) \
            .orderby(a.LastLogin, order=Order.desc)

        f.set_self(vars())
