import pypika as pk

from .. import factorycampaign as fc
from . import gui as ui
from .__init__ import *
from .delegates import AlignDelegate, DateColumnDelegate, EditorDelegate
from . import dialogs as dlgs
from .. import emails as em
from .. import queries as qr
from .. import reports as rp

log = logging.getLogger(__name__)

class TableView(QTableView):    
    def __init__(self, *args, **kwargs):
        QTableView.__init__(self, *args, **kwargs)

        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setWordWrap(True)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignCenter | Qt.Alignment(Qt.TextWordWrap))
        self.setSortingEnabled(True)
        self.horizontalHeader().sortIndicatorChanged.connect(self.resizeRowsToContents)
        self.setStyleSheet(' \
            QTableView::item:selected:active {color: #000000;background-color: #ffff64;} \
            QTableView::item:selected:hover {color: #000000;background-color: #cccc4e;} \
            QTableView::item {border: 0px; padding: 2px;}')

    def keyPressEvent(self, event):
        # F2 to edit cell
        if event.key() == 16777265 and (self.state() != QAbstractItemView.EditingState):
            self.edit(self.currentIndex())

        super().keyPressEvent(event)

class TableWidget(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        title = f.config['TableName']['Class'][self.__class__.__name__]
        disabled_cols, hide_cols, check_exist_cols, db_col_map = (), (), (), {}
        col_widths = {'Title': 150, 'Part Number': 150}

        mainwindow = ui.get_mainwindow()
        minesite = mainwindow.minesite

        vLayout = QVBoxLayout(self)
        btnbox = QHBoxLayout()
        btnbox.setAlignment(Qt.AlignLeft)

        view = TableView(self)

        vLayout.addLayout(btnbox)
        vLayout.addWidget(view)

        # get default refresh dialog from refreshtables by name
        from . import refreshtables as rtbls
        name = self.__class__.__name__
        refresh_dialog = getattr(rtbls, name, rtbls.RefreshTable)
        query = getattr(qr, name, qr.QueryBase)()

        f.set_self(self, vars())
        self.add_button(name='Refresh', func=self.show_refresh)
        self.add_button(name='Add New', func=self.show_addrow)
        self.set_default_headers()

    def set_default_headers(self):
        cols = f.get_default_headers(title=self.title)
        df = pd.DataFrame(columns=cols)
        self.display_data(df=df)

    def add_button(self, name, func):
        btn = QPushButton(name, self)
        btn.setMaximumWidth(60)
        btn.clicked.connect(func)
        self.btnbox.addWidget(btn)
   
    def show_addrow(self):
        try:
            dlg = dlgs.AddEvent(parent=self)
            # ui.disable_window_animations_mac(dlg)
            dlg.exec_()
        except:
            msg = 'couldn\'t show AddRow'
            f.send_error(msg=msg)
            log.error(msg)

    def show_refresh(self):
        try:
            dlg = self.refresh_dialog(parent=self)
            # ui.disable_window_animations_mac(dlg)
            dlg.exec_()
        except:
            msg = 'couldn\'t show RefreshTable'
            f.send_error(msg=msg)
            log.error(msg)

    def refresh_lastweek(self, default=False):
        fltr = self.query.fltr
        if default:
            self.query.set_minesite()
        fltr.add(field='DateAdded', val=dt.now().date() + delta(days=-7))
        self.refresh()

    def refresh_lastmonth(self, default=False):
        # self.sender() = PyQt5.QtWidgets.QAction > could use this to decide on filters
        fltr = self.query.fltr
        if default:
            self.query.set_minesite()
        fltr.add(field='DateAdded', val=dt.now().date() + delta(days=-30))
        self.refresh()

    def refresh_allopen(self, default=False):
        query = self.query
        if hasattr(query, 'set_allopen'):
            query.set_allopen()

        self.refresh(default=default)

    def refresh(self, default=False):
        # RefreshTable dialog will have modified query's fltr, load data to table view

        df = db.get_df(query=self.query, default=default)

        if not len(df) == 0:
            self.display_data(df=df)
        else:
            dlgs.msg_simple(msg='No rows returned in query!', icon='warning')

    def set_date_delegates(self):
        view = self.view
        date_delegate = DateColumnDelegate(view)

        for i in view.model().dt_cols:
            view.setItemDelegateForColumn(i, date_delegate)
            view.setColumnWidth(i, 90) # TODO: this should be in the delegate!

    def center_columns(self, cols):
        view = self.view
        model = view.model()
        align_delegate = AlignDelegate(view)

        for c in cols:
            if c in model.df.columns:
                view.setItemDelegateForColumn(model.getColIndex(c), align_delegate)

    def set_column_width(self, cols, width):
        view = self.view
        model = view.model()
        if not isinstance(cols, list): cols = [cols]

        for c in cols:
            if c in model.df.columns:
                view.setColumnWidth(model.getColIndex(c), width)
    
    def set_column_widths(self):
        view = self.view
        model = view.model()

        for c, width in self.col_widths.items():
            if c in model.df.columns:
                view.setColumnWidth(model.getColIndex(c), width)

    def hide_columns(self):
        for col in self.hide_cols:
            self.view.hideColumn(self.model.getColIndex(col))

    def display_data(self, df):
        view = self.view
        title = self.title
        model = ui.Table(df=df, parent=self)
        self.model = model
        view.setModel(model)
        view.setItemDelegate(EditorDelegate(parent=view))
        view.resizeColumnsToContents()

        cols = ['Passover', 'Unit', 'Status', 'Wrnty', 'Work Order', 'Seg', 'Customer WO', 'Customer PO', 'Serial', 'Side']
        self.center_columns(cols=cols)
        self.set_column_widths()
        
        self.hide_columns()
        self.set_date_delegates()
        view.resizeRowsToContents()
        view.horizontalHeader().setFixedHeight(30)

    def active_row_index(self):
        rows = self.view.selectionModel().selectedRows() # list of selected rows
        if rows:
            return rows[0].row()
        else:
            msg = 'No row selected in table.'
            dlgs.msg_simple(msg=msg, icon='warning')
    
    def row_from_activerow(self):
        i = self.active_row_index()
        if i is None: return
        return el.Row(tbl=self.model, i=i)

    def model_from_activerow(self):
        i = self.active_row_index()
        if i is None: return
        return self.model.create_model(i=i)
    
    def df_from_activerow(self):
        i = self.active_row_index()
        if i is None: return
        return self.model.df.iloc[[i]]

class EventLog(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.disabled_cols = ('Title',) # TODO: remove thise
        self.hide_cols = ('UID',)
        self.col_widths.update(dict(Passover=50, Description=800, Status=100))
        
class WorkOrders(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.hide_cols = ('UID',)       
        self.col_widths.update({
            'Work Order': 90,
            'Customer WO': 80,
            'Customer PO': 80,
            'Comp CO': 50,
            'Comments': 400})

class ComponentCO(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.disabled_cols = ('MineSite', 'Model', 'Unit', 'Component', 'Side')
        self.hide_cols = ('UID',)
        self.col_widths.update(dict(Notes=400))

class TSI(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.disabled_cols = ('WO',)
        self.hide_cols = ('UID',)
        self.col_widths.update(dict(Details=400))

class UnitInfo(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.disabled_cols = ('SMR Measure Date', 'Current SMR', 'Warranty Remaining', 'GE Warranty')
        self.col_widths.update({
            'Warranty Remaining': 40,
            'GE Warranty': 40})

class FCBase(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.add_button(name='Import FCs', func=lambda: fc.importFC(upload=True))
        self.add_button(name='View FC Folder', func=self.view_fc_folder)
   
    def get_fc_folder(self):
        if not fl.drive_exists():
            return

        row = self.model_from_activerow()
        if row is None: return

        p = f.drive / f.config['FilePaths']['Factory Campaigns'] / row.FCNumber

        if not p.exists():
            msg = f'FC folder: \n\n{p} \n\ndoes not exist, create now?'
            if dlgs.msgbox(msg=msg, yesno=True):
                p.mkdir(parents=True)
            else:
                return
        
        return p
    
    def view_fc_folder(self):
        fl.open_folder(p=self.get_fc_folder())

class FCSummary(FCBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.hide_cols = ('MineSite',)
        self.disabled_cols = ('FC Number', 'Total Complete', '% Complete') # also add all unit cols?
        self.col_widths.update({
            'Subject': 250,
            'Comments': 600,
            'Action Reqd': 60,
            'Type': 40,
            'Part Number': 100,
            'Parts Avail': 40,
            'Total Complete': 60,
            '% Complete': 40})

        # TODO: add dropdown menu for Type, Action Reqd, Parts Avail

        # map table col to update table in db if not default
        tbl_b = 'FCSummaryMineSite'
        self.db_col_map = {
            'Action Reqd': tbl_b,
            'Parts Avail': tbl_b,
            'Comments': tbl_b}
        
        self.check_exist_cols = tuple(self.db_col_map.keys()) # rows for these cols may not exist yet in db

        self.add_button(name='Email New FC', func=self.email_new_fc)

    def email_new_fc(self):
        # get df of current row
        df = self.df_from_activerow().iloc[:, :10]
        df.replace('\n', '<br>', inplace=True, regex=True)
        style = rp.set_style(df=df)
        formats = {'int64': '{:,}', 'datetime64[ns]': '{:%Y-%m-%d}'}
        m = rp.format_dtype(df=df, formats=formats)
        style.format(m)

        fcnumber = df['FC Number'].iloc[0]
        subject = df.Subject.iloc[0]
        title = f'New FC - {fcnumber} - {subject}'

        body = f'Hello,<br><br>New FC Released:<br><br>{style.hide_index().render()}'

        # get email list from db
        df2 = db.get_df(query=qr.EmailList())
        lst = list(df2[(df2.MineSite==self.minesite) & (df2['FC Summary'].notnull())].Email)

        # show new email
        msg = em.Message(subject=title, body=body, to_recip=lst)

        # attach files in fc folder
        p = self.get_fc_folder()
        if not p is None:
            for attach in p.glob('*.pdf'):
                msg.add_attachment(p=attach)

class FCDetails(FCBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.disabled_cols = ('MineSite', 'Model', 'Unit', 'FC Number', 'Complete', 'Closed', 'Type', 'Subject')
        self.col_widths.update({
            'Complete': 60,
            'Closed': 60,
            'Type': 60,
            'Subject': 400,
            'Notes': 400})

class EmailList(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # self.disabled_cols = ('SMR Measure Date', 'Current SMR', 'Warranty Remaining', 'GE Warranty')
        # self.col_widths.update({
        #     'Warranty Remaining': 40,
        #     'GE Warranty': 40})