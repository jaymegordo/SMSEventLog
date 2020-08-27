import re

from .. import email as em
from .. import errors as er
from .. import factorycampaign as fc
from .. import functions as f
from .. import queries as qr
from .. import styles as st
from . import _global as gbl
from . import dialogs as dlgs
from . import eventfolders as efl
from .__init__ import *
from .datamodel import TableModel
from .delegates import (CellDelegate, ComboDelegate, DateDelegate,
                        DateTimeDelegate)
from .multithread import Worker

log = logging.getLogger(__name__)

# TODO change how multiple selection works, don't select all rows
# TODO row selection - highlight behind existing cell colors
# TODO highlight header red when filter active
# TODO add tsi status to WO page


class TableView(QTableView):
    dataFrameChanged = pyqtSignal()
    cellClicked = pyqtSignal(int, int)

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.activated.connect(self.double_click_enter)
        mainwindow = gbl.get_mainwindow()

        self.mcols = dd(tuple)
        col_widths = {'Title': 150, 'Part Number': 150, 'Failure Cause': 300}
        highlight_funcs, col_func_triggers, formats = dd(type(None)), dd(list), {} # NOTE use all lowercase!
        highlight_vals = {
                'true': 'goodgreen',
                'false': 'bad'}

        colors = f.config['color']

        query = parent.query
        formats.update(query.formats) # start with query formats, will be overridden if needed
        
        # set up initial empty model
        self.parent = parent # model needs this to access parent table_widget
        self.table_widget = parent if isinstance(parent, TableWidget) else None
        _data_model = TableModel(parent=self)
        self.setModel(_data_model)
        rows_initialized = True

        # Signals/Slots
        _data_model.modelReset.connect(self.dataFrameChanged)
        _data_model.dataChanged.connect(self.dataFrameChanged)
        self.clicked.connect(self._on_click) # NOTE not sure if need this..
        self.dataFrameChanged.connect(self._enable_widgeted_cells) # NOTE or this

        header = HeaderView(self)
        self.setHorizontalHeader(header)

        self.setItemDelegate(CellDelegate(parent=self))
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setSelectionBehavior(QTableView.SelectRows)
        self.setWordWrap(True)
        self.setSortingEnabled(True)

        # yellowrow = colors['bg'].get('yellowrow', 'green')
        yellowrow = '#ffff64'
        darkyellow = '#cccc4e'
        lightblue = '#148CD2' ##19232D # border: 1px solid red; 
        self.setStyleSheet(' \
            QTableView::item:selected {color: #000000; background-color: #ffff64;} \
            QTableView::item:selected:active {color: black; background-color: #ffff64;} \
            QTableView:item:selected:focus {color: black; background-color: #ffff64; border: 1px solid red; } \
            QTableView::item:selected:hover {color: black; background-color: #cccc4e;}') \
        
        f.set_self(vars())
        self.set_default_headers()
        self.setVisible(True)

    @property
    def e(self):
        return self.model_from_activerow()

    @property
    def e_db(self):
        return self.model_from_activerow_db()

    @property
    def i(self):
        return self.active_row_index()

    @property
    def row(self):
        return self.row_from_activerow()

    def display_data(self, df):
        self.rows_initialized = False 
        self.model().set_df(df=df, center_cols=self.get_center_cols(df=df))
            
        self.hide_columns()
        self.resizeColumnsToContents()
        self.set_date_delegates()
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
            self.col_func_triggers[col].append(func)

    def highlight_alternating(self, df, row, col, role, **kw):
        # use count of unique values mod 2 to highlight alternating groups of values
        # TODO only works if column is sorted by unit
        # TODO make this work with irow/icol .. email table fails
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
                        if not color_code is None:
                            return QColor(color_code)

    def highlight_blanks(self, val, role, **kw):
        if val is pd.NA or val is np.NaN: val = None

        if val in ('', None):
            if role == Qt.BackgroundRole:
                return QColor(self.colors['bg']['bad'])
            elif role == Qt.ForegroundRole:
                return QColor(self.colors['text']['bad'])

    def highlight_pics(self, val, role, **kw):
        color = 'goodgreen' if f.isnum(val) and val > 0 else 'bad'

        if role == Qt.BackgroundRole:
            color_code = self.colors['bg'][color]
        elif role == Qt.ForegroundRole:
            color_code = self.colors['text'][color]
        
        return QColor(color_code)

    def highlight_color_scale(self, val, **kw):
        # highlight values using max/min within range of multiple columns

        if self.col_maxmin is None:
            df = self.model().df
            df = df[self.maxmin_cols]
            self.col_maxmin = tuple(df.max().max(), df.min().min())

        return

    def get_style(self, df=None, outlook=False, exclude_cols=None):
        model = self.model()
        if df is None:
            df = model.df
        
        # only pass a subset to get_background_colors if exclude_cols are passed
        kw = dict(subset=[c for c in df.columns if not c in exclude_cols]) if not exclude_cols is None else {}

        s = []
        s.append(dict(
            selector='table',
            props=[('border', '1px solid black')]))

        return st.default_style(df=df, outlook=outlook) \
            .apply(model.get_background_colors_from_df, axis=None, **kw) \
            .format(self.formats) \
            .pipe(st.add_table_style, s=s)

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
        elif event.key() == Qt.Key_D and event.modifiers() == Qt.ControlModifier:
            self.fill_down()
        else:
            super().keyPressEvent(event)

    def set_default_headers(self):
        cols = f.get_default_headers(title=self.parent.title)
        df = pd.DataFrame(columns=cols) \
            .pipe(f.parse_datecols) \
            .pipe(f.set_default_dtypes, m=self.parent.query.default_dtypes)

        self.display_data(df=df)

    def set_date_delegates(self):
        model = self.model()
        date_delegate = DateDelegate(self)

        for i in model.mcols['date']:
            col = model.headerData(i)
            self.formats[col] = '{:%Y-%m-%d}'
            self.setColumnWidth(i, date_delegate.width)
            self.setItemDelegateForColumn(i, date_delegate)

        # if the parent table_widget has specified datetime cols
        if self.mcols['datetime']:
            datetime_delegate = DateTimeDelegate(self)
            for i in model.mcols['datetime']:
                self.setColumnWidth(i, datetime_delegate.width)
                col = model.headerData(i)
                self.formats[col] = '{:%Y-%m-%d     %H:%M}'
                self.setItemDelegateForColumn(i, datetime_delegate)

    def set_combo_delegate(self, col, items):
        model = self.model()
        combo_delegate = ComboDelegate(parent=self, items=items)
        c = model.get_col_idx(col=col)
        self.setItemDelegateForColumn(c, combo_delegate)

    def set_column_width(self, cols, width):
        model = self.model()
        if not isinstance(cols, list): cols = [cols]

        for c in cols:
            if c in model.df.columns:
                self.setColumnWidth(model.get_col_idx(c), width)
    
    def set_column_widths(self):
        model = self.model()

        for c, width in self.col_widths.items():
            if c in model.df.columns:
                self.setColumnWidth(model.get_col_idx(c), width)

    def hide_columns(self):
        for col in self.mcols['hide']:
            self.hideColumn(self.model().get_col_idx(col))

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
            icol = self.selectionModel().currentIndex().column()
        else:
            icol = model.get_col_idx(col_name)

        if None in (irow, icol): return
        return model.createIndex(irow, icol)
    
    def get_irow_uid(self, uid):
        # get irow from uid
        # TODO this is only for EventLog tables with UID, should probably adapt this for any key
        df = self.model().df

        index = df[df.UID==uid].index
        if len(index.values) == 1:
            irow = index.values[0] # uid exists in df.UID
        else:
            irow = None # uid doesn't exist

        return irow

    def active_row_index(self):
        rows = self.selectionModel().selectedRows() # list of selected rows
        if rows:
            return rows[0].row()
        else:
            msg = 'No row selected in table.'
            dlgs.msg_simple(msg=msg, icon='warning')
            return None
    
    def row_from_activerow(self):
        i = self.active_row_index()
        if i is None: return
        return dbt.Row(table_model=self.model(), i=i)

    def model_from_activerow(self):
        # only returns values in current table view, not all database
        i = self.active_row_index()
        if i is None: return
        return self.model().create_model(i=i)
    
    def model_from_activerow_db(self):
        # create model from db (to access all fields, eg MineSite)
        # NOTE this relies on MineSite being a field in Event Log > can also use db.get_df_unit() for model/minesite
        row = self.row_from_activerow()
        if row is None: return
        return row.create_model_from_db() # TODO this won't work with mixed tables eg FCSummary
    
    def df_from_activerow(self, i=None):
        if i is None:
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
        print(f'len index: {len(indexes)}')

        # Capture selection into a DataFrame
        df = pd.DataFrame() # NOTE may need to set size?
        for idx in indexes:
            row, col, item = idx.row(), idx.column(), idx.data()
            print(row, col, item)
        
        return

            # if item:
            #     df.iloc[row, col] = str(item)

        # Make into tab-delimited text (best for Excel)
        items = list(df.itertuples(index=False))
        s = '\n'.join(['\t'.join([cell for cell in row]) for row in df])

        # Send to clipboard
        QApplication.clipboard().setText(s)

    def fill_down(self):
        index = self.create_index_activerow()
        if index.row() == 0: return # cant fill down at first row

        model = self.model()
        index_copy = index.siblingAtRow(index.row() - 1)

        val = index_copy.data(role=model.RawDataRole)
        model.setData(index=index, val=val)

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

    def get_center_cols(self, *a, **kw):
        return self.mcols['center']

    def remove_row(self, i=None):
        # default, just remove row from table view
        if i is None: i = self.active_row_index()
        self.model().removeRows(i=i)

    def update_statusbar(self, msg):
        if not self.mainwindow is None:
            self.mainwindow.update_statusbar(msg=msg)

class TableWidget(QWidget):
    # controls TableView & buttons/actions within tab

    def __init__(self, parent=None):
        super().__init__(parent)
        name = self.__class__.__name__
        self.name = name
        self.title = f.config['TableName']['Class'][name]

        self.mainwindow = gbl.get_mainwindow()

        vLayout = QVBoxLayout(self)
        btnbox = QHBoxLayout()
        btnbox.setAlignment(Qt.AlignLeft)

        # get default refresh dialog from refreshtables by name
        from . import refreshtables as rtbls
        refresh_dialog = getattr(rtbls, name, rtbls.RefreshTable)
        self.query = getattr(qr, name, qr.QueryBase)(parent=self, theme='dark')
        dbtable = self.query.update_table
        db_col_map = {}

        # try getting inner-classed tableview, if not use default
        view = getattr(self, 'View', TableView)(parent=self)

        vLayout.addLayout(btnbox)
        vLayout.addWidget(view)

        f.set_self(vars())

        self.add_button(name='Refresh', func=self.show_refresh)
    
    @property
    def minesite(self):
        return self.mainwindow.minesite if not self.mainwindow is None else 'FortHills' # default for testing
    
    @property
    def e(self):
        return self.view.e

    @property
    def e_db(self):
        return self.view.e_db

    @property
    def i(self):
        return self.view.i

    @property
    def row(self):
        return self.view.row
        
    def add_action(self, name, func, shortcut=None, btn=False):
        act = QAction(name, self, triggered=er.e(func))

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

    def show_component(self, **kw):
        dlg = dlgs.ComponentCO(parent=self)
        dlg.exec_()
            
    def show_refresh(self):
        dlg = self.refresh_dialog(parent=self)
        dlg.exec_()

    def show_details(self):
        # get model of selected row
        model = self.view.row_from_activerow().create_model_from_db()
        df = dbt.df_from_row(model=model)

        # load to details view
        dlg = dlgs.DetailsView(parent=self, df=df)
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
        # return dbtable (definition) for specific header
        m = self.db_col_map
        dbtable = self.dbtable if header is None or not header in m else getattr(dbm, m[header])
        return dbtable

    def email_table(self, subject='', body='', email_list=None, df=None, prompts=True):
        # TODO make this an input dialog so settings can be remembered
        style = self.view.get_style(df=df, outlook=True) # this will have all colors in current GUI table

        msg_ = 'Include table in email body?'
        style_body = ''
        if prompts:
            include_style = dlgs.msgbox(msg=msg_, yesno=True)
        
        if not df is None or include_style:
            style_body = style.hide_index().render()

        body = f'{body}<br><br>{style_body}' # add in table to body msg

        # show new email
        msg = em.Message(subject=subject, body=body, to_recip=email_list, show_=False)
        
        if prompts:
            msg_ = 'Would you like to attach an excel file of the data?'
            if dlgs.msgbox(msg=msg_, yesno=True):
                p = self.save_excel(style=style, name=self.name)
                msg.add_attachment(p)
                p.unlink()

        msg.show()
    
    def save_excel(self, style, p=None, name='temp'):
        if p is None:
            p = f.datafolder / f'csv/{name}.xlsx'

        try:
            style.to_excel(p, index=False, freeze_panes=(1,0))
            return p
        except:
            return None
    
    def export_excel(self):
        # export current table as excel file, prompt user for location
        from .. import folders as fl

        p = dlgs.save_file(name=self.title)
        if p is None: return

        style = self.view.get_style(df=None, outlook=True)

        p = self.save_excel(style=style, name=self.name, p=p)
        if not p is None:
            msg = f'File created:\n\n{p}\n\nOpen now?'
            if dlgs.msgbox(msg=msg, yesno=True):
                fl.open_folder(p=p, check_drive=False)

    def remove_row(self):
        # default, just remove from table view (doesn't do anything really)
        self.view.remove_row()

    def update_statusbar(self, msg):
        if not self.mainwindow is None:
            self.mainwindow.update_statusbar(msg=msg)

class EventLogBase(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.add_button(name='Add New', func=self.show_addrow)

    class View(TableView):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.add_col_funcs(['Work Order', 'Title', 'Date Added'], self.update_eventfolder_path)
            self.add_col_funcs('Status', self.parent.close_event)
            self.highlight_funcs['Status'] = self.highlight_by_val
            self.highlight_funcs['Pics'] = self.highlight_pics
            self.mcols['hide'] = ('UID',)
            self.mcols['longtext'] = ('Description', 'Failure Cause', 'Comments', 'Details', 'Notes')
            self.mcols['disabled'] = ('Model', 'Serial')
            self.highlight_vals.update({
                'closed': 'goodgreen',
                'open': 'bad',
                'action required': 'bad',
                'complete': 'goodgreen',
                'work in progress': 'lightorange',
                'waiting customer': 'lightorange',
                'monitor': 'lightyellow',
                'planned': 'lightyellow',
                'waiting parts (up)': 'lightyellow',
                'missing info': 'lightyellow',
                'waiting parts (down)': 'bad',
                'x': 'good'})
            
            self.formats.update({
                'Unit SMR': '{:,.0f}',
                'Comp SMR': '{:,.0f}',
                'Part SMR': '{:,.0f}',
                'SMR': '{:,.0f}'})

            items = f.config['Lists'][f'{self.parent.name}Status']
            self.set_combo_delegate(col='Status', items=items)
        
        def update_eventfolder_path(self, index, val_prev, **kw):
            # update event folder path when Title/Work Order/Date Added changed
            e = self.e
            minesite = db.get_unit_val(e.Unit, 'MineSite')

            # get header from index
            header = index.model().headerData(i=index.column()).replace(' ', '').lower()
            if header == 'codate': header = 'dateadded' # little hack for component CO table

            ef = efl.get_eventfolder(minesite=minesite) \
                .from_model(e=e, table_model=self.model(), irow=index.row(), table_widget=self.parent) \
                .update_eventfolder_path(vals={header: val_prev})

    def close_event(self, index, **kw):
        # set DateCompleted to current date when status change to 'Closed' or 'Completed' (EL + WO only)
        # NOTE would be more ideal to queue change at start of setData and update all vals in bulk
        # NOTE could auto link those changes through setData eg auto_update_sibling_table
        if not self.title in ('Event Log', 'Work Orders'): return

        view, e, row = self.view, self.e, self.row
        if row is None: return

        if index.data() in ('Closed', 'Complete'):
            # update both StatusEvent and StatusWO in db
            d = dt.now().date()
            vals = dict(
                StatusEvent='Complete',
                StatusWO='Closed',
                DateCompleted=d)
            
            # set dateclosed in table view but don't update
            model = index.model()
            update_index = index.siblingAtColumn(model.get_col_idx('Date Complete'))

            # Update if DateComplete is null
            if not update_index.data():
                model.setData(index=update_index, val=d, triggers=False, update_db=False)

            row.update(vals=vals)
            self.update_statusbar(msg=f'Event closed: {e.Unit} - {d.strftime("%Y-%m-%d")} - {e.Title} ')
        
    def view_folder(self):
        view, i, e = self.view, self.i, self.e_db 
        minesite = db.get_unit_val(e.Unit, 'MineSite')

        # try to get minesite-specific EventFolder, if not use default
        efl.get_eventfolder(minesite=minesite).from_model(e=e, irow=i, table_model=view.model()).show()
    
    def remove_row(self):
        # remove selected event from table and delete from db
        view, e, row = self.view, self.e, self.row
        if row is None: return

        m = dict(Unit=e.Unit, DateAdded=e.DateAdded, Title=e.Title)

        msg = f'Are you sure you would like to permanently delete the event:\n\n{f.pretty_dict(m)}'
        if dlgs.msgbox(msg=msg, yesno=True):
            row.update(delete=True)
            view.remove_row(i=row.i)
            self.mainwindow.update_statusbar(msg=f'Event removed from database: {e.Unit} - {e.Title}')
    
class EventLog(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.add_action(name='Email Passover', func=self.email_passover, btn=True)

    class View(EventLogBase.View):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.col_widths.update(dict(Passover=50, Description=800, Status=100))
            self.highlight_funcs['Passover'] = self.highlight_by_val

        def get_style(self, df=None, outlook=False):
            return super().get_style(df=df, outlook=outlook) \
                .pipe(st.set_column_widths, vals=dict(Status=80, Description=400, Title=100), outlook=outlook)


    def email_passover(self):
        df = self.view.model().df

        cols = ['Status', 'Unit', 'Title', 'Description', 'Date Added']
        df = df[df.Passover.str.lower()=='x'] \
            .sort_values(by=['Unit', 'Date Added']) \
            [cols]
        
        df.Description = df.Description.apply(self.remove_old_dates)
        
        minesite = self.minesite
        company = 'SMS' if not 'cwc' in minesite.lower() else 'Cummins'
        d = dt.now().date().strftime('%Y-%m-%d')
        shift = 'DS' if 8 <= dt.now().hour <= 20 else 'NS'
        shift = f'{d} ({shift})'

        subject = f'{company} Passover {minesite} - {shift}'
        body = f'{f.greeting()}Please see updates from {shift}:<br>'

        query = qr.EmailList(minesite=minesite)
        df2 = query.get_df()
        email_list = df2[df2.Passover.notnull()].Email

        self.email_table(subject=subject, body=body, email_list=email_list, df=df, prompts=False)
    
    def remove_old_dates(self, s):
        # split description on newlines, remove old dates if too long, color dates red
        if s is None: return None
        lst = s.splitlines()
        cur_len, max_len = 0, 400

        for i, item in enumerate(lst[::-1]):
            cur_len += len(item)
            if cur_len >= max_len: break

        lst = lst[max(len(lst) - i - 1, 0):]
            
        # color dates red
        date_reg_exp = re.compile('(\d{4}[-]\d{2}[-]\d{2})')
        replace = r'<span style="color: red;">\1</span>'
        lst = [re.sub(date_reg_exp, replace, item) for item in lst]

        return '\n'.join(lst)
        
class WorkOrders(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    class View(EventLogBase.View):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.col_widths.update({
                'Work Order': 90,
                'Customer WO': 80,
                'Customer PO': 90,
                'Comp CO': 50,
                'Comments': 400,
                'Seg': 30,
                'Pics': 40})
            
            self.add_col_funcs('Comp CO', self.set_component)
            self.highlight_funcs['Comp CO'] = self.highlight_by_val

            lists = f.config['Lists']
            self.set_combo_delegate(col='Wrnty', items=lists['WarrantyType'])
            self.set_combo_delegate(col='Comp CO', items=lists['TrueFalse'])
        
        def set_component(self, val_new, **kw):
            if val_new == True:
                self.parent.show_component()

class ComponentCO(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
    
    class View(EventLogBase.View):
        def __init__(self, parent):
            super().__init__(parent=parent)

            self.mcols['disabled'] = ('MineSite', 'Model', 'Unit', 'Component', 'Side')
            self.col_widths.update(dict(Notes=400))
            self.highlight_funcs['Unit'] = self.highlight_alternating

            cols = ['Unit SMR', 'Comp SMR', 'SN Removed', 'SN Installed', 'Removal Reason']
            self.add_highlight_funcs(cols=cols, func=self.highlight_blanks)

            self.set_combo_delegate(col='Reman', items=['True', 'False'])

            items = ['High Hour Changeout', 'Damage/Abuse', 'Convenience', 'Failure', 'Pro Rata Buy-in', 'Warranty']
            self.set_combo_delegate(col='Removal Reason', items=items)

class TSI(EventLogBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.add_button(name='Create Failure Report', func=self.create_failure_report)
        self.add_button(name='TSI Homepage', func=self.open_tsi_homepage)
        self.add_button(name='Fill TSI Webpage', func=self.fill_tsi_webpage)
        self.add_button(name='Refresh Open (User)', func=self.refresh_allopen_user)
    
    def remove_row(self):
        view, e, row = self.view, self.e, self.row
        if row is None: return

        m = dict(Unit=e.Unit, DateAdded=e.DateAdded, Title=e.Title)

        msg = f'Are you sure you would like to remove the TSI for:\n\n{f.pretty_dict(m)}\n\n \
            (This will only set the TSI Status to Null, not delete the event).'
        if dlgs.msgbox(msg=msg, yesno=True):
            row.update(vals=dict(StatusTSI=None))
            view.remove_row(i=row.i)
            self.mainwindow.update_statusbar(msg=f'TSI removed: {e.Unit} - {e.Title}')

    class View(EventLogBase.View):
        def __init__(self, parent):
            super().__init__(parent=parent)
            # self.mcols['disabled'] = ('WO',)
            self.col_widths.update({'Details': 400, 'TSI No': 120})
        
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
        from ..web import TSIWebPage
        view, e, e2 = self.view, self.e_db, self.e

        d = e.DateAdded.strftime('%m/%d/%Y')

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
            'Complaint': e.Title,
            'Cause': e.FailureCause,
            'Notes': e.Description}

        msg = 'Would you like to save the TSI after it is created?'
        save_tsi = True if dlgs.msgbox(msg=msg, yesno=True) else False
            
        tsi = TSIWebPage(
            field_vals=field_vals,
            serial=e2.Serial,
            model=e2.Model,
            _driver=self.driver,
            parent=self,
            uid=e.UID)
        
        if not tsi.is_init: return

        Worker(func=tsi.open_tsi, mw=self.mainwindow, save_tsi=save_tsi) \
            .add_signals(signals=('result', dict(func=self.accept_tsi_result))) \
            .start()

        self.update_statusbar('Creating new TSI in worker thread. GUI free to use.')

    def accept_tsi_result(self, tsi=None):
        # get TSIWebpage obj back from worker thread, save TSI Number back to table
        if tsi is None: return
        
        self.driver = tsi.driver
        tsi_number, uid, view = tsi.tsi_number, tsi.uid, self.view

        # fill tsi number back to table or db
        # Get correct row number by UID > user may have reloaded table or changed tabs

        if not tsi_number is None:
            irow = view.get_irow_uid(uid=uid)

            if not irow is None:
                index = view.create_index_activerow(irow=irow, col_name='TSI No')
                view.model().setData(index=index, val=tsi_number)
            else:
                dbt.Row(dbtable=self.get_dbtable(), keys=dict(UID=uid)) \
                    .update(vals=dict(TSINumber=tsi_number))

        self.update_statusbar(f'New TSI created. TSI Number: {tsi_number}')

    def create_failure_report(self):
        from . import eventfolders as efl

        view = self.view
        row = view.row_from_activerow()
        if row is None: return
        e = row.create_model_from_db()

        # get event folder
        ef = efl.get_eventfolder(minesite=e.MineSite).from_model(e=e, irow=row.i, table_model=view.model())

        # get pics, body text from dialog
        text = dict(
            complaint=e.TSIDetails,
            cause='Uncertain.',
            correction='Component replaced with new.',
            details=e.Description)

        dlg = dlgs.FailureReport(parent=self, p_start=ef.p_event / 'Pictures', text=text)
        if not dlg.exec_(): return

        # create header data from event dict + unit info
        header_data = f.model_dict(e, include_none=True)
        header_data.update(db.get_df_unit().loc[e.Unit])

        # keys = dict(UID=e.UID)
        # header_data = dbt.join_query(tables=(EventLog, UnitID), keys=keys, join_field='Unit')

        # create report obj and save as pdf in event folder
        from .. import reports as rp
        rep = rp.FailureReport(header_data=header_data, pictures=dlg.pics, body=dlg.text, e=e)
        p_rep = rep.create_pdf(p_base=ef.p_event)

        msg = 'Failure report created, open now?'
        if dlgs.msgbox(msg=msg, yesno=True):
            fl.open_folder(p_rep)

class UnitInfo(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        view = self.view
        view.mcols['disabled'] = ('SMR Measure Date', 'Current SMR', 'Warranty Remaining', 'GE Warranty')
        view.col_widths.update({
            'Warranty Remaining': 40,
            'GE Warranty': 40})
        view.formats.update({
            'Current SMR': '{:,.0f}',
            'Engine Serial': '{:.0f}'})

        self.add_button(name='Add New', func=self.show_addrow)
    
    def show_addrow(self):
        dlg = dlgs.AddUnit(parent=self)
        dlg.exec_()

    def remove_row(self):
        # remove selected unit from table and delete from db
        view, e, row = self.view, self.e, self.row
        if row is None: return

        m = dict(Unit=e.Unit, Model=e.Model, MineSite=e.MineSite)

        msg = f'Are you sure you would like to permanently delete the unit:\n\n{f.pretty_dict(m)}'
        if dlgs.msgbox(msg=msg, yesno=True):
            row.update(delete=True)
            view.remove_row(i=row.i)
            self.mainwindow.update_statusbar(msg=f'Unit removed from database: {e.Unit}')

class FCBase(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.add_button(name='Import FCs', func=lambda: fc.import_fc(upload=True))
        self.add_button(name='View FC Folder', func=self.view_fc_folder)
   
    def get_fc_folder(self):
        if not fl.drive_exists():
            return

        e = self.e
        if e is None: return

        p = f.drive / f.config['FilePaths']['Factory Campaigns'] / e.FCNumber

        if not p.exists():
            msg = f'FC folder: \n\n{p} \n\ndoes not exist, create now?'
            if dlgs.msgbox(msg=msg, yesno=True):
                p.mkdir(parents=True)
            else:
                return
        
        return p
    
    def view_fc_folder(self):
        fl.open_folder(p=self.get_fc_folder())
    
    def view_folder(self):
        self.view_fc_folder()

class FCSummary(FCBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.add_button(name='Email New FC', func=self.email_new_fc)
        self.add_button(name='Close FC', func=self.close_fc)

        # map table col to update table in db if not default
        tbl_b = 'FCSummaryMineSite'
        self.db_col_map = {
            'Action Reqd': tbl_b,
            'Parts Avail': tbl_b,
            'Comments': tbl_b,
            'ManualClosed': tbl_b} # bit sketch, not actual header in table, just in db

        self.view.mcols['check_exist'] = tuple(self.db_col_map.keys()) # rows for cols may not exist yet

    class View(TableView):
        def __init__(self, parent):
            super().__init__(parent=parent)

            self.mcols['hide'] = ('MineSite',)
            self.col_widths.update({
                'Subject': 250,
                'Comments': 600,
                'Action Reqd': 60,
                'Type': 40,
                'Part Number': 100,
                'Parts Avail': 40,
                'Total Complete': 60,
                '% Complete': 45})

            self.highlight_vals.update({'m': 'maroon'})
            self.highlight_funcs['Type'] = self.highlight_by_val

            # TODO: add dropdown menu for Type, Action Reqd, Parts Avail
        
        def get_center_cols(self, df):
            # FCSummary needs dynamic center + vertical cols
            # this is called every time table is refreshed - NOTE change to 'update_cols'
            cols = list(df.columns[13:]) if df.shape[1] >= 13 else []
            mcols = self.mcols
            mcols['vertical'] = cols
            mcols['disabled'] = ['FC Number', 'Total Complete', '% Complete'] + cols
            self.col_widths.update({c: 25 for c in cols}) # NOTE not ideal, would like to reimplement sizeHint
            return cols

    def email_new_fc(self):
        # get df of current row
        df = self.view.df_from_activerow().iloc[:, :10]
        style = st.default_style(df=df, outlook=True)
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
    
    def close_fc(self):
        e = self.e

        msg = f'Would you like close FC "{e.FCNumber}" for MineSite "{e.MineSite}"?'
        if not dlgs.msgbox(msg=msg, yesno=True): return

        row = dbt.Row(table_model=self.view.model(), dbtable=self.get_dbtable(header='ManualClosed'), i=self.i)

        row.update(vals=dict(ManualClosed=True))
        self.view.remove_row()

        msg = f'FC: "{e.FCNumber} - {e.Subject}" closed for MineSite: "{e.MineSite}"'
        self.update_statusbar(msg=msg)

class FCDetails(FCBase):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        tbl_b = 'EventLog'
        self.db_col_map = {
            'Pics': tbl_b}

    class View(TableView):
        def __init__(self, parent):
            super().__init__(parent=parent)

            self.highlight_funcs['Pics'] = self.highlight_pics
            self.highlight_funcs['Complete'] = self.highlight_by_val
            self.mcols['disabled'] = ('MineSite', 'Model', 'Unit', 'FC Number', 'Complete', 'Closed', 'Type', 'Subject', 'Pics')
            self.mcols['hide'] = ('UID',)
            self.col_widths.update({
                'Complete': 60,
                'Closed': 60,
                'Type': 60,
                'Subject': 400,
                'Notes': 400})
    
    def view_folder(self):
        view, i, e = self.view, self.i, self.e

        df = view.df_from_activerow()
        unit, uid = df.Unit.values[0], df.UID.values[0]
        minesite = db.get_unit_val(unit, 'MineSite')

        if pd.isnull(uid):
            msg = f'FC not yet linked to an event, cannot view event folder.'
            dlgs.msg_simple(msg=msg, icon='warning')
            return
        
        # create EventLog row/e with UID
        row = dbt.Row(dbtable=dbm.EventLog, keys=dict(UID=uid))
        e2 = row.create_model_from_db()

        efl.get_eventfolder(minesite=minesite).from_model(e=e2, irow=i, table_model=view.model()).show()

class EmailList(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def show_addrow(self):
        # TODO Add email
        dlg = dlgs.AddEmail(parent=self)
        dlg.exec_()
    
    def delete_email(self):
        # TODO delete email
        return

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

            self.mcols['disabled'] = ('Unit', 'ShiftDate', 'StartDate', 'EndDate')
            self.mcols['datetime'] = ('StartDate', 'EndDate')
            self.mcols['dynamic'] = ('Total', 'SMS', 'Suncor')
            self.mcols['sort_filter'] = ('Unit',)
            self.col_widths.update(dict(Comment=600))
            # self.highlight_funcs['Unit'] = self.highlight_alternating
            self.add_highlight_funcs(cols=['Category Assigned', 'Assigned'], func=self.highlight_by_val)
            self.add_highlight_funcs(cols=['StartDate', 'EndDate'], func=self.highlight_ahs_duplicates)
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
            
            # if a value is changed in any of self.mcols['dynamic'], model needs to re-request stylemap from query for that specific col

        def get_style(self, df=None, outlook=False):
            # this supercedes the default tableview get_style
            # used for email > should probably move/merge this with query
            theme = 'light'
            return super().get_style(df=df, outlook=outlook, exclude_cols=['Unit']) \
                .pipe(st.set_column_widths, vals=dict(StartDate=60, EndDate=60, Comment=400)) \
                .pipe(self.parent.query.background_gradient, theme=theme, do=outlook) \
                .apply(st.highlight_alternating, subset=['Unit'], theme=theme, color='navyblue')

        def update_duration(self, index, **kw):
            # Set SMS/Suncor duration if other changes
            model = index.model()
            col_name = model.headerData(i=index.column())

            duration = model.df.iloc[index.row(), model.get_col_idx('Total')]
            val = index.data(role=TableModel.RawDataRole)

            if col_name == 'SMS':
                update_col = model.get_col_idx('Suncor')
            elif col_name == 'Suncor':
                update_col = model.get_col_idx('SMS')

            update_index = index.siblingAtColumn(update_col)
            update_val = duration - val
            model.setData(index=update_index, val=update_val, triggers=False, queue=True)
            model.flush_queue()
        
        def highlight_ahs_duplicates(self, df, val, row, col, role, **kw):
            # if row startdate is between prior row's star/end date, highlight red
            if row == 0 or not role == Qt.BackgroundRole: return
            row_prev = df.loc[row - 1]
            if not df.loc[row, 'Unit'] == row_prev.Unit: return

            m = dict(StartDate=(op.ge, op.lt), EndDate=(op.lt, op.le))
            ops = m[col]
            if ops[0](val, row_prev.StartDate) and ops[1](val, row_prev.EndDate):
                return QColor('red')

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
        df = model.df
        df = df[df.Assigned==0]

        msg = f'Would you like to update [{len(df)}] records in the database?'
        if not dlgs.msgbox(msg=msg, yesno=True):
            return

        cols = ['Total', 'SMS', 'Suncor', 'Category Assigned', 'Comment']
        txn = dbt.DBTransaction(table_model=model) \
            .add_df(df=df, update_cols=cols) \
            .update_all()
        
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
        
        model.set_stylemap(col='Unit')

        if not name_index is None:
            self.view.select_by_nameindex(name_index=name_index)
    
    def assign_suncor(self):
        # func ctrl+shift+Z to auto assign suncor
        # TODO loop selected rows and bulk update
        view = self.view
        model = view.model()

        index = view.create_index_activerow(col_name='Suncor')
        duration = model.df.iloc[index.row(), model.get_col_idx('Total')]
        model.setData(index=index, val=duration, queue=True)
    
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
        
    def email_report(self, period_type=False, p_rep=False, name=None):
        from .refreshtables import AvailReport
        
        if not period_type:
            dlg = AvailReport(parent=self)
            if not dlg.exec_(): return
            d_rng, period_type, name = dlg.d_rng, dlg.period_type, dlg.name

        title = self.get_report_name(period_type, name)
        
        if not p_rep:
            p_rep = self.get_report_path(p_base=self.get_report_base(period_type), name=title)
        
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
        f.set_self(vars())

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
        f.set_self(vars())

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

        f.set_self(vars())
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


# HEADER
class HeaderView(QHeaderView):
    """Custom header, allows vertical header labels"""
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)

        from .startup import get_qt_app
        _font = get_qt_app().font()
        _metrics = QFontMetrics(_font)
        _descent = _metrics.descent()
        _margin = 10

        # create header menu bindings
        self.setDefaultAlignment(Qt.AlignCenter | Qt.Alignment(Qt.TextWordWrap))
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(parent._header_menu)
        # self.setFixedHeight(30) # NOTE maybe not
        self.setMinimumHeight(30)

        f.set_self(vars())

    def paintSection(self, painter, rect, index):
        col = self._get_data(index)

        if col in self.parent.mcols['vertical']:
            painter.rotate(-90)
            painter.setFont(self._font)
            painter.drawText(- rect.height() + self._margin,
                            rect.left() + int((rect.width() + self._descent) / 2), col)
        else:
            super().paintSection(painter, rect, index)

    def sizeHint(self):
        if self.parent.mcols['vertical']:
            return QSize(0, self._max_text_width() + 2 * self._margin)
        else:
            return super().sizeHint()

    def _max_text_width(self):
        # return max text width of vertical cols, used for header height
        return max([self._metrics.width(self._get_data(i))
                    for i in self.model().get_col_idxs(self.parent.mcols['vertical'])])

    def _get_data(self, index):
        return self.model().headerData(index, self.orientation())
