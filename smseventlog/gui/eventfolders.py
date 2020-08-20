from .. import folders as fl
from .. import functions as f
from . import dialogs as dlgs
from .__init__ import *

log = logging.getLogger(__name__)

class EventFolder(object):
    def __init__(self, unit, dateadded, workorder, title, uid=None, table_model=None, irow=None, table_widget=None):
        # table_model only needed to set pics in table view
        self.dt_format = '%Y-%m-%d'

        # f.copy_model_attrs(model=e, target=self)

        # get unit's row from unit table, save to self attributes
        m = db.get_df_unit().loc[unit]
        f.copy_dict_attrs(m=m, target=self)

        modelpath = self.get_modelpath() # needs model and model_map
        year = dateadded.year

        wo_blank = 'WO' + ' ' * 14
        if not workorder:
            workorder = wo_blank

        # confirm unit, date, title exist?
        folder_title = self.get_folder_title(unit, dateadded, workorder, title)

        unitpath = f'{unit} - {self.serial}'

        p_base = f.drive / f'{self.equippath}/{modelpath}/{unitpath}/Events/{year}'
        _p_event = p_base / folder_title
        p_event_blank = p_base / self.get_folder_title(unit, dateadded, wo_blank, title)

        f.set_self(vars())
    
    @classmethod
    def from_model(cls, e, **kw):
        # create eventfolder from database/row model 'e', used when single query to db first is okay
        # NOTE works with row model OR df.itertuples
        efl = cls(unit=e.Unit, dateadded=e.DateAdded, workorder=e.WorkOrder, title=e.Title, **kw)

        if hasattr(e, 'Pictures'):
            efl.pictures = e.Pictures
            
        return efl

    @property
    def equippath(self):
        return f'Regional/SMS West Mining/Equipment'
    
    @property
    def p_event(self):
        # NOTE careful when using this if don't want to check/correct path > use _p_event instead
        self.check()
        return self._p_event

    def update_eventfolder_path(self, vals):
        # update folder path with defaults (actually new vals) + changed vals (previous)
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
        d_str = dateadded.strftime(self.dt_format)
        return f'{unit} - {d_str} - {workorder} - {title}'

    def check(self, p_prev=None, check_pics=True):
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
        
        p_pics = self._p_event / 'Pictures'
        num_pics = fl.count_files(p=p_pics, ftype='pics')
        if hasattr(self, 'pictures') and num_pics == self.pictures: return # same as previous pictures

        # if WorkOrders table active, use setData to set table + db
        if not model is None and model.table_widget.title == 'Work Orders':
            if irow is None: return # need model/row to set value in table view

            index = model.createIndex(irow, model.get_col_idx('Pics'))
            model.setData(index=index, val=num_pics)
        else:
            # just set str8 to db with uid
            if self.uid is None: return

            row = dbt.Row(keys=dict(UID=self.uid), dbtable=dbm.EventLog)
            row.update(vals=dict(Pictures=num_pics))
            print(f'num pics updated in db: {num_pics}')

    def create_folder(self, show=True, ask_show=False):
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
            log.error(msg)

    def get_modelpath(self):
        model = self.model
        
        if hasattr(self, 'model_map'):
            m = self.model_map
            # loop model_map and convert to model folder path if found
            for k, v in m.items():
                if k.lower() in model.lower():
                    return v

        modelbase = db.get_modelbase(model=model)
        return modelbase if not modelbase is None else 'temp'

    @property
    def has_condition_report(self):
        return len(self.condition_reports) > 0
    
    @property
    def condition_reports(self):
        if not hasattr(self, '_condition_reports') or self._condition_reports is None:
            self._condition_reports = fl.find_files_partial(p=self._p_event, partial_text='cond')

        return self._condition_reports 

class FortHills(EventFolder):
    model_map = {
        '980':'1. 980E Trucks',
        '930': '2. 930E Trucks',
        'HD1500': '3. HD1500'}

    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def equippath(self):
        return f'Fort Hills/02. Equipment Files'

class BaseMine(EventFolder):
    # NOTE may need to add other models in here eg shovels?
    trucks = '1. Trucks'
    model_map = {
        '980': f'{trucks}/2. 980E',
        '930': f'{trucks}/1. 930E',
        'HD1500': f'{trucks}/3. HD1500'}
    
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def equippath(self):
        return f'Fort McMurray/service/2. Customer Equipment Files/1. Suncor'

class Elkford(EventFolder):   
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def equippath(self):
        return 'Elkford/Equipment'

def get_eventfolder(minesite=None):
    # Try to get minesite specific event folder, else use default
    return getattr(sys.modules[__name__], minesite, EventFolder)

def example():
    from . import startup
    from .. import dbtransaction as dbt
    app = startup.get_qt_app()
    e = dbt.example()
    efl = get_eventfolder(minesite=e.MineSite)(e=e)

    return efl