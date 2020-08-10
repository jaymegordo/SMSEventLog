from .. import folders as fl
from .. import functions as f
from . import dialogs as dlgs
from .__init__ import *

log = logging.getLogger(__name__)

class EventFolder(object):
    def __init__(self, e, model=None, irow=None):
        self.dt_format = '%Y-%m-%d'

        f.copy_model_attrs(model=e, target=self)

        # get unit's row from unit table, save to self attributes
        m = db.get_df_unit().loc[self.unit]
        f.copy_dict_attrs(m=m, target=self)

        modelpath = self.get_modelpath() # needs model and model_map
        year = self.dateadded.year

        wo_blank = 'WO' + ' ' * 14
        if not self.workorder:
            self.workorder = wo_blank

        # confirm unit, date, title exist?
        folder_title = self.get_folder_title(self.unit, self.dateadded, self.workorder, self.title)

        unitpath = f'{self.unit} - {self.serial}'

        p_base = f.drive / f'{self.equippath}/{modelpath}/{unitpath}/Events/{year}'
        _p_event = p_base / folder_title
        p_event_blank = p_base / self.get_folder_title(self.unit, self.dateadded, wo_blank, self.title)

        f.set_self(vars())

    @property
    def equippath(self):
        return f'Regional/SMS West Mining/Equipment'
    
    @property
    def p_event(self):
        self.check()
        return self._p_event

    def get_modelbase(self):
        # get modelbase from db for units in Regional
        # TODO this probably needs to move somewhere else eventually
        t = T('EquipType')
        q = t.select(t.ModelBase).where(t.Model==self.model)
        return db.query_single_val(q)

    def get_folder_title(self, unit, d, wo, title):
        d_str = d.strftime(self.dt_format)
        return f'{unit} - {d_str} - {wo} - {title}'

    def check(self):
        if not fl.drive_exists():
            return
            
        p = self._p_event
        p_blank = self.p_event_blank

        if not p.exists():
            if p_blank.exists():
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
            self.set_pics()
            return True
        else:
            return False
        
    def show(self):
        if self.check():
            fl.open_folder(p=self._p_event, check_drive=False)
    
    def set_pics(self):
        # count number of pics in folder and set model + save to db
        model, irow = self.model, self.irow
        if model is None or irow is None: return # need model to set value
        # TODO need to check and set pics from any table, have to bypass using model
        if model.table_widget.title != 'Work Orders': return

        p_pics = self._p_event / 'Pictures'
        num_pics = fl.count_files(p=p_pics, ftype='pics')

        index = model.createIndex(irow, model.get_col_idx('Pics'))
        model.setData(index=index, val=num_pics)
    
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
        model = self.model.lower()
        
        if hasattr(self, 'model_map'):
            m = self.model_map
            # loop model_map and convert to model folder path if found
            for k, v in m.items():
                if k.lower() in model:
                    return v

        modelbase = self.get_modelbase()
        if not modelbase is None:
            return modelbase
        else:
            return 'temp'
        
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
    model_map = {
        '980': '2. 980E',
        '930': '1. 930E',
        'HD1500': '3. HD1500'}
    
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
