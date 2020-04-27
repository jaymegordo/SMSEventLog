import pypika as pk

from .. import factorycampaign as fc
from . import gui as ui
from .__init__ import *
from .delegates import AlignDelegate, DateColumnDelegate, EditorDelegate
from . import dialogs as dlgs

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
    def __init__(self, parent=None, title=None):
        QWidget.__init__(self, parent)
        self.parent = parent
        self.title = title
        self.disabled_cols = []
        self.mainwindow = ui.get_mainwindow()
        self.minesite = self.mainwindow.minesite
        self.set_fltr()

        vLayout = QVBoxLayout(self)
        self.btnbox = QHBoxLayout()
        self.btnbox.setAlignment(Qt.AlignLeft)

        self.add_button(name='Refresh', func=self.show_refresh)
        self.add_button(name='Add New', func=self.show_addrow)

        view = TableView(self)

        vLayout.addLayout(self.btnbox)
        vLayout.addWidget(view)
        self.view = view
        self.col_widths = {'Title': 150, 'Part Number': 150}
        self.set_default_headers()

        # get default refresh dialog from refreshtables by name
        from . import refreshtables as rtbls
        self.refresh_dialog = getattr(rtbls, self.__class__.__name__, rtbls.RefreshTable)

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

    def set_fltr(self):
        self.fltr = el.Filter(title=self.title)

    def show_refresh(self):
        try:
            dlg = self.refresh_dialog(parent=self)
            # ui.disable_window_animations_mac(dlg)
            dlg.exec_()
        except:
            msg = 'couldn\'t show RefreshTable'
            f.send_error(msg=msg)
            log.error(msg)

    def refresh_lastweek(self):
        self.fltr.add(field='MineSite', val=self.minesite)
        self.fltr.add(field='DateAdded', val=dt.now().date() + delta(days=-7))
        self.refresh()

    def refresh_lastmonth(self):
        # self.sender() = PyQt5.QtWidgets.QAction > could use this to decide on filters
        self.fltr.add(field='MineSite', val=self.minesite)
        self.fltr.add(field='DateAdded', val=dt.now().date() + delta(days=-30))
        self.refresh()

    def refresh_allopen(self):
        # All open is specific to each table.. need to subclass this
        self.set_default_filter()
        self.refresh()

    def refresh(self, fltr=None, default=False):
        # Accept filter from RefreshTable dialog, load data to table view

        if default:
            if hasattr(self, 'set_default_filter'):
                self.set_default_filter()

        if fltr is None:
            fltr = self.fltr
        
        # fltr.add(field='MineSite', val=self.mainwindow.minesite) # TODO: can't have this here always
        fltr.print_criterion()
        df = el.get_df(title=self.title, fltr=fltr)
        
        if hasattr(self, 'process_df'):
            df = self.process_df(df=df)
        
        self.set_fltr() # reset filter after every refresh call
        self.display_data(df=df)

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
            
    def display_data(self, df):
        view = self.view
        title = self.title
        model = ui.Table(df=df, parent=self)
        view.setModel(model)
        view.setItemDelegate(EditorDelegate(parent=view))
        view.resizeColumnsToContents()

        cols = ['Passover', 'Unit', 'Status', 'Wrnty', 'Work Order', 'Seg', 'Customer WO', 'Customer PO', 'Serial', 'Side']
        self.center_columns(cols=cols)
        self.set_column_widths()
        
        if title in ('Event Log', 'Work Orders', 'TSI', 'Component CO'):
            view.hideColumn(model.getColIndex('UID'))

        self.set_date_delegates()
        view.resizeRowsToContents()
        self.model = model

    def active_row_index(self):
        rows = self.view.selectionModel().selectedRows() # list of selected rows
        return rows[0].row()
    
    def row_from_activerow(self):
        i = self.active_row_index()
        return el.Row(tbl=self.model, i=i)

    def model_from_activerow(self):
        i = self.active_row_index()
        return self.model.create_model(i=i)

class EventLog(TableWidget):
    def __init__(self, parent=None, title='Event Log'):
        super().__init__(parent=parent, title=title)
        self.disabled_cols = ('Title')
        self.col_widths.update(dict(Passover=50, Description=800, Status=100))
    
    def set_default_filter(self):
        self.fltr.add(field='MineSite', val=self.minesite)
        self.fltr.add(field='StatusEvent', val='complete', opr=operator.ne)
        
class WorkOrders(TableWidget):
    def __init__(self, parent=None, title='Work Orders'):
        super().__init__(parent=parent, title=title)
        
        self.col_widths.update({
            'Work Order': 80,
            'Customer WO': 80,
            'Customer PO': 80,
            'Comp CO': 50,
            'Comments': 400})

    def set_default_filter(self):
        self.fltr.add(field='MineSite', val=self.minesite)
        self.fltr.add(field='StatusWO', val='open')

class ComponentCO(TableWidget):
    def __init__(self, parent=None, title='Component CO'):
        super().__init__(parent=parent, title=title)
        self.col_widths.update(dict(Notes=400))

    def set_default_filter(self):
        self.fltr.add(vals=dict(MineSite=self.minesite))
        self.fltr.add(vals=dict(DateAdded=dt.now().date() + delta(days=-30)))

class TSI(TableWidget):
    def __init__(self, parent=None, title='TSI'):
        super().__init__(parent=parent, title=title)
        self.disabled_cols = ('WO')

        self.col_widths.update(dict(Details=400))

    def set_default_filter(self):
        self.fltr.add(field='MineSite', val=self.mainwindow.minesite)
        self.fltr.add(field='StatusTSI', val='closed', opr=operator.ne)

class UnitInfo(TableWidget):
    def __init__(self, parent=None, title='Unit Info'):
        super().__init__(parent=parent, title=title)
        self.disabled_cols = ('SMR Measure Date', 'Current SMR', 'Warranty Remaining', 'GE Warranty',)
        self.col_widths.update({
            'Warranty Remaining': 40,
            'GE Warranty': 40})
    
    def set_default_filter(self):
        self.fltr.add(vals=dict(MineSite=self.minesite))

class FCDetails(TableWidget):
    def __init__(self, parent=None, title='FC Details'):
        super().__init__(parent=parent, title=title)

    def set_default_filter(self):
        fltr = self.fltr
        fltr.add(vals=dict(MineSite=ui.get_minesite()), table=pk.Table('UnitID'))
        fltr.add(vals=dict(ManualClosed=0), table=pk.Table('FCSummaryMineSite'))
        fltr.add(vals=dict(Complete=0))

class FCSummary(TableWidget):
    def __init__(self, parent=None, title='FC Summary'):
        super().__init__(parent=parent, title=title)
        self.col_widths.update({
            'Subject': 250,
            'Comments': 800,
            'Action Reqd': 60,
            'Type': 40,
            'Part Number': 100,
            'Parts Avail': 40,
            'Total Complete': 60,
            '% Complete': 40})

        self.add_button(name='Import FCs', func=lambda: fc.importFC(upload=True))

    def set_default_filter(self):
        fltr = self.fltr
        fltr.add(vals=dict(MineSite=ui.get_minesite()), table=pk.Table('UnitID'))
        fltr.add(vals=dict(ManualClosed=0), table=pk.Table('FCSummaryMineSite'))
        # fltr.add(vals=dict(Classification='M'), table=pk.Table('FCSummary'))

    def process_df(self, df):
        try:
            # create summary (calc complete %s)
            df2 = pd.DataFrame()
            gb = df.groupby('FC Number')

            df2['Total'] = gb['Complete'].count()
            df2['Complete'] = gb.apply(lambda x: x[x['Complete']=='Y']['Complete'].count())
            df2['Total Complete'] = df2.Complete.astype(str) + ' / ' +  df2.Total.astype(str)
            df2['% Complete'] = df2.Complete / df2.Total
            df2.drop(columns=['Total', 'Complete'], inplace=True)

            # pivot - note: can't pivot properly if Hours column (int) is NULL.. just make sure its filled
            index = [c for c in df.columns if not c in ('Unit', 'Complete')] # use all df columns except unit, complete
            df = df.pipe(f.multiIndex_pivot, index=index, columns='Unit', values='Complete').reset_index()

            # merge summary
            df = df.merge(right=df2, how='left', on='FC Number')

            # reorder cols after merge
            cols = list(df)
            cols.insert(10, cols.pop(cols.index('Total Complete')))
            cols.insert(11, cols.pop(cols.index('% Complete')))
            df = df.loc[:, cols]

            df = f.sort_df_by_list(df=df, lst=['M', 'FAF', 'DO', 'FT'])

        except:
            f.send_error(msg='Can\'t pivot fc summary dataframe')

        return df

