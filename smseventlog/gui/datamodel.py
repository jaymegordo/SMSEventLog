from .__init__ import *

log = logging.getLogger(__name__)
log.setLevel(logging.WARNING)
# irow, icol = row/column integer locations eg 3, 5
# row, col = row/column index names eg (if no actual index) 3, 'StartDate'

# NOTE calling index.data() defaults to role=DisplayRole, NOT model.data(role=RawDataRole) careful!

global m_align
m_align =  {
    'object': Qt.AlignLeft,
    'float64': Qt.AlignRight,
    'int64': Qt.AlignRight,
    'bool': Qt.AlignCenter,
    'datetime64[ns]': Qt.AlignCenter}

class TableModel(QAbstractTableModel):
    RawDataRole = 64
    NameIndexRole = 65
    DateRole = 66
    RawBackgroundRole = 67
    iIndexRole = 68
    qtIndexRole = 69

    def __init__(self, parent, df=None):
        super().__init__(parent)
        # table model must be created from TableWidget()/TableView() parent
        
        _df = pd.DataFrame()
        _df_orig = pd.DataFrame()
        _df_pre_dyn_filter = None
        _resort = lambda : None # Null resort functon
        _cols = []
        view = parent
        table_widget = view.parent #sketch
        formats = parent.formats
        highlight_funcs = parent.highlight_funcs
        # _stylemap = {}
        current_row = -1
        selection_color = QColor(f.config['color']['bg']['yellowrow'])
        display_color = True
        self.set_queue()
        self.alignments = {}

        color_enabled = False

        f.set_self(vars(), exclude='df')

        if not df is None:
            self.set_df(df=df)

    @classmethod
    def example(cls, name='EventLog'):
        from . import startup
        from . import tables as tbls
        app = startup.get_qt_app()
        table_widget = getattr(tbls, name, tbls.EventLog)()
        query = table_widget.query
        df = query.get_df(default=True)
        view = table_widget.view
        model = view.model()
        model.set_df(df)

        return model
    
    def set_queue(self):
        # queue to hold updates before flushing to db in bulk
        self.queue = dd(dict)

    def set_df(self, df, center_cols=None):
        # Set or change pd DataFrame to show
        _df_orig = df.copy()
        _df_pre_dyn_filter = None # Clear dynamic filter
        self._cols = list(df.columns)
        mcols = dd(list) # dict of col_type: list of ints
        parent = self.parent
        query = self.table_widget.query

        mcols['center'] = self.get_col_idxs(center_cols)
        mcols['disabled'] = self.get_col_idxs(parent.mcols['disabled'])
        mcols['datetime'] = self.get_col_idxs(parent.mcols['datetime'])

        # date cols have to exclude datetime cols
        date_cols = self.get_col_idxs(df.dtypes[df.dtypes=='datetime64[ns]'].index)
        mcols['date'] = [i for i in date_cols if not i in mcols['datetime']]

        self.mcols = mcols
        self.set_date_formats()
        self.set_static_dfs(df=df)

        f.set_self(vars(), exclude='df')
        self.df = df
        # self.set_stylemap()
    
    def set_date_formats(self):
        for i in self.mcols['date']:
            self.formats[self.headerData(i)] = '{:%Y-%m-%d}'

        for i in self.mcols['datetime']:
            self.formats[self.headerData(i)] = '{:%Y-%m-%d     %H:%M}'

    @property
    def df(self):
        return self._df

    @df.setter
    def df(self, dataFrame):
        # print('Setting Dataframe', dataFrame.shape)
        """Setter should only be used internal to DataFrameModel.  Others should use set_df()"""
        self.layoutAboutToBeChanged.emit()
        self.modelAboutToBeReset.emit()
        self._df = dataFrame

        # set so mainwindow can update current rows label
        self.visible_rows = self._df.shape[0]
        self.total_rows = self._df_orig.shape[0]
        self.view.mainwindow.update_rows_label()
        
        self.modelReset.emit()
        self.layoutChanged.emit()

        if self._df.shape[0] > 0:
            self.parent.resizeRowsToContents()
   
    def set_static_dfs(self, df):
        """Set static dict copies of df string value + colors for faster display in table.

        Parameters
        ----------
        df : pd.DataFrame
        """        
        self.m_display = f.df_to_strings(df=df, formats=self.formats).to_dict()
        self.m_color_bg = f.df_to_color(df=df, highlight_funcs=self.highlight_funcs, role=Qt.BackgroundRole).to_dict()
        self.m_color_text = f.df_to_color(df=df, highlight_funcs=self.highlight_funcs, role=Qt.ForegroundRole).to_dict()

        self.set_stylemap(df=df)

    def search(self, search_text: str) -> list:
        """Filter self.m_display dict to values which match search text"""

        if search_text.strip() == '':
            return []
            
        hidden_cols = self.view.mcols['hide']
        expr = re.compile(search_text, re.IGNORECASE)

        # get dict of {col_name: (index_name, ...)}
        m_out = {k: tuple(k2 for k2, v in m2.items() if expr.match(str(v))) for k, m2 in self.m_display.items()}

        # convert dict to list of (row_name, col_name)
        lst_out = [(v2, k) for k, v in m_out.items() for v2 in v]

        return lst_out

    def set_stylemap(self, df=None, col=None):
        """Get colors from applying a stylemap func to df, merge to static dfs"""
        if df is None: df = self.df
        if df.shape[0] == 0: return

        # only avail + FCSummary use this so far
        # m_stylemap is tuple of 2 nested dicts
        m_stylemap = self.query.get_stylemap(df=df, col=col)
        if m_stylemap is None: return

        for col_name in m_stylemap[0].keys():
            self.m_color_bg[col_name].update(m_stylemap[0][col_name])
            self.m_color_text[col_name].update(m_stylemap[1][col_name])

    @property
    def dbtable_default(self):
        return self.table_widget.get_dbtable()

    @pyqtSlot()
    def beginDynamicFilter(self):
        """Effects of using the "filter" function will not become permanent until endDynamicFilter called"""
        if self._df_pre_dyn_filter is None:
            print('Begin new dynamic filter')
            self._df_pre_dyn_filter = self.df.copy()
        else:
            # Already dynamically filtering, so don't override that
            print("SAME DYNAMIC FILTER MODEL")
            pass

    @pyqtSlot()
    def endDynamicFilter(self):
        """Makes permanent the effects of the dynamic filter"""
        print(" * * * RESETING DYNAMIC")
        self._df_pre_dyn_filter = None

    @pyqtSlot()
    def cancelDynamicFilter(self):
        """Cancel the dynamic filter"""
        self.df = self._df_pre_dyn_filter.copy()
        self._df_pre_dyn_filter = None

    def headerData(self, i, orientation=Qt.Horizontal, role=Qt.DisplayRole):
        cols = self._cols

        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if i < len(cols):
                    return cols[i]
                else:
                    return ''
            elif orientation == Qt.Vertical:
                return i

        return None

    def get_background_colors_from_df(self, df):
        # return df of background colors to use in style.apply (df is passed in by default)
        func = lambda x: f'background-color: {str(x)};'

        # call self.data to get current table's background colors as [list of (tuples of QColors)]
        rows = []
        for row_name in df.index:
            rows.append(tuple(self.data(name_index=(row_name, col_name), role=Qt.BackgroundRole) for col_name in df.columns))

        df = pd.DataFrame(data=rows, columns=df.columns, index=df.index)

        # convert QColor back to hex for styler
        for irow in df.index:
            for col in df.columns:
                val = df.loc[irow, col]

                if isinstance(val, QColor):
                    val_str = func(val.name())
                else:
                    val_str = func(val)
                df.loc[irow, col] = val_str
        
        return df

    def data(self, index=None, role=RawDataRole, i_index=None, name_index=None):
        # TableView asks the model for data to display, edit, paint etc
        # convert index integer values to index names for df._get_value() > fastest lookup

        df = self.df
        irow, icol, row, col = None, None, None, None

        if not index is None and index.isValid():
            irow, icol = self.getRowCol(index)
        elif not i_index is None:
            irow, icol = i_index[0], i_index[1]
        elif not name_index is None:
            row, col = name_index[0], name_index[1]
        else:
            return None

        if col is None:
            row, col = df.index[irow], df.columns[icol]
        
        if role == Qt.DisplayRole:
            return str(self.m_display[col][row])

        elif role in (Qt.BackgroundRole, Qt.ForegroundRole):
            # ask table_widget for cell color given df, irow, icol
            if not self.display_color: return None
            
            # check self.m_color_display first
            if role == Qt.BackgroundRole:
                color = self.m_color_bg[col][row]
            elif role == Qt.ForegroundRole:
                color = self.m_color_text[col][row]
            
            if not pd.isnull(color):
                return color
            
            # TODO somehow merge complex highlight funcs
            func = self.parent.highlight_funcs_complex[col]
            if not func is None:
                try:
                    color = func(df=df, row=row, col=col, irow=irow, icol=icol, val=val, role=role, index=index)

                    # if color is None need to keep checking if selected
                    if not color is None:
                        return color
                except:
                    return None
            
            # highlight current selected row manually
            if irow == self.current_row:
                if role == Qt.BackgroundRole:
                    return self.selection_color
                elif role == Qt.ForegroundRole:
                    return QColor('#000000')
            else:
                return None

        elif role == Qt.TextAlignmentRole:
            return self.get_alignment(icol=icol)

        # return named row/col index for use with df.loc
        elif role == self.NameIndexRole:
            return (row, col)
        
        elif role in (self.iIndexRole, self.qtIndexRole):
            if irow is None:
                try:
                    irow, icol = df.index.get_loc(row), df.columns.get_loc(col)
                    if role == self.iIndexRole:
                        return (irow, icol)
                    elif role == self.qtIndexRole:
                        return self.createIndex(irow, icol)
                except KeyError:
                    return None

        try:
            val = df._get_value(row, col)
        except KeyError:
            log.warning(f'Couldn\'t get value for row: {row}, col: {col}, role: {role}')
            return None


        if role == Qt.EditRole:
            return val if not pd.isnull(val) else ''
        elif role == self.RawDataRole:
            return val           

        return None
   
    def setData(self, index, val, role=Qt.EditRole, triggers=True, queue=False, update_db=True):
        if not index.isValid(): return False
        val_prev = index.data(role=Qt.EditRole) # self.RawDataRole doesnt work great with pd.NA
        row, col = index.data(role=self.NameIndexRole)
        irow, icol = self.getRowCol(index)
        df = self.df

        # if val type doesn't match column dtype, try to enforce and convert
        m_type = {'object': str, 'float64': float, 'int64': int, 'bool': bool, 'datetime64[ns]': dt}
        m_conv = m_type.copy() # bool/date need different func to convert
        m_conv.update({'bool': f.str_to_bool, 'datetime64[ns]': f.convert_date})

        dtype = self.get_dtype(icol=icol)

        if not type(val) == m_type[dtype]:
            try:
                val = m_conv[dtype](val)
            except:
                if isinstance(val, str) and val.strip() == '':
                    # set numeric cols to None if given blank string
                    val = None
                else:
                    msg = f'Error: incorrect data type "{type(val)}" for "{val}"'
                    self.table_widget.mainwindow.update_statusbar(msg=msg)
                    log.info(msg)
                    return

        # dont update db if value is same as previous
        if role == Qt.EditRole and val_prev != val:

            # keep original df copy in sync for future filtering
            self._df_orig.loc[row, col] = val
            df.loc[row, col] = val
            # self.m_values[col][row] = val

            # set display vals, NOTE this could go into own func maybe
            if not pd.isnull(val):
                if col in self.formats.keys():
                    display_val = self.formats[col].format(val)
                else:
                    display_val = str(val)
            else:
                display_val = ''

            self.m_display[col][row] = display_val
            
            # set highlight color back to static dict
            func = self.highlight_funcs.get(col, None)
            if not func is None:
                self.m_color_bg[col][row] = func(val=val, role=Qt.BackgroundRole)
                self.m_color_text[col][row] = func(val=val, role=Qt.ForegroundRole)

            # reset stylemap for single col when val in dynamic_cols is changed
            if col in self.parent.mcols['dynamic']:
                self.set_stylemap(col=col)

            # either add items to the queue, or update single val
            if queue:
                self.add_queue(vals={col: val}, irow=irow)
            elif update_db:
                self.update_db(index=index, val=val)               

            self.dataChanged.emit(index, index)

        # trigger column update funcs, stop other funcs from updating in a loop
        if triggers:
            func_list = self.parent.col_func_triggers.get(col, None) # dd of list of funcs to run
            if not func_list is None:
                for func in func_list:
                    func(index=index, val_new=val, val_prev=val_prev)
        
        return True

    def sort(self, icol, order):
        if len(self.df) == 0:
            return

        self.df = self.df.sort_values( 
            self._cols[icol],
            ascending=order==Qt.AscendingOrder)

        # Set sorter to current sort (for future filtering)
        self._resort = partial(self.sort, icol, order)

    def filter(self, icol, needle):
        """Filter DataFrame view.  Case Insenstive.
        Fitlers the DataFrame view to include only rows who's value in col
        contains the needle. EX: a needle of "Ab" will show rows with
        "absolute" and "REABSOLVE"."""

        if self._df_pre_dyn_filter is not None:
            df = self._df_pre_dyn_filter.copy()
        else:
            df = self.df

        col = df.columns[icol]

        # Create lowercase string version of column as series
        s_lower = df[col].astype('str').str.lower()

        needle = str(needle).lower()

        self.df = df[s_lower.str.contains(needle)].copy()

        self._resort()

    def filter_by_items(self, items, icol=None, col=None):
        df = self._df_orig
        if col is None:
            col = df.columns[icol]

        s_col = df[col].astype('str')
        self.df = df[s_col.isin(items)].copy()
        self._resort()

    def filter_by_func(self, icol, func):
        df = self.df
        col = self.df.columns[icol]
        self.df = df[func(df[col])]
        self._resort()

    def reset(self):
        self.df = self._df_orig.copy()
        self._resort = lambda: None
        self._df_pre_dyn_filter = None

    def get_dtype(self, icol):
        return str(self.df.dtypes[icol]).lower()
    
    def get_alignment(self, icol : int) -> int:
        """Get alignment value for specified column.

        Parameters
        ----------
        icol : int
            Column integer

        Returns
        -------
        int
            Alignment value for column
        """        
        saved_align = self.alignments.get(icol, None)

        if not saved_align is None:
            return saved_align
        else:
            dtype = self.get_dtype(icol=icol)
            col_name = self.get_col_name(icol=icol)
            
            # align all cols except 'longtext' VCenter
            alignment = m_align.get(dtype, Qt.AlignLeft)

            if not col_name in self.parent.mcols['longtext']:
                alignment |= Qt.AlignVCenter
            
            self.alignments[icol] = alignment

    def get_col_name(self, icol):
        return self._cols[icol]

    def get_col_idx(self, col):
        try:
            return self._cols.index(col) # cant use df.columns, they may be changed
        except:
            return None
    
    def get_col_idxs(self, cols):
        # return list of column indexs for col names eg [3, 4, 5, 14]
        if cols is None: return []
        return [self.get_col_idx(c) for c in cols if c in self._cols]
    
    def getRowCol(self, index):
        return index.row(), index.column()

    def update_db(self, index, val):
        # Update single value from row in database
        # TODO: this could maybe move to TableWidget?
        df = self.df
        header = df.columns[index.column()] # view header

        # model asks parent's table_widget for dbtable to update based on col
        dbtable = self.table_widget.get_dbtable(header=header)
        check_exists = False if not header in self.parent.mcols['check_exist'] else True

        row = dbt.Row(table_model=self, dbtable=dbtable, i=index.row())
        row.update_single(header=header, val=val, check_exists=check_exists)
    
    def add_queue(self, vals, irow=None):
        # vals is dict of view_col: val
        # add either single val or entire row
        # TODO just using default dbtable for now
        # could have multiple dbtables per row... have to check headers for each? bulk update once per table??

        # if keys aren't in update_vals, need to use irow to get from current df row
        check_key_vals = self.df.iloc[irow].to_dict() if not irow is None else vals

        key_tuple, key_dict = dbt.get_dbtable_key_vals(dbtable=self.dbtable_default, vals=check_key_vals)
        self.queue[key_tuple].update(**key_dict, **vals) # update all vals - existing key, or create new key
    
    def flush_queue(self):
        # bulk uptate all items in queue, could be single row or vals from multiple rows
        # TODO trigger the update with signal?
        
        txn = dbt.DBTransaction(table_model=self) \
            .add_items(update_items=list(self.queue.values())) \
            .update_all()
    
        self.set_queue()

    def create_model(self, i):
        # create dbmodel from table model given row index i
        table_widget = self.table_widget
        e = table_widget.get_dbtable()()
        df = self.df
        view_cols = self._cols
        model_cols = f.convert_list_view_db(title=table_widget.title, cols=view_cols)

        # loop cols, setattr on model
        for col, v in enumerate(model_cols):
            setattr(e, v, df.iloc[i, col])
        
        return e
               
    def insertRows(self, m, i=None, num_rows=1, select=False):
        # insert new row to table view
        # m is dict with view_cols
        
        if i is None:
            i = self.rowCount()

        self.beginInsertRows(QModelIndex(), i, i + num_rows - 1)
        self._df = self.df.pipe(f.append_default_row)

        # NOTE maybe append blank row to each static df instead of resetting all..
        self.set_static_dfs(df=self._df)

        for col, val in m.items():
            icol = self.get_col_idx(col)
            if not icol is None:
                index = self.createIndex(i, icol)
                self.setData(index=index, val=val, update_db=False, triggers=False)

        self.endInsertRows()

        if select:
            self.parent.select_by_index(index=self.createIndex(i, 1))

    def append_row(self, data):
        # TODO use this instead of insert
        self.insert_row([data], self.rowCount())

    def removeRows(self, i, num_rows=1):
        # TODO build remove more than one row
        self.beginRemoveRows(QModelIndex(), i, i + num_rows - 1)
        df = self._df
        self._df = df.drop(df.index[i]).reset_index(drop=True)
        self.set_static_dfs(df=self._df)

        self.endRemoveRows()

    def rowCount(self, index=QModelIndex()):
        return self.df.shape[0]

    def columnCount(self, index=QModelIndex()):
        return self.df.shape[1]

    def row_changed(self, index_current, index_prev):
        # only redraw the table if the row index changes (faster for horizontal switching)
        if not index_current.row() == index_prev.row():
            # view = self.parent
            # view.setUpdatesEnabled(False)
            # self.current_row = index_current.row()
            # for row in (index_current.row(), index_prev.row()):
            #     for col in range(self.columnCount()):
            #         view.childAt(row, col).repaint()
            
            # view.setUpdatesEnabled(True)

            self.layoutAboutToBeChanged.emit()
            self.current_row = index_current.row()
            self.layoutChanged.emit()

    def change_color(self, qt_color, color_enabled):
        self.layoutAboutToBeChanged.emit()
        self.color_enabled = color_enabled
        self.color_back = qt_color
        self.layoutChanged.emit()

    def flags(self, index):
        ans = Qt.ItemIsEnabled | Qt.ItemIsSelectable 
        # Qt.ItemIsEditable ?
        # fl |= Qt.ItemIsDragEnabled
        # fl |= Qt.ItemIsDropEnabled

        if not index.column() in self.mcols['disabled']:
            ans |= Qt.ItemIsEditable
        
        return ans

    def toggle_color(self):
        self.layoutAboutToBeChanged.emit()
        self.display_color = not self.display_color
        self.layoutChanged.emit()

    def get_val_index(self, val, col_name):
        """Get index of value in column"""
        df = self.df
        index = df[df[col_name]==val].index
        if len(index.values) == 1:
            irow = index.values[0] # uid exists in df.UID
        else:
            irow = None # uid doesn't exist

        return irow