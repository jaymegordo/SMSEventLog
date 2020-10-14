import shutil

from . import functions as f
from .__init__ import *
from .database import db
from .dbtransaction import Row
from .utils import fileops as fl
from .utils.dbmodel import EventLog

log = getlog(__name__)

class UnitFolder(object):
    def __init__(self, unit : str):
        """Object that represents path to unit's base folder

        Parameters
        ---
        Unit: string

        Examples
        -------
        >>> uf = UnitFolder(unit='F301')
        >>> uf.p_unit
        '/Volumes/Public/Fort Hills/02. Equipment Files/1. 980E Trucks/F301 - A40017'
        """

        # get unit's row from unit table, save to self attributes
        m = db.get_df_unit().loc[unit]
        f.copy_dict_attrs(m=m, target=self)

        modelpath = self.get_modelpath() # needs model and model_map
        unitpath = f'{unit} - {self.serial}'

        if not 'shovels' in self.minesite.lower():
            p_unit = f.drive / f'{self.equippath}/{modelpath}/{unitpath}'
        else:
            # shovels doesn't want modelpath. Could make this a list of exclusions or something
            p_unit = f.drive / f'{self.equippath}/{unitpath}'

        p_dls = p_unit / 'Downloads'
        
        f.set_self(vars())
    
    @property
    def equippath(self):
        """Return specific equippath from data/config.yaml if exists for self.minesite, else default
        >>> 'Fort McMurray/service/2. Customer Equipment Files/1. Suncor'
        """
        minesite = self.minesite.replace('-', '') # handle Shovels-63N
        s = f.config['EquipPaths'].get(minesite, None)
        if not s is None:
            return s
        else: 
            return 'Regional/SMS West Mining/Equipment'

    def get_modelpath(self):
        """Return section of path to bridge equippath and unitpath.

        Some units have specific path for model, others use default modelbase eg 'HM400'

        Examples
        ---
        (BaseMine)
        >>> '1. Trucks/2. 980E'
        """
        model = self.model

        modelbase = f.config.get('ModelPaths', {}).get(self.minesite, {}).get(self.modelbase, None)
        if not modelbase is None: return modelbase

        # NOTE very ugly and sketch but w/e
        lst_full_model = ['Bighorn', 'RainyRiver', 'GahchoKue', 'CoalValley', 'ConumaCoal', 'IOC-RioTinto']

        if not self.minesite in lst_full_model:
            modelbase = db.get_modelbase(model=model)
        else:
            # TODO eventually maybe migrate all these folders to a modelbase structure
            modelbase = model
            
        return modelbase if not modelbase is None else 'temp'

class EventFolder(UnitFolder):
    def __init__(self, unit, dateadded, workorder, title, uid=None, table_model=None, irow=None, table_widget=None, **kw):
        super().__init__(unit=unit, **kw)
        # table_model only needed to set pics in table view
        self.dt_format = '%Y-%m-%d'

        year = dateadded.year

        wo_blank = 'WO' + ' ' * 14
        if not workorder or 'nan' in workorder.lower():
            workorder = wo_blank

        # confirm unit, date, title exist?
        folder_title = self.get_folder_title(unit, dateadded, workorder, title)

        p_base = self.p_unit / f'Events/{year}'
        _p_event = p_base / folder_title
        p_event_blank = p_base / self.get_folder_title(unit, dateadded, wo_blank, title)

        f.set_self(vars())
    
    @classmethod
    def from_model(cls, e, **kw):
        """Create eventfolder from database/row model 'e'. Used when single query to db first is okay.
        \n NOTE works with row model OR df.itertuples"""
        efl = cls(unit=e.Unit, dateadded=e.DateAdded, workorder=e.WorkOrder, title=e.Title, **kw)

        if hasattr(e, 'Pictures'):
            efl.pictures = e.Pictures
            
        return efl
    
    @classmethod
    def example(cls, uid=108085410910):
        from . import dbtransaction as dbt
        from .gui import startup
        app = startup.get_qt_app()
        e = dbt.example(uid=uid)
        return cls.from_model(e=e)
    
    @property
    def p_event(self) -> Path:
        """NOTE careful when using this if don't want to check/correct path > use _p_event instead"""
        self.check()
        return self._p_event

    @property
    def p_pics(self) -> Path:
        return self._p_event / 'Pictures'
    
    def update_eventfolder_path(self, vals : dict):
        """Update folder path with defaults (actually new vals) + changed vals (previous)"""
        m_prev = dict(
            unit=self.unit,
            dateadded=self.dateadded,
            workorder=self.workorder,
            title=self.title)

        m_prev.update(vals)

        p_prev = self.p_base / self.get_folder_title(**m_prev)
        if not p_prev == self._p_event:
            self.check(p_prev=p_prev)

            if not self.table_widget is None:
                self.table_widget.mainwindow.update_statusbar(msg=f'Folder path updated: {self.folder_title}')

    def get_folder_title(self, unit, dateadded, workorder, title):
        title = f.nice_title(title=title)
        workorder = f.remove_bad_chars(w=workorder)
        return f'{unit} - {dateadded:%Y-%m-%d} - {workorder} - {title}'

    @property
    def exists(self):
        """Simple check if folder exists"""
        return self._p_event.exists()
    
    @property
    def num_files(self):
        """Return number of files in event folder and subdirs, good check before deleting"""
        return len(list(self._p_event.glob('**/*'))) if self.exists else 0
    
    def remove_folder(self):
        try:
            p = self._p_event
            shutil.rmtree(p)
            return True
        except:
            return False

    def check(self, p_prev : Path = None, check_pics=True):
        """Check if self.p_event exists.

        Parameters
        ----------
        p_prev : Path, optional
            Compare against manually given path, default None\n
        check_pics : bool, optional

        Returns
        -------
        bool
            True if folder exists or replace was successful.
        """        
        from .gui import dialogs as dlgs
        if not fl.drive_exists():
            return
            
        p = self._p_event
        p_blank = self.p_event_blank

        if not p.exists():
            if not p_prev is None and p_prev.exists():
                # rename folder when title changed
                fl.move_folder(p_src=p_prev, p_dst=p)
            elif p_blank.exists():
                # if wo_blank stills exists but event now has a WO, automatically rename
                fl.move_folder(p_src=p_blank, p_dst=p)
            else:
                # show folder picker dialog
                msg = f'Can\'t find folder:\n\'{p.name}\'\n\nWould you like to link it?'
                if dlgs.msgbox(msg=msg, yesno=True):
                    p_old = dlgs.get_filepath_from_dialog(p_start=p.parent)
                    
                    # if user selected a folder
                    if p_old:
                        fl.move_folder(p_src=p_old, p_dst=p)
                    
                if not p.exists():
                    # if user declined to create OR failed to choose a folder, ask to create
                    msg = f'Folder:\n\'{p.name}\' \n\ndoesn\'t exist, create now?'
                    if dlgs.msgbox(msg=msg, yesno=True):
                        self.create_folder()
        
        if p.exists():            
            if check_pics: self.set_pics()
            return True
        else:
            return False
        
    def show(self):
        if self.check():
            fl.open_folder(p=self._p_event, check_drive=False)
    
    def set_pics(self):
        # count number of pics in folder and set model + save to db
        model, irow = self.table_model, self.irow
        
        num_pics = fl.count_files(p=self.p_pics, ftype='pics')
        if hasattr(self, 'pictures') and num_pics == self.pictures: return # same as previous pictures

        # if WorkOrders table active, use setData to set table + db
        if not model is None and model.table_widget.title in ('Work Orders', 'TSI', 'FC Details'):
            if irow is None: return # need model/row to set value in table view

            index = model.createIndex(irow, model.get_col_idx('Pics'))
            model.setData(index=index, val=num_pics)
        else:
            # just set str8 to db with uid
            if self.uid is None: return

            row = Row(keys=dict(UID=self.uid), dbtable=EventLog)
            row.update(vals=dict(Pictures=num_pics))
            print(f'num pics updated in db: {num_pics}')

    def create_folder(self, show=True, ask_show=False):
        from .gui import dialogs as dlgs
        
        if not fl.drive_exists():
            return
            
        try:
            p = self._p_event
            p_pics = p / 'Pictures'
            p_dls = p / 'Downloads'

            if not p.exists():
                p_pics.mkdir(parents=True)
                p_dls.mkdir(parents=True)

                if ask_show:
                    msg = 'Event folder created. Would you like to open?'
                    if dlgs.msgbox(msg=msg, yesno=True):
                        self.show()
                elif show:
                    self.show()
        except:
            msg = 'Can\'t create folder!'
            dlgs.msg_simple(msg=msg, icon='critical')
            log.error(msg, exc_info=True)

    @property
    def has_condition_report(self):
        return len(self.condition_reports) > 0
    
    @property
    def condition_reports(self):
        if not hasattr(self, '_condition_reports') or self._condition_reports is None:
            self._condition_reports = fl.find_files_partial(p=self._p_event, partial_text='cond')

        return self._condition_reports
