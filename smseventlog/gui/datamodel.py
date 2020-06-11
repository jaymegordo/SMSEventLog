from .__init__ import *

# irow, icol = row/column integer locations eg 3, 5
# row, col = row/column index names eg (if no actual index) 3, 'StartDate'

class TableModel(QAbstractTableModel):
    RawDataRole = 64
    RawIndexRole = 65
    DateRole = 66
    RawBackgroundRole = 67

    def __init__(self, parent, df=None):
        super().__init__()
        # table model must be created from TableWidget()/TableView() parent
        
        _df = pd.DataFrame()
        _df_orig = pd.DataFrame()
        _df_pre_dyn_filter = None
        _resort = lambda : None # Null resort functon
        _cols = []
        table_widget = parent.parent #sketch
        _stylemap = {}

        color_enabled = False
        color_back = Qt.magenta

        f.set_self(self, vars(), exclude='df')

        if not df is None:
            self.set_df(df=df)

    def set_df(self, df):
        # Set or change pd DataFrame to show
        _df_orig = df.copy()
        _df_pre_dyn_filter = None # Clear dynamic filter
        _cols = list(df.columns)
        parent = self.parent

        # apply style functions
        # TODO this isn't finished yet
        query = self.table_widget.query
        if hasattr(query, 'get_stylemap'):
            self.stylemap = query.get_stylemap(df=df)

        # create tuple of ints from parent's list of disabled table headers
        disabled_cols = tuple(i for i, col in enumerate(_cols) if col in parent.disabled_cols)
        
        # tuple of ints for date cols
        dt_cols = tuple(i for i, val in enumerate(df.dtypes) if val == 'datetime64[ns]' and not df.columns[i] in parent.datetime_cols)

        datetime_cols = tuple(df.columns.get_loc(col) for col in parent.datetime_cols)

        f.set_self(self, vars(), exclude='df')
        self.df = df

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
        self.modelReset.emit()
        self.layoutChanged.emit()

        if self._df.shape[0] > 0:
            self.parent.resizeRowsToContents()

    @property
    def stylemap(self):
        return self._stylemap

    @stylemap.setter
    def stylemap(self, stylemap):
        self._stylemap = stylemap
        
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
        # return df of background colors to use in style.apply
        # TODO this needs to be rebuilt!!
        func = lambda x: f'background-color: {str(x)};'
        # print(df.shape, df.tail())
        # print(df.columns)
        rows = []
        for row_name in df.index:
            rows.append(tuple(self.data(raw_index_names=(row_name, col_name), role=Qt.BackgroundRole) for col_name in df.columns))

        df = pd.DataFrame(data=rows, columns=df.columns, index=df.index)
        # print(df.shape, df.tail())

        # convert QColor back to hex
        for irow in df.index:
            for col in df.columns:
                val = df.loc[irow, col]
                #print(idx)

                if isinstance(val, QColor):
                    val_str = func(val.name())
                else:
                    val_str = func(val)
                df.loc[irow, col] = val_str
        
        return df

    def data(self, index=None, role=RawDataRole, raw_index=None, raw_index_names=None):
        # TableView asks the model for data to display, edit, paint etc
        # convert index integer values to index names for df._get_value() > fastest lookup
        # TODO create 'display' dataframe of all string values, 'background df' etc
        df = self.df
        irow, icol, row, col = None, None, None, None

        if not index is None and index.isValid():
            irow, icol = self.getRowCol(index)
        elif not raw_index is None:
            irow, icol = raw_index[0], raw_index[1]
        elif not raw_index_names is None:
            row, col = raw_index_names[0], raw_index_names[1]
        else:
            return None

        if col is None:
            row, col = df.index[irow], df.columns[icol]

        val = df._get_value(row, col)

        if role == Qt.DisplayRole:
            if not pd.isnull(val):
                fmt = self.parent.formats.get(col, None)
                if not fmt is None:
                    return fmt.format(val)
                else:
                    return str(val)
            else:
                return ''
        
        elif role == Qt.EditRole:
            if not pd.isnull(val):
                return val
            else:
                return ''

        elif role == self.RawDataRole:
            return val
            
        elif role == Qt.TextAlignmentRole:
            # TODO set this based on column dtypes, not value?
            if isinstance(val, int) or isinstance(val, float):
                return Qt.AlignVCenter + Qt.AlignRight

        elif role in (Qt.BackgroundRole, Qt.ForegroundRole):
            # ask table_widget for cell color given df, irow, icol
            func = self.parent.highlight_funcs[col]
            if not func is None:
                return func(**dict(df=df, row=row, col=col, val=val, role=role))
            
            style_vals = self.stylemap.get((row, col), None)
            if style_vals:
                if role == Qt.BackgroundRole:
                    color = style_vals[0]
                elif role == Qt.ForegroundRole:
                    color = style_vals[1]
                return QColor(color.split(' ')[1])

        elif role == self.RawIndexRole:
            return (row, col)

        return None

    def setData(self, index, val, role=Qt.EditRole, triggers=True):
        # TODO Check if text has changed, don't commit
        # TODO queue updates in batch!!
        if index.isValid():
            try:
                if role == Qt.EditRole:
                    irow, icol = self.getRowCol(index)
                    row, col = index.data(role=self.RawIndexRole)
                    df = self.df

                    dtype = str(df.dtypes[icol]).lower()
                    # TODO build a better dict to convert all these.. need to work with datetime delegate
                    # m = {'datetime64[ns]': '')

                    if dtype in ('float64', 'int64') and not f.isnum(val):
                        val = None
                    else:
                        if dtype == 'object':
                            val = str(val)
                        elif dtype == 'float64':
                            val = float(val)
                        elif dtype == 'int64':
                            val = int(val)

                    df.loc[row, col] = val

                    # keep original df copy in sync for future filtering
                    self._df_orig.loc[row, col] = val

                    self.update_db(index=index, val=val)
                    self.dataChanged.emit(index, index)

                    # stop other funcs from updating in a loop
                    if triggers:
                        func = self.parent.col_func_triggers.get(col, None)
                        if not func is None:
                            func(index=index)
                    
                    return True
            except:
                f.send_error(msg=f'Couldn\'t update data in model: {val}')
        
        return False

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

    def get_column_idx(self, col):
        return self.df.columns.get_loc(col)

    def getColIndex(self, header):
        return self.df.columns.get_loc(header)
    
    def getRowCol(self, index):
        return index.row(), index.column()

    def update_db(self, index, val):
        # Update single value from row in database
        # TODO: this could maybe move to TableWidget?
        df = self.df
        header = df.columns[index.column()] # view header

        # model asks parent's table_widget for dbtable to update based on col
        dbtable = self.table_widget.get_dbtable(header=header)
        check_exists = False if not header in self.parent.check_exist_cols else True

        e = el.Row(table_model=self, dbtable=dbtable, i=index.row())
        e.update_single(header=header, val=val, check_exists=check_exists)
    
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
               
    def insertRows(self, m, i=None, num_rows=1):
        if i is None:
            i = self.rowCount()
        
        self.beginInsertRows(QModelIndex(), i, i + num_rows - 1) 
        # TODO need to loop inserting data (m) here
        self.df = self.df.append(m, ignore_index=True)
        self.endInsertRows()

    def append_row(self, data):
        # TODO use this instead of insert
        self.insert_row([data], self.rowCount())

    def removeRows(self, i, num_rows=1):
        # TODO build remove more than one row
        self.beginRemoveRows(QModelIndex(), i, i + num_rows - 1)
        df = self.df
        self.df = df.drop(df.index[i]).reset_index(drop=True)
        self.endInsertRows()

    def rowCount(self, index=QModelIndex()):
        return self.df.shape[0]

    def columnCount(self, index=QModelIndex()):
        return self.df.shape[1]

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

        if not index.column() in self.disabled_cols:
            ans |= Qt.ItemIsEditable
        
        return ans
