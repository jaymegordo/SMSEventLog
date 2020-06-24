import pypika as pk

from .. import factorycampaign as fc
from . import gui as ui
from .datamodel import TableModel
from .__init__ import *
from .delegates import AlignDelegate, DateDelegate, DateTimeDelegate, CellDelegate, ComboDelegate
from . import dialogs as dlgs
from .. import emails as em
from .. import queries as qr
from .. import styles as st
from .. import functions as f

log = logging.getLogger(__name__)

# TODO change how multiple selection works, don't select all rows
# TODO row selection - highlight behind existing cell colors
# TODO trigger on title changed?
# TODO trigger on componentCO changed
# TODO function bulk update multiple values in row (availability)
# TODO Component CO highlight null SNs + other vals
# TODO highlight header red when filter active
# TODO add pics count to TSI page
# TODO add tsi status to WO page
# TODO UnitINFO add new function/menu
# TODO create function to evaluate '=' formulas


class TableView(QTableView):
    dataFrameChanged = pyqtSignal()
    cellClicked = pyqtSignal(int, int)

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.activated.connect(self.double_click_enter)

        disabled_cols, hide_cols, check_exist_cols, datetime_cols = (), (), (), ()
        col_widths = {'Title': 150, 'Part Number': 150}
        highlight_funcs, highlight_vals, col_func_triggers, formats = dd(type(None)), {}, {}, {} # NOTE use all lowercase!
        colors = f.config['color']
        # col_maxmin # used for highlighting color scales
        
        # set up initial empty model
        self.parent = parent # model needs this to access parent table_widget
        _data_model = TableModel(parent=self)
        self.setModel(_data_model)
        rows_initialized = True

        # Signals/Slots
        _data_model.modelReset.connect(self.dataFrameChanged)
        _data_model.dataChanged.connect(self.dataFrameChanged)
        self.clicked.connect(self._on_click) # NOTE not sure if need this..
        self.dataFrameChanged.connect(self._enable_widgeted_cells) # NOTE or this

        self.setItemDelegate(CellDelegate(parent=self))

        # create header menu bindings
        header = self.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignCenter | Qt.Alignment(Qt.TextWordWrap))
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._header_menu)
        header.setFixedHeight(30)

        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setWordWrap(True)
        self.setSortingEnabled(True)

        yellowrow = colors['bg'].get('yellowrow', 'green')
        yellowrow = '#ffff64'
        darkyellow = '#cccc4e'
        lightblue = '#148CD2' ##19232D # border: 1px solid red; 
        self.setStyleSheet(' \
            QTableView::item:selected {color: #000000; background-color: #ffff64;} \
            QTableView::item:selected:active {color: black; background-color: #ffff64;} \
            QTableView:item:selected:focus {color: black; background-color: #ffff64; border: 1px solid red; } \
            QTableView::item:selected:hover {color: black; background-color: #cccc4e;}') \
        
        f.set_self(self, vars())
        self.set_default_headers()
        self.setVisible(True)

    def display_data(self, df):
        self.rows_initialized = False 
        self.model().set_df(df=df)
            
        self.hide_columns()
        self.resizeColumnsToContents()
        self.set_date_delegates()

        cols = ['Passover', 'Unit', 'Work Order', 'Seg', 'Customer WO', 'Customer PO', 'Serial', 'Side']
        # TODO should set textalignrole for these columns instead
        # self.center_columns(cols=cols)
        self.set_column_widths()

        self.rows_initialized = True
        self.resizeRowsToContents()

    def double_click_enter(self, QModelIndex):
        print('double_click_enter')
        QModelIndex.model().change_color(Qt.red, True)
 
        self.alarm = QTimer()
        self.alarm.setSingleShot(True)
        self.alarm.timeout.connect(self.color_timeout)
        self.alarm.start(200)
 
    def color_timeout(self):
        self.model().change_color(Qt.magenta, False)
    
    def add_highlight_funcs(self, cols, func):
        # add same highlight func to multiple cols
        if not isinstance(cols, list): cols = [cols]
        for col in cols:
            self.highlight_funcs[col] = func

    def add_col_funcs(self, cols, func):
        # add same col trigger func to multiple cols
        if not isinstance(cols, list): cols = [cols]
        for col in cols:
            self.col_func_triggers[col] = func

    def highlight_alternating(self, df, row, col, role, **kw):
        # use count of unique values mod 2 to highlight alternating groups of values
        # TODO only works if column is sorted by unit
        irow, icol = df.index.get_loc(row), df.columns.get_loc(col)
        alt_row_num = len(df.iloc[:irow + 1, icol].unique()) % 2

        if alt_row_num == 0 and role == Qt.BackgroundRole:
            return QColor(self.colors['bg']['maroon'])
    
    def highlight_by_val(self, val, role, **kw):
        # map cell value > color name > color code
        color_name = self.highlight_vals.get(str(val).lower(), None)
        if not color_name is None:
            color_code = self.colors['bg'].get(color_name, None)

            if not color_code is None:
                if role == Qt.BackgroundRole:
                    return QColor(color_code)
                elif role == Qt.ForegroundRole:
                    if 'light' in color_name: # TODO maybe move into own func
                        return QColor(Qt.black)
                    else:
                        color_code = self.colors['text'].get(color_name, None)
                        return QColor(color_code)

    def highlight_pics(self, val, role, **kw):
        if val > 0:
            color = 'goodgreen'
        else:
            color = 'bad'

        if role == Qt.BackgroundRole:
            color_code = self.colors['bg'][color]
        elif role == Qt.ForegroundRole:
            color_code = self.colors['text'][color]
        
        return QColor(color_code)

    def highlight_color_scale(self, val, **kw):
        # highlight values using max/min within range of multiple columns
        # get color scale
        if self.col_maxmin is None:
            df = self.model().df
            df = df[self.maxmin_cols]
            self.col_maxmin = tuple(df.max().max(), df.min().min())

        return

    def get_style(self, df=None, outlook=False):
        model = self.model()
        if df is None:
            df = model.df
        
        style = st.set_style(df=df, outlook=outlook) \
            .apply(model.get_background_colors_from_df, axis=None) \
            .format(self.formats)

        s = []
        s.append(dict(
            selector='table',
            props=[('border', '1px solid black')]))
        # s.append(dict(
        #     selector='tr:nth-child(even)',
        #     props=[('background-color', f.config['color']['bg']['greyrow'])])) 
        style.table_styles.extend(s)
        return style

    def resizeRowsToContents(self):
        # sender = self.sender()
        # model cant sort initially before the column widths are set
        if self.rows_initialized:
            # if self.model().df.shape[0] > 0:
            # print(f'\tResizing Rows: {sender}')
            super().resizeRowsToContents()

    def keyPressEvent(self, event):
        # F2 to edit cell
        if event.key() == 16777265 and (self.state() != QAbstractItemView.EditingState):
            self.edit(self.currentIndex())
        elif event.matches(QKeySequence.Copy):
            self.copy()
        else:
            super().keyPressEvent(event)

    def set_default_headers(self):
        cols = f.get_default_headers(title=self.parent.title)
        df = pd.DataFrame(columns=cols)
        self.display_data(df=df)

    def set_date_delegates(self):
        model = self.model()
        date_delegate = DateDelegate(self)

        for i in model.dt_cols:
            col = model.headerData(i)
            self.formats[col] = '{:%Y-%m-%d}'
            self.setColumnWidth(i, date_delegate.width)
            self.setItemDelegateForColumn(i, date_delegate)

        # if the parent table_widget has specified datetime cols
        if self.datetime_cols:
            datetime_delegate = DateTimeDelegate(self)
            for i in model.datetime_cols:
                self.setColumnWidth(i, datetime_delegate.width)
                col = model.headerData(i)
                self.formats[col] = '{:%Y-%m-%d     %H:%M}'
                self.setItemDelegateForColumn(i, datetime_delegate)

    def set_combo_delegate(self, col, items):
        model = self.model()
        combo_delegate = ComboDelegate(parent=self, items=items)
        c = model.get_column_idx(col=col)
        self.setItemDelegateForColumn(c, combo_delegate)

    def center_columns(self, cols):
        model = self.model()
        align_delegate = AlignDelegate(self)

        for c in cols:
            if c in model.df.columns:
                self.setItemDelegateForColumn(model.getColIndex(c), align_delegate)

    def set_column_width(self, cols, width):
        model = self.model()
        if not isinstance(cols, list): cols = [cols]

        for c in cols:
            if c in model.df.columns:
                self.setColumnWidth(model.getColIndex(c), width)
    
    def set_column_widths(self):
        model = self.model()

        for c, width in self.col_widths.items():
            if c in model.df.columns:
                self.setColumnWidth(model.getColIndex(c), width)

    def hide_columns(self):
        for col in self.hide_cols:
            self.hideColumn(self.model().getColIndex(col))

    def _header_menu(self, pos):
        """Create popup menu used for header"""
        # TODO values > df.col.value_counts()
        model = self.model()
        menu = FilterMenu(self)
        icol = self.header.logicalIndexAt(pos)

        if icol == -1: return # out of bounds

        # Filter Menu Action
        menu.addAction(DynamicFilterMenuAction(self, menu, icol))
        menu.addAction(FilterListMenuWidget(self, menu, icol))
        menu.addAction(self._icon('DialogResetButton'),
                        'Clear Filter',
                        model.reset)

        # Sort Ascending/Decending Menu Action
        menu.addAction(self._icon('TitleBarShadeButton'),
                        'Sort Ascending',
                    partial(model.sort, icol=icol, order=Qt.AscendingOrder))
        menu.addAction(self._icon('TitleBarUnshadeButton'),
                        'Sort Descending',
                    partial(model.sort, icol=icol, order=Qt.DescendingOrder))
        menu.addSeparator()

        # Hide
        menu.addAction(f'Hide Column: {model.headerData(icol, Qt.Horizontal)}', partial(self.hideColumn, icol))

        # Show column to left and right
        for i in (-1, 1):
            col = icol + i
            if self.isColumnHidden(col):
                menu.addAction(f'Unhide Column: {model.headerData(col, Qt.Horizontal)}',
                                partial(self.showColumn, col))


        menu.exec_(self.mapToGlobal(pos))

    def create_index_activerow(self, col_name=None, irow=None):
        # create QModelIndex from currently selected row
        model = self.model()
        if irow is None:
            irow = self.active_row_index()
        if col_name is None:
            icol = self.selectionModel().selectedColumns()
        return model.createIndex(irow, model.get_column_idx(col_name))

    def active_row_index(self):
        rows = self.selectionModel().selectedRows() # list of selected rows
        if rows:
            return rows[0].row()
        else:
            msg = 'No row selected in table.'
            dlgs.msg_simple(msg=msg, icon='warning')
    
    def row_from_activerow(self):
        i = self.active_row_index()
        if i is None: return
        return el.Row(table_model=self.model(), i=i)

    def model_from_activerow(self):
        i = self.active_row_index()
        if i is None: return
        return self.model().create_model(i=i)
    
    def df_from_activerow(self):
        i = self.active_row_index()
        if i is None: return
        return self.model().df.iloc[[i]]
    
    def nameindex_from_activerow(self):
        index = self.selectionModel().currentIndex()
        
        if index.isValid():
            return self.model().data(index=index, role=TableModel.NameIndexRole)

    def select_by_nameindex(self, name_index):
        # used to reselect items by named index after model is sorted/filtered
        model = self.model()
        # convert name_index to i_index
        i_index = model.data(name_index=name_index, role=TableModel.iIndexRole)
        if i_index is None:
            i_index = (0, 0)

        index = model.createIndex(*i_index)
        sel = QItemSelection(index, index)
        self.selectionModel().select(sel, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
        self.selectionModel().setCurrentIndex(index, QItemSelectionModel.Current) # make new index 'active'

    def copy(self):
        """Copy selected cells into copy-buffer"""
        selection = self.selectionModel()
        indexes = selection.selectedIndexes()

        if len(indexes) < 1: return # Nothing selected

        # Capture selection into a DataFrame
        df = pd.DataFrame() # NOTE may need to set size?
        for idx in indexes:
            row, col, item = idx.row(), idx.column(), idx.data()

            if item:
                df.iloc[row, col] = str(item)

        # Make into tab-delimited text (best for Excel)
        items = list(df.itertuples(index=False))
        s = '\n'.join(['\t'.join([cell for cell in row]) for row in df])

        # Send to clipboard
        QApplication.clipboard().setText(s)

    def _icon(self, icon_name):
        # Convinence function to get standard icons from Qt
        if not icon_name.startswith('SP_'):
            icon_name = f'SP_{icon_name}'

        icon = getattr(QStyle, icon_name, None)

        if icon is None:
            raise Exception(f'Unknown icon {icon_name}')

        return self.style().standardIcon(icon)

    def _on_click(self, index):
        if index.isValid():
            self.cellClicked.emit(index.row(), index.column())

    def _enable_widgeted_cells(self):
        return # NOTE not set up yet
        # Update all cells with WidgetedCell to have persistent editors
        model = self.model()
        if model is None:
            return
        for r in range(model.rowCount()):
            for c in range(model.columnCount()):
                idx = model.index(r,c)
                d = model.data(idx, TableModel.RawDataRole)
                # if isinstance(d, WidgetedCell):
                #     self.openPersistentEditor(idx)

class TableWidget(QWidget):
    # controls TableView & buttons/actions within tab

    def __init__(self, parent=None):
        super().__init__(parent)
        name = self.__class__.__name__
        self.title = f.config['TableName']['Class'][name]

        mainwindow = ui.get_mainwindow()
        minesite = ui.get_minesite()

        vLayout = QVBoxLayout(self)
        btnbox = QHBoxLayout()
        btnbox.setAlignment(Qt.AlignLeft)

        # get default refresh dialog from refreshtables by name
        from . import refreshtables as rtbls
        refresh_dialog = getattr(rtbls, name, rtbls.RefreshTable)
        self.query = getattr(qr, name, qr.QueryBase)()
        dbtable = self.query.update_table
        db_col_map = {}

        # try getting inner-classed tableview, if not use default
        view = getattr(self, 'View', TableView)(parent=self)

        vLayout.addLayout(btnbox)
        vLayout.addWidget(view)

        f.set_self(self, vars())

        self.add_button(name='Refresh', func=self.show_refresh)
        self.add_button(name='Add New', func=self.show_addrow)
        # self.add_button(name='Resize Rows', func=view.resizeRowsToContents)
    
    def add_action(self, name, func, shortcut=None, btn=False):
        act = QAction(name, self, triggered=func)

        if not shortcut is None:
            act.setShortcut(QKeySequence(shortcut))
            self.addAction(act)
        
        if btn:
            self.add_button(act=act)

    def add_button(self, name=None, func=None, act=None):
        if not act is None:
            name = act.text()
            func = act.triggered
        
        btn = QPushButton(name, self)
        btn.setMinimumWidth(60)
        btn.clicked.connect(func)
        self.btnbox.addWidget(btn)      
   
    def add_shortcut(self, name, func, shortcut=None):
        act = QAction(name, self, triggered=func)
        act.setShortcut(QKeySequence(shortcut))
        self.addAction(act)
        return act

    def show_addrow(self):
        dlg = dlgs.AddEvent(parent=self)
        dlg.exec_()

    def show_component(self):
        dlg = dlgs.ComponentCO(parent=self)
        dlg.exec_()
            
    def show_refresh(self):
        dlg = self.refresh_dialog(parent=self)
        dlg.exec_()

    def refresh_lastweek(self, default=False):
        fltr = self.query.fltr
        if default:
            self.query.set_minesite()
        self.query.set_lastweek()
        self.refresh()

    def refresh_lastmonth(self, default=False):
        # self.sender() = PyQt5.QtWidgets.QAction > could use this to decide on filters
        fltr = self.query.fltr
        if default:
            self.query.set_minesite()
        self.query.set_lastmonth()
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
            self.view.display_data(df=df)
        else:
            dlgs.msg_simple(msg='No rows returned in query!', icon='warning')

    def get_dbtable(self, header=None):
        # return dbtable for specific header
        m = self.db_col_map
        dbtable = self.dbtable if header is None or not header in m else getattr(dbm, m[header])
        return dbtable

    def email_table(self, subject='', body='', email_list=[], df=None):
        # TODO optional show table vs just excel file, consider temp files too
        style = self.view.get_style(df=df, outlook=True)

        msg_ = 'Include table in email body?'
        style_body = ''
        if dlgs.msgbox(msg=msg_, yesno=True):
            style_body = style \
                .pipe(self.query.background_gradient, theme='light') \
                .hide_index().render()

        body = f'{body}<br><br>{style_body}' # add in table to body msg

        # show new email
        msg = em.Message(subject=subject, body=body, to_recip=email_list, show_=False)
        
        msg_ = 'Would you like to attach an excel file of the data?'
        if dlgs.msgbox(msg=msg_, yesno=True):
            p = self.save_excel(style=style, name=self.name)
            msg.add_attachment(p)
            p.unlink()

        msg.show()
    
    def save_excel(self, style, p=None, name='temp'):
        if p is None:
            p = f.datafolder / f'csv/{name}.xlsx'
        style.to_excel(p, index=False, freeze_panes=(1,0))
        return p

class EventLogBase(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        view = self.view
        view.highlight_funcs['Status'] = view.highlight_by_val
        view.hide_cols = ('UID',)
        view.disabled_cols = ('Model', 'Serial')
        view.highlight_vals.update({
            'closed': 'goodgreen',
            'open': 'bad',
            'complete': 'goodgreen',
            'work in progress': 'lightorange',
            'waiting customer': 'lightorange',
            'monitor': 'lightyellow',
            'planned': 'lightyellow',
            'waiting parts (up)': 'lightyellow',
            'missing info': 'lightyellow',
            'waiting parts (down)': 'bad',
            'x': 'good'})
        
        view.formats.update({
            'Unit SMR': '{:,.0f}',
            'Comp SMR': '{:,.0f}',
            'Part SMR': '{:,.0f}',
            'SMR': '{:,.0f}'})

        items = f.config['Lists'][f'{self.name}Status']
        view.set_combo_delegate(col='Status', items=items)

class EventLog(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        view = self.view
        view.disabled_cols = ('Title',) # TODO: remove thise
        view.col_widths.update(dict(Passover=50, Description=800, Status=100))
        view.highlight_funcs['Passover'] = view.highlight_by_val
        
class WorkOrders(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        view = self.view 
        view.col_widths.update({
            'Work Order': 90,
            'Customer WO': 80,
            'Customer PO': 90,
            'Comp CO': 50,
            'Comments': 400,
            'Seg': 30})
        
        view.highlight_funcs['Pics'] = view.highlight_pics

        lists = f.config['Lists']
        view.set_combo_delegate(col='Wrnty', items=lists['WarrantyType'])
        view.set_combo_delegate(col='Comp CO', items=lists['TrueFalse'])

class ComponentCO(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
    
    class View(TableView):
        def __init__(self, parent=None):
            super().__init__(parent=parent)

            self.disabled_cols = ('MineSite', 'Model', 'Unit', 'Component', 'Side')
            self.col_widths.update(dict(Notes=400))
            self.highlight_funcs['Unit'] = self.highlight_alternating

            self.set_combo_delegate(col='Reman', items=['True', 'False'])

            items = ['High Hour Changeout', 'Damage/Abuse', 'Convenience', 'Failure', 'Pro Rata Buy-in', 'Warranty']
            self.set_combo_delegate(col='Removal Reason', items=items)

class TSI(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        view = self.view
        view.disabled_cols = ('WO',)
        view.col_widths.update({'Details': 400, 'TSI No': 100})

        self.add_button(name='TSI Homepage', func=self.open_tsi_homepage)
        self.add_button(name='Fill TSI Webpage', func=self.fill_tsi_webpage)
        self.add_button(name='Refresh Open (User)', func=self.refresh_allopen_user)
    
    def refresh_allopen_user(self):
        username = self.mainwindow.username
        query = self.query
        query.set_allopen()
        query.fltr.add(vals=dict(TSIAuthor=username))
        self.refresh()
       
    @property
    def driver(self):
        # save driver for use between TSI webpage calls
        return self._driver if hasattr(self, '_driver') else None
    
    @driver.setter
    def driver(self, driver):
        self._driver = driver
       
    def open_tsi_homepage(self):
        # just login and show the homepage so user can go from there, check TSIs etc
        from .. import web
        tsi = web.TSIWebPage(parent=self, _driver=self.driver)
        if not tsi.is_init: return
        tsi.tsi_home()
        self.driver = tsi.driver
    
    def fill_tsi_webpage(self):
        # TODO make this secondary process
        from .. import web
        view = self.view
        e = view.row_from_activerow().create_model_from_db()
        e2 = view.model_from_activerow()
        
        d = e.DateAdded.strftime('%-m/%-d/%Y')

        field_vals = {
            'Failure Date': d,
            'Repair Date': d,
            'Failure SMR': e.SMR,
            'Hours On Parts': e.ComponentSMR,
            'Serial': e.SNRemoved,
            'Part Number': e.PartNumber,
            'Part Name': e.TSIPartName,
            'New Part Serial': e.SNInstalled,
            'Work Order': e.WorkOrder,
            'Complaint': e.TSIDetails}

        msg = 'Would you like to save the TSI after it is created?'
        save_tsi = True if dlgs.msgbox(msg=msg, yesno=True) else False
            
        tsi = web.TSIWebPage(
            field_vals=field_vals,
            serial=e2.Serial,
            model=e2.Model,
            _driver=self.driver,
            parent=self)
        
        if not tsi.is_init: return

        tsi.open_tsi(save_tsi=save_tsi)
        self.driver = tsi.driver

        # fill tsi number back to current row
        if not tsi.tsi_number is None:
            index = view.create_index_activerow(col_name='TSI No')
            view.model().setData(index=index, val=tsi.tsi_number)

        dlgs.msg_simple(msg=f'New TSI created.\nTSI Number: {tsi.tsi_number}')

class UnitInfo(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        view = self.view
        view.disabled_cols = ('SMR Measure Date', 'Current SMR', 'Warranty Remaining', 'GE Warranty')
        view.col_widths.update({
            'Warranty Remaining': 40,
            'GE Warranty': 40})
        view.formats.update({
            'Current SMR': '{:,.0f}',
            'Engine Serial': '{:.0f}'})

class FCBase(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.add_button(name='Import FCs', func=lambda: fc.importFC(upload=True))
        self.add_button(name='View FC Folder', func=self.view_fc_folder)
   
    def get_fc_folder(self):
        if not fl.drive_exists():
            return

        row = self.view.model_from_activerow()
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
        view = self.view
        view.hide_cols = ('MineSite',)
        view.disabled_cols = ('FC Number', 'Total Complete', '% Complete') # also add all unit cols?
        view.col_widths.update({
            'Subject': 250,
            'Comments': 600,
            'Action Reqd': 60,
            'Type': 40,
            'Part Number': 100,
            'Parts Avail': 40,
            'Total Complete': 60,
            '% Complete': 40})

        view.highlight_vals.update({'m': 'maroon'})
        view.highlight_funcs['Type'] = view.highlight_by_val

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
        df = self.view.df_from_activerow().iloc[:, :10]
        style = st.set_style(df=df)
        formats = {'int64': '{:,}', 'datetime64[ns]': '{:%Y-%m-%d}'}
        m = st.format_dtype(df=df, formats=formats)
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
        view = self.view
        view.disabled_cols = ('MineSite', 'Model', 'Unit', 'FC Number', 'Complete', 'Closed', 'Type', 'Subject')
        view.col_widths.update({
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

class Availability(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.report = None

        self.add_action(name='Create Report', func=self.create_report, btn=True)
        self.add_action(name='Email Report', func=self.email_report, btn=True)
        self.add_action(name='Email Assignments', func=self.email_assignments, shortcut='Ctrl+Shift+E', btn=True)
        self.add_action(name='Filter Assigned', func=self.filter_assigned, shortcut='Ctrl+Shift+A', btn=True)
        self.add_action(name='Save Assignments', func=self.save_assignments, btn=True)
        self.add_action(name='Assign Suncor', func=self.assign_suncor, shortcut='Ctrl+Shift+Z')
        self.add_action(name='Show Unit EL', func=self.filter_unit_eventlog, shortcut='Ctrl+Shift+F', btn=True)

    class View(TableView):
        def __init__(self, parent):
            super().__init__(parent=parent)

            self.disabled_cols = ('Unit', 'ShiftDate', 'StartDate', 'EndDate')
            self.datetime_cols = ('StartDate', 'EndDate')
            self.col_widths.update(dict(Comment=600))
            self.highlight_funcs['Unit'] = self.highlight_alternating
            self.add_highlight_funcs(cols=['Category Assigned', 'Assigned'], func=self.highlight_by_val)
            self.add_col_funcs(cols=['SMS', 'Suncor'], func=self.update_duration)

            self.formats.update({
                'Total': '{:,.2f}',
                'SMS': '{:,.2f}',
                'Suncor': '{:,.2f}'})

            # TODO move this to an after_init, first time tab selected
            p = f.datafolder / 'csv/avail_resp.csv'
            df = pd.read_csv(p)
            self.set_combo_delegate(col='Category Assigned', items=f.clean_series(s=df['Category Assigned']))

            self.highlight_vals.update({
                's1 service': 'lightyellow',
                's4 service': 'lightblue',
                's5 service': 'lightgreen',
                '0': 'greyrow',
                'collecting info': 'lightyellow'})

        def get_style(self, df=None, outlook=False):
            return super().get_style(df=df, outlook=outlook) \
                .pipe(st.set_column_widths, vals=dict(StartDate=300, EndDate=300))

        def update_duration(self, index):
            # Set SMS/Suncor duration if other changes
            model = index.model()
            col_name = model.headerData(i=index.column())

            duration = model.df.iloc[index.row(), model.get_column_idx('Total')]
            val = index.data(role=TableModel.RawDataRole)

            if col_name == 'SMS':
                update_col = model.get_column_idx('Suncor')
            elif col_name == 'Suncor':
                update_col = model.get_column_idx('SMS')

            update_index = index.siblingAtColumn(update_col)
            update_val = duration - val
            model.setData(index=update_index, val=update_val, triggers=False)

    def get_email_list(self, email_type='Daily'):
        # get email list from csv
        p = f.datafolder / 'csv/avail_email.csv'
        df2 = pd.read_csv(p)
        
        return list(df2[df2[email_type]==1].Email)

    def email_table(self):
        self.email_assignments(filter_assignments=False)

    def email_assignments(self, filter_assignments=True):
        model = self.view.model()
        df = model.df
        if filter_assignments:
            df = df[df.Assigned==0]

        df = df.iloc[:, :-1]

        s = df.ShiftDate
        fmt = '%Y-%m-%d'
        maxdate, mindate = s.max(), s.min()
        if not maxdate == mindate:
            dates = '{} - {}'.format(mindate.strftime(fmt), maxdate.strftime(fmt))
        else:
            dates = maxdate.strftime(fmt)

        subject = f'Downtime Assignment | {dates}'

        body = f'{f.greeting()}See below for current downtime assignments. Please correct and respond with any updates as necessary.'

        # p = f.topfolder.parent / 'avail.html'
        # with open(str(p), 'w+') as file:
        #     file.write(style.render())

        super().email_table(subject=subject, body=body, email_list=self.get_email_list(), df=df)
        
    def save_assignments(self):
        model = self.view.model()
        cols = ['Total', 'SMS', 'Suncor', 'Category Assigned', 'Comment']
        txn = el.DBTransaction(table_model=model, update_cols=cols)
        
        df = model.df
        df = df[df.Assigned==0]

        msg = f'Would you like to update [{len(df)}] records in the database?'
        if not dlgs.msgbox(msg=msg, yesno=True):
            return

        txn.add_df(df)
        txn.update_all()
        
        dlgs.msg_simple(msg='Records updated.')
    
    def filter_assigned(self):
        # filter unassigned items out or back into table
        model = self.view.model()
        name_index = self.view.nameindex_from_activerow() # TODO probably connect this to a signal so can use other places

        if not hasattr(self, 'filter_state') or not self.filter_state:
            model.filter_by_items(col='Assigned', items=[str(0)])
            self.filter_state = True
            
        else:
            model.reset()
            self.filter_state = False

        if not name_index is None:
            self.view.select_by_nameindex(name_index=name_index)
    
    def assign_suncor(self):
        # func ctrl+shift+Z to auto assign suncor
        # TODO loop selected rows and bulk update
        view = self.view
        model = view.model()

        index = view.create_index_activerow(col_name='Suncor')
        duration = model.df.iloc[index.row(), model.get_column_idx('Total')]
        model.setData(index=index, val=duration)
    
    def filter_unit_eventlog(self):
        # filter eventlog to currently selected unit and jump to table
        view = self.view
        unit = view.create_index_activerow('Unit').data()

        title = 'Event Log'
        tabs = self.mainwindow.tabs
        table_widget = tabs.get_widget(title)

        if table_widget.view.model().rowCount() == 0:
            table_widget.refresh_lastmonth(default=True)

        table_widget.view.model().filter_by_items(col='Unit', items=[unit])
        tabs.activate_tab(title)

    def get_report_base(self, period_type):
        return Path(f.drive / f.config['FilePaths']['Availability'] / f'{self.minesite}/{period_type.title()}ly')

    def get_report_name(self, period_type, name):
        return f'Suncor Reconciliation Report - {self.minesite} - {period_type.title()}ly - {name}'
    
    def get_report_path(self, p_base, name):
        return p_base / f'{name}.pdf'
    
    def create_report(self):
        # show menu to select period
        from .refreshtables import AvailReport
        from ..reports import AvailabilityReport
        from ..folders import drive_exists

        dlg = AvailReport(parent=self)
        if not drive_exists() or not dlg.exec_(): return

        rep = AvailabilityReport(d_rng=dlg.d_rng, period_type=dlg.period_type, name=dlg.name)
        rep.load_all_dfs()

        p_base = self.get_report_base(dlg.period_type)
        p = rep.create_pdf(p_base=p_base)
        self.report = rep

        fl.open_folder(p)

        msg = f'Report:\n\n"{rep.title}"\n\nsuccessfully created. Email now?'
        if dlgs.msgbox(msg=msg, yesno=True):
            self.email_report(period_type=dlg.period_type, p_rep=p, name=dlg.name)
        
    def email_report(self, period_type=None, p_rep=None, name=None):
        from .refreshtables import AvailReport
        title = self.get_report_name(period_type, name)
        
        if period_type is None:
            dlg = AvailReport(parent=self)
            if not dlg.exec_(): return
            d_rng, period_type, name = dlg.d_rng, dlg.period_type, dlg.name
        
        if p_rep is None:
            p_rep = self.get_report_path(p_base=self.get_report_base(period_type), name=name)

        body = f'{f.greeting()}See attached report for availability {name}.'

        if not self.report is None:
            rep = self.report
            style1 = rep.style_df('Fleet Availability', outlook=True).hide_index().render()
            style2 = rep.style_df('Summary Totals', outlook=True).hide_index().render()

            template = rep.env.get_template('exec_summary_template.html')
            template_vars = dict(
                exec_summary=rep.exec_summary,
                d_rng=rep.d_rng)

            html_exec = template.render(template_vars)

            body = f'{body}<br>{html_exec}<br>{style1}<br><br>{style2}'

        msg = em.Message(subject=title, body=body, to_recip=self.get_email_list('Reports'), show_=False)
        msg.add_attachment(p_rep)
        msg.show()


# FILTER MENU
class FilterMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

class DynamicFilterLineEdit(QLineEdit):
    # Filter textbox for a DataFrameTable

    def __init__(self, *args, **kwargs):
        _always_dynamic = kwargs.pop('always_dynamic', False)
        super().__init__(*args, **kwargs)

        col_to_filter, _df_orig, _host = None, None, None
        f.set_self(self, vars())

    def bind_dataframewidget(self, host, icol):
        # Bind tihs DynamicFilterLineEdit to a DataFrameTable's column

        self.host = host
        self.col_to_filter = icol
        self.textChanged.connect(self._update_filter)

    @property
    def host(self):
        if self._host is None:
            raise RuntimeError("Must call bind_dataframewidget() "
            "before use.")
        else:
            return self._host

    @host.setter
    def host(self, value):
        if not isinstance(value, TableView):
            raise ValueError(f'Must bind to a TableModel, not {value}')
        else:
            self._host = value

        if not self._always_dynamic:
            self.editingFinished.connect(self._host._data_model.endDynamicFilter)

    def focusInEvent(self, QFocusEvent):
        self._host._data_model.beginDynamicFilter()
        super().focusInEvent(QFocusEvent)

    def _update_filter(self, text):
        # Called everytime we type in the filter box
        icol = self.col_to_filter

        self.host.model().filter(icol, text)

class DynamicFilterMenuAction(QWidgetAction):
    """Filter textbox in column-header right-click menu"""
    def __init__(self, parent, menu, icol):
        super().__init__(parent)

        parent_menu = menu

        # Build Widgets
        widget = QWidget()
        layout = QHBoxLayout()
        label = QLabel('Filter')
        text_box = DynamicFilterLineEdit()
        text_box.bind_dataframewidget(self.parent(), icol)
        text_box.returnPressed.connect(self._close_menu)

        layout.addWidget(label)
        layout.addWidget(text_box)
        widget.setLayout(layout)

        self.setDefaultWidget(widget)
        f.set_self(self, vars())

    def _close_menu(self):
        """Gracefully handle menu"""
        self.parent_menu.close()

class FilterListMenuWidget(QWidgetAction):
    """Filter textbox in column-right click menu"""
    def __init__(self, parent, menu, icol):
        super().__init__(parent)

        # Build Widgets
        widget = QWidget()
        layout = QVBoxLayout()
        lst_widget = QListWidget()
        lst_widget.setFixedHeight(200)

        layout.addWidget(lst_widget)
        widget.setLayout(layout)

        self.setDefaultWidget(widget)

        # Signals/slots
        lst_widget.itemChanged.connect(self.on_list_itemChanged)
        self.parent().dataFrameChanged.connect(self._populate_list)

        f.set_self(self, vars())
        self._populate_list(inital=True)

    def _populate_list(self, inital=False):
        self.lst_widget.clear()
        model = self.parent.model()

        df = model._df_orig
        col = df.columns[self.icol]
        
        full_col = f.clean_series(s=df[col], convert_str=True) # All Entries possible in this column
        disp_col = f.clean_series(s=model.df[col], convert_str=True) # Entries currently displayed

        def _build_item(item, state=None):
            i = QListWidgetItem(f'{item}')
            i.setFlags(i.flags() | Qt.ItemIsUserCheckable)

            if state is None:
                if item in disp_col:
                    state = Qt.Checked
                else:
                    state = Qt.Unchecked

            i.setCheckState(state)
            i.checkState()
            self.lst_widget.addItem(i)
            return i

        # Add a (Select All)
        if full_col == disp_col:
            select_all_state = Qt.Checked
        else:
            select_all_state = Qt.Unchecked

        self._action_select_all = _build_item('(Select All)', state=select_all_state)

        # Add filter items
        if inital:
            build_list = full_col
        else:
            build_list = disp_col

        for i in build_list:
            _build_item(i)

        # Add a (Blanks)
        # TODO

    def on_list_itemChanged(self, item):
        ###
        # Figure out what "select all" check-box state should be
        ###
        lst_widget = self.lst_widget
        count = lst_widget.count()

        lst_widget.blockSignals(True)
        if item is self._action_select_all:
            # Handle "select all" item click
            if item.checkState() == Qt.Checked:
                state = Qt.Checked
            else:
                state = Qt.Unchecked

            # Select/deselect all items
            for i in range(count):
                if i is self._action_select_all: continue
                i = lst_widget.item(i)
                i.setCheckState(state)
        else:
            # Non "select all" item; figure out what "select all" should be
            if item.checkState() == Qt.Unchecked:
                self._action_select_all.setCheckState(Qt.Unchecked)
            else:
                # "select all" only checked if all other items are checked
                for i in range(count):
                    i = lst_widget.item(i)
                    if i is self._action_select_all: continue
                    if i.checkState() == Qt.Unchecked:
                        self._action_select_all.setCheckState(Qt.Unchecked)
                        break
                else:
                    self._action_select_all.setCheckState(Qt.Checked)

        lst_widget.blockSignals(False)

        ###
        # Filter dataframe according to list
        ###
        items = []
        for i in range(count):
            i = lst_widget.item(i)
            if i is self._action_select_all: continue
            if i.checkState() == Qt.Checked:
                items.append(str(i.text()))

        parent = self.parent
        parent.blockSignals(True)
        parent.model().filter_by_items(items, icol=self.icol)
        parent.blockSignals(False)
        parent._enable_widgeted_cells()

