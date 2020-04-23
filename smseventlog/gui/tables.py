import pypika as pk

from .. import factorycampaign as fc
from . import dialogs as dlgs
from . import gui as ui
from .__init__ import *
from .delegates import AlignDelegate, DateColumnDelegate, EditorDelegate

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
        self.set_fltr()

        vLayout = QVBoxLayout(self)
        self.btnbox = QHBoxLayout()
        self.btnbox.setAlignment(Qt.AlignLeft)

        # TODO: Different tabs will need different buttons
        self.add_button(name='Refresh', func=self.show_refresh)
        self.add_button(name='Add New', func=self.show_addrow)

        view = TableView(self)

        vLayout.addLayout(self.btnbox)
        vLayout.addWidget(view)
        self.view = view
        self.col_widths = {'Title': 150, 'Part Number': 150}
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
            ui.disable_window_animations_mac(dlg)
            dlg.exec_()
        except:
            msg = 'couldn\'t show AddRow'
            f.senderror(msg=msg)
            log.error(msg)

    def set_fltr(self):
        self.fltr = el.Filter(title=self.title)

    def show_refresh(self):
        try:
            dlg = dlgs.RefreshTable(parent=self)
            ui.disable_window_animations_mac(dlg)
            dlg.exec_()
        except:
            msg = 'couldn\'t show RefreshTable'
            f.senderror(msg=msg)
            log.error(msg)

    def refresh_lastweek(self):
        self.fltr.add(field='DateAdded', val=dt.now().date() + delta(days=-7))
        self.refresh()

    def refresh_lastmonth(self):
        self.fltr.add(field='DateAdded', val=dt.now().date() + delta(days=-30))
        self.refresh()

    def refresh_allopen(self):
        # All open is specific to each table.. need to subclass this
        self.refresh()

    def refresh(self, fltr=None, default=False):
        # Accept filter from RefreshTable dialog, load data to table view

        if default:
            try:
                self.set_default_filter()
            except:
                pass

        if fltr is None:
            fltr = self.fltr
        
        fltr.add(field='MineSite', val=self.mainwindow.minesite) # TODO: can't have this here always
        fltr.print_criterion()
        df = el.get_df(title=self.title, fltr=fltr)
        df = process_df(df=df)
        
        self.set_fltr() # reset filter after every refresh call
        self.display_data(df=df)

    def process_df(self, df):
        return df # subclass for each table if need to post process after query

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
    def __init__(self, parent=None, title=None):
        super().__init__(parent=parent, title=title)
        self.disabled_cols = ('Title')
        self.col_widths.update(dict(Passover=50, Description=800))
    
    def set_default_filter(self):
        self.fltr.add(field='StatusEvent', val='complete', opr=operator.ne)
    
    def refresh_allopen(self):
        self.set_default_filter()
        super().refresh_allopen()
        
class WorkOrders(TableWidget):
    def __init__(self, parent=None, title=None):
        super().__init__(parent=parent, title=title)
        
        self.col_widths.update({
            'Work Order': 80,
            'Customer WO': 80,
            'Customer PO': 80,
            'Comp CO': 50,
            'Comments': 400})

    def set_default_filter(self):
        self.fltr.add(field='StatusWO', val='open')

    def refresh_allopen(self):
        self.set_default_filter()
        super().refresh_allopen()

class ComponentCO(TableWidget):
    def __init__(self, parent=None, title=None):
        super().__init__(parent=parent, title=title)

class TSI(TableWidget):
    def __init__(self, parent=None, title=None):
        super().__init__(parent=parent, title=title)
        self.disabled_cols = ('WO')

        self.col_widths.update(dict(Details=400))

    def set_default_filter(self):
        self.fltr.add(field='StatusTSI', val='closed', opr=operator.ne)

    def refresh_allopen(self):
        self.set_default_filter()
        super().refresh_allopen()

class UnitInfo(TableWidget):
    def __init__(self, parent=None, title=None):
        super().__init__(parent=parent, title=title)
        self.disabled_cols = ('SMR Measure Date', 'Current SMR', 'Warranty Remaining', 'GE Warranty',)
        self.col_widths.update({
            'Warranty Remaining': 40,
            'GE Warranty': 40})

class FCDetails(TableWidget):
    def __init__(self, parent=None, title=None):
        super().__init__(parent=parent, title=title)

class FCSummary(TableWidget):
    def __init__(self, parent=None, title=None):
        super().__init__(parent=parent, title=title)
        
        self.add_button(name='Import FCs', func=lambda: fc.importFC(upload=True))

    def set_default_filter(self):
        # TODO: add these to refresh form
        fltr = self.fltr
        fltr.add(field='Classification', val='M', table=pk.Table('FCSummary'))
        fltr.add(field='MineSite', val='FortHills', table=pk.Table('UnitID'))
        fltr.add(field='ManualClosed', val=0, table=pk.Table('FCSummaryMineSite'))
    
    def process_df(self, df):
        # create summary (calc complete %s)
        df2 = pd.DataFrame()
        gb = df.groupby('FC Number')

        df2['Total'] = gb['Complete'].count()
        df2['Complete'] = gb.apply(lambda x: x[x['Complete']=='Y']['Complete'].count())
        df2['Total Complete'] = df2.Complete.astype(str) + ' / ' +  df2.Total.astype(str)
        df2['% Complete'] = df2.Complete / df2.Total
        df2.drop(columns=['Total', 'Complete'], inplace=True)

        # pivot
        index = [c for c in df.columns if not c in ('Unit', 'Complete')] # use all df columns except unit, complete
        df = df.pipe(f.multiIndex_pivot, index=index, columns='Unit', values='Complete').reset_index()

        # merge summary
        df = df.merge(right=df2, how='left', on='FC Number')

        # reorder cols after merge
        cols = list(df)
        cols.insert(10, cols.pop(cols.index('Total Complete')))
        cols.insert(11, cols.pop(cols.index('% Complete')))
        df = df.loc[:, cols]

        return df
