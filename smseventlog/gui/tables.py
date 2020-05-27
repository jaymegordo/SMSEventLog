import pypika as pk

from .. import factorycampaign as fc
from . import gui as ui
from .datamodel import TableModel
from .__init__ import *
from .delegates import AlignDelegate, DateDelegate, DateTimeDelegate, CellDelegate, ComboDelegate
from . import dialogs as dlgs
from .. import emails as em
from .. import queries as qr
from .. import reports as rp

log = logging.getLogger(__name__)

class TableView(QTableView):
    dataFrameChanged = pyqtSignal()
    cellClicked = pyqtSignal(int, int)

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.activated.connect(self.double_click_enter)

        disabled_cols, hide_cols, check_exist_cols, datetime_cols = (), (), (), ()
        col_widths = {'Title': 150, 'Part Number': 150}
        highlight_funcs, highlight_vals = dd(type(None)), {} # NOTE use all lowercase!
        colors = f.config['color']
        
        # set up initial empty model
        self.parent = parent
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
        self.setStyleSheet(' \
            QTableView::item:selected:active {color: #000000;background-color: #ffff64;} \
            QTableView::item:selected:hover {color: #000000;background-color: #cccc4e;}') \
            # QTableView::item {border: 0px; padding: 2px;}')
        
        f.set_self(self, vars())
        self.set_default_headers()
        self.setVisible(True)

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

    def highlight_alternating(self, df, row_ix, col_ix, role, **kw):
        # use count of unique values mod 2 to highlight alternating groups of values
        # TODO only works if column is sorted by unit
        alt_row_num = len(df.iloc[:row_ix + 1, col_ix].unique()) % 2

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

    def resizeRowsToContents(self):
        sender = self.sender()
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

    def display_data(self, df):
        self.rows_initialized = False 
        self.model().set_df(df=df)
            
        self.hide_columns()
        self.set_date_delegates()
        self.resizeColumnsToContents()

        cols = ['Passover', 'Unit', 'Status', 'Wrnty', 'Work Order', 'Seg', 'Customer WO', 'Customer PO', 'Serial', 'Side']
        self.center_columns(cols=cols)
        self.set_column_widths()

        self.rows_initialized = True
        self.resizeRowsToContents()

    def set_date_delegates(self):
        model = self.model()
        date_delegate = DateDelegate(self)

        for i in model.dt_cols:
            self.setItemDelegateForColumn(i, date_delegate)

        # if the parent table_widget has specified datetime cols
        if self.datetime_cols:
            datetime_delegate = DateTimeDelegate(self)
            for i in model.datetime_cols:
                self.setItemDelegateForColumn(i, datetime_delegate)

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
        try:
            model = self.model()
            menu = FilterMenu(self)
            col_ix = self.header.logicalIndexAt(pos)

            if col_ix == -1: return # out of bounds

            # Filter Menu Action
            menu.addAction(DynamicFilterMenuAction(self, menu, col_ix))
            menu.addAction(FilterListMenuWidget(self, menu, col_ix))
            menu.addAction(self._icon('DialogResetButton'),
                            'Clear Filter',
                            model.reset)

            # Sort Ascending/Decending Menu Action
            menu.addAction(self._icon('TitleBarShadeButton'),
                            'Sort Ascending',
                        partial(model.sort, col_ix=col_ix, order=Qt.AscendingOrder))
            menu.addAction(self._icon('TitleBarUnshadeButton'),
                            'Sort Descending',
                        partial(model.sort, col_ix=col_ix, order=Qt.DescendingOrder))
            menu.addSeparator()

            # Hide
            menu.addAction(f'Hide Column: {model.headerData(col_ix, Qt.Horizontal)}', partial(self.hideColumn, col_ix))

            # Show column to left and right
            for i in (-1, 1):
                col = col_ix + i
                if self.isColumnHidden(col):
                    menu.addAction(f'Unhide Column: {model.headerData(col, Qt.Horizontal)}',
                                    partial(self.showColumn, col))


            menu.exec_(self.mapToGlobal(pos))
        except:
            f.send_error(msg='Couldnt show header menu')

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
        query = getattr(qr, name, qr.QueryBase)()
        dbtable = query.update_table
        db_col_map = {}

        view = TableView(parent=self)

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
        try:
            dlg = dlgs.AddEvent(parent=self)
            # ui.disable_window_animations_mac(dlg)
            dlg.exec_()
        except:
            msg = 'couldn\'t show AddRow'
            f.send_error(msg=msg)
            log.error(msg)

    def show_component(self):
        try:
            dlg = dlgs.ComponentCO(parent=self)
            dlg.exec_()
        except:
            msg = 'couldn\'t show ComponentCO'
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

class EventLog(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        view = self.view
        view.disabled_cols = ('Title',) # TODO: remove thise
        view.hide_cols = ('UID',)
        view.col_widths.update(dict(Passover=50, Description=800, Status=100))
        
class WorkOrders(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        view = self.view
        view.hide_cols = ('UID',)       
        view.col_widths.update({
            'Work Order': 90,
            'Customer WO': 80,
            'Customer PO': 80,
            'Comp CO': 50,
            'Comments': 400})
        
        view.highlight_funcs['Status'] = view.highlight_by_val
        view.highlight_vals.update({
            'closed': 'goodgreen',
            'open': 'bad'})

class ComponentCO(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        view = self.view
        view.disabled_cols = ('MineSite', 'Model', 'Unit', 'Component', 'Side')
        view.hide_cols = ('UID',)
        view.col_widths.update(dict(Notes=400))
        view.highlight_funcs['Unit'] = view.highlight_alternating
    
class TSI(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        view = self.view
        view.disabled_cols = ('WO',)
        view.hide_cols = ('UID',)
        view.col_widths.update(dict(Details=400))

        view.highlight_funcs['Status'] = view.highlight_by_val
        view.highlight_vals.update({
            'closed': 'goodgreen',
            'open': 'bad'})

class UnitInfo(TableWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        view = self.view
        view.disabled_cols = ('SMR Measure Date', 'Current SMR', 'Warranty Remaining', 'GE Warranty')
        view.col_widths.update({
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
        view = self.view
        view.disabled_cols = ('Unit', 'ShiftDate', 'StartDate', 'EndDate')
        view.datetime_cols = ('StartDate', 'EndDate')
        view.col_widths.update(dict(Comment=600))
        view.highlight_funcs['Unit'] = view.highlight_alternating
        view.add_highlight_funcs(cols=['CategoryAssigned', 'Assigned'], func=view.highlight_by_val)

        # create cell dropdown for CategoryAssigned
        # TODO move this to an after_init, first time tab selected
        p = f.datafolder / 'csv/avail_assigned.csv'
        df = pd.read_csv(p)
        combo_delegate = ComboDelegate(parent=view, items=f.clean_series(s=df.CategoryAssigned))
        model = view.model()
        c = model.get_column_idx(col='CategoryAssigned')
        view.setItemDelegateForColumn(c, combo_delegate)

        view.highlight_vals.update({
            's1 service': 'lightyellow',
            's4 service': 'lightblue',
            's5 service': 'lightgreen',
            '0': 'lightyellow'})

        self.add_action(name='Filter Assigned', func=self.filter_assigned, shortcut='Ctrl+Shift+A', btn=True)
        self.add_action(name='Assign Suncor', func=self.assign_suncor, shortcut='Ctrl+Shift+Z')
        self.add_action(name='Email Assignments', func=self.email_assignments, shortcut='Ctrl+Shift+E', btn=True)

        # TODO func auto set SMS/Suncor duration if other changes?
    
    def email_assignments(self):
        model = self.view.model()
        df = model.df
        df = df[df.Assigned==0].iloc[:, :-1]
        style = rp.set_style(df=df)
        style.apply(model.get_background_colors_from_df, axis=None)
        
        s = []
        s.append(dict(
            selector='table',
            props=[('border', '1px solid black')]))
        s.append(dict(
            selector='tr:nth-child(even)',
            props=[('background', 'red')])) #'#E4E4E4'
        style.table_styles.extend(s)

        # Date formats
        # cell borders

        s = df.ShiftDate
        fmt = '%Y-%m-%d'
        maxdate, mindate = s.max(), s.min()
        if not maxdate == mindate:
            dates = '{} - {}'.format(mindate.strftime(fmt), maxdate.strftime(fmt))
        else:
            dates = maxdate.strftime(fmt)

        title = f'Downtime Assignment | {dates}'

        body = f'Good Morning,<br><br>See below for current downtime assignments. Please correct and respond with any updates as necessary.<br><br>{style.hide_index().render()}'

        p = f.topfolder.parent / 'avail.html'
        with open(str(p), 'w+') as file:
            file.write(style.render())

        # get email list from csv
        p = f.datafolder / 'csv/avail_email.csv'
        df2 = pd.read_csv(p)
        lst = list(df2[df2.Daily==1].Email)

        # show new email
        msg = em.Message(subject=title, body=body, to_recip=lst)
        
    def update_unassigned(self):
        # TODO save assigned=False back to db
        # get dataframe, filter to unassigned
        # bulk update (need to build this)
        return
    
    def filter_assigned(self):
        model = self.view.model()
        
        if not hasattr(self, 'filter_state') or not self.filter_state:
            model.filter_by_items(col_name='Assigned', include=[str(0)])
            self.filter_state = True
        else:
            model.reset()
            self.filter_state = False
    
    def assign_suncor(self):
        # TODO func ctrl+shift+Z to auto assign suncor
        # loop selected rows
        return

class FilterMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent=parent)


class DynamicFilterLineEdit(QLineEdit):
    # Filter textbox for a DataFrameTable

    def __init__(self, *args, **kwargs):
        _always_dynamic = kwargs.pop('always_dynamic', False)
        super().__init__(*args, **kwargs)

        col_to_filter, _orig_df, _host = None, None, None
        f.set_self(self, vars())

    def bind_dataframewidget(self, host, col_ix):
        # Bind tihs DynamicFilterLineEdit to a DataFrameTable's column

        self.host = host
        self.col_to_filter = col_ix
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
        col_ix = self.col_to_filter

        self.host.model().filter(col_ix, text)

class DynamicFilterMenuAction(QWidgetAction):
    """Filter textbox in column-header right-click menu"""
    def __init__(self, parent, menu, col_ix):
        super().__init__(parent)

        parent_menu = menu

        # Build Widgets
        widget = QWidget()
        layout = QHBoxLayout()
        label = QLabel('Filter')
        text_box = DynamicFilterLineEdit()
        text_box.bind_dataframewidget(self.parent(), col_ix)
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
    def __init__(self, parent, menu, col_ix):
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

        df = model._orig_df
        col = df.columns[self.col_ix]
        
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
        include = []
        for i in range(count):
            i = lst_widget.item(i)
            if i is self._action_select_all: continue
            if i.checkState() == Qt.Checked:
                include.append(str(i.text()))

        parent = self.parent
        parent.blockSignals(True)
        parent.model().filter_by_items(include, col_ix=self.col_ix)
        parent.blockSignals(False)
        parent._enable_widgeted_cells()
