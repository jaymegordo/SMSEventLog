from .__init__ import *

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

        color_enabled = False
        color_back = Qt.magenta

        f.set_self(self, vars(), exclude='df')

        # self.layoutChanged.connect(lambda: print('layoutChanged!'))
        # self.layoutChanged.connect(parent.resizeRowsToContents)

        if not df is None:
            self.set_df(df=df)

    def set_df(self, df):
        # Set or change pd DataFrame to show
        _df_orig = df.copy()
        _df_pre_dyn_filter = None # Clear dynamic filter
        _cols = list(df.columns)
        parent = self.parent

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
            
    @pyqtSlot()
    def beginDynamicFilter(self):
        """Effects of using the "filter" function will not become permanent until endDynamicFilter called"""
        if self._df_pre_dyn_filter is None:
            print("NEW DYNAMIC FILTER MODEL")
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
        func = lambda x: f'background: {str(x)};'
        # print(df.shape, df.tail())
        # print(df.columns)
        rows = []
        for row_name in df.index:
            rows.append(tuple(self.data(raw_index_names=(row_name, col_name), role=Qt.BackgroundRole) for col_name in df.columns))

        df = pd.DataFrame(data=rows, columns=df.columns, index=df.index)
        # print(df.shape, df.tail())

        # convert QColor back to hex
        for row_ix in df.index:
            for col in df.columns:
                val = df.loc[row_ix, col]
                #print(idx)

                if isinstance(val, QColor):
                    val_str = func(val.name())
                else:
                    val_str = func(val)
                df.loc[row_ix, col] = val_str
        
        return df

    def data(self, index=None, role=Qt.DisplayRole, raw_index=None, raw_index_names=None):
        # TableView asks the model for data to display, edit, paint etc
        # TODO create 'display' dataframe of all string values, 'background df' etc
        df = self.df
        row, col, row_name, col_name = None, None, None, None

        if not index is None and index.isValid():
            row, col = self.getRowCol(index)
        elif not raw_index is None:
            row, col = raw_index[0], raw_index[1]
        elif not raw_index_names is None:
            row_name, col_name = raw_index_names[0], raw_index_names[1]
        else:
            return None

        if col_name is None:
            col_name = df.columns[col]

        if not row is None:
            try:
                val = df.iloc[row, col]
            except IndexError:
                print(f'index error: {row, col}')
                return
        elif not row_name is None:
            val = df.loc[row_name, col_name]

        # TODO find way to speed this up as much as possible
        if role == Qt.DisplayRole:
            if not pd.isnull(val):
                fmt = self.parent.formats.get(col_name, None)
                if not fmt is None:
                    return fmt.format(val)
                else:
                    return str(val)
            else:
                return ''
                
        elif role in (TableModel.RawDataRole, Qt.EditRole):
            # if col in self.dt_cols or col in self.datetime_cols:
            return val
            
        elif role == Qt.TextAlignmentRole:
            if isinstance(val, int) or isinstance(val, float):
                return Qt.AlignVCenter + Qt.AlignRight

        elif role in (Qt.BackgroundRole, Qt.ForegroundRole):
            # ask table_widget for cell color given df, row, col

            if row is None:
                row = df.index.get_loc(row_name)
            if col is None:
                col = df.columns.get_loc(col_name)

            func = self.parent.highlight_funcs[col_name]
            if not func is None:
                return func(**dict(df=df, row_ix=row, col_ix=col, val=val, role=role))

        elif role == TableModel.RawIndexRole:
            r = self.df.index[row]
            c = self.df.columns[col]
            return (r, c)

        return None

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

    def setData(self, index, val, role=Qt.EditRole, triggers=True):
        # TODO Check if text has changed, don't commit
        # TODO queue updates in batch!!
        if index.isValid():
            try:
                if role == Qt.EditRole:
                    row, col = self.getRowCol(index)
                    df = self.df

                    dtype = str(df.dtypes[col]).lower()
                    # TODO build a better dict to convert all these.. need to work with datetime delegate
                    # m = {'datetime64[ns]': '')

                    if dtype == 'object':
                        val = str(val)
                    elif dtype == 'float64':
                        val = float(val)
                    elif dtype == 'int64':
                        val = int(val)

                    df.iloc[row, col] = val

                    # keep original df copy in sync for future filtering
                    row_index_name = df.iloc[row].name
                    self._df_orig.loc[row_index_name, df.columns[col]] = val

                    self.update_db(index=index, val=val)
                    self.dataChanged.emit(index, index)

                    # stop other funcs from updating in a loop
                    if triggers:
                        func = self.parent.col_func_triggers.get(self.headerData(col), None)
                        if not func is None:
                            func(index=index)
                    
                    return True
            except:
                f.send_error(msg=f'Couldn\'t update data in model: {val}')
        
        return False


    def sort(self, col_ix, order):
        if len(self.df) == 0:
            return

        self.df = self.df.sort_values( 
            self._cols[col_ix],
            ascending=order==Qt.AscendingOrder)

        # Set sorter to current sort (for future filtering)
        self._resort = partial(self.sort, col_ix, order)

    def filter(self, col_ix, needle):
        """Filter DataFrame view.  Case Insenstive.
        Fitlers the DataFrame view to include only rows who's value in col
        contains the needle. EX: a needle of "Ab" will show rows with
        "absolute" and "REABSOLVE"."""

        if self._df_pre_dyn_filter is not None:
            df = self._df_pre_dyn_filter.copy()
        else:
            df = self.df

        col = df.columns[col_ix]

        # Create lowercase string version of column as series
        s_lower = df[col].astype('str').str.lower()

        needle = str(needle).lower()

        self.df = df[s_lower.str.contains(needle)]

        self._resort()

    def filter_by_items(self, include, col_ix=None, col_name=None):
        df = self._df_orig
        if col_ix is None:
            col_ix = self.get_column_idx(col=col_name)
            
        col = self.df.columns[col_ix]
        s_col = df[col].astype('str')
        self.df = df[s_col.isin(include)]
        self._resort()

    def filter_by_func(self, col_ix, func):
        df = self.df
        col = self.df.columns[col_ix]
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
    
