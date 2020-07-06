from .__init__ import *

# irow, icol = row/column integer locations eg 3, 5
# row, col = row/column index names eg (if no actual index) 3, 'StartDate'

class TableModel(QAbstractTableModel):
    RawDataRole = 64
    NameIndexRole = 65
    DateRole = 66
    RawBackgroundRole = 67
    iIndexRole = 68

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
        self.set_queue()

        color_enabled = False
        color_back = Qt.magenta

        f.set_self(self, vars(), exclude='df')

        if not df is None:
            self.set_df(df=df)

    def set_queue(self):
        # queue to hold updates before flushing to db in bulk
        self.queue = dd(dict)

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
        # return df of background colors to use in style.apply
        # TODO this needs to be rebuilt!!
        func = lambda x: f'background-color: {str(x)};'
        # print(df.shape, df.tail())
        # print(df.columns)
        rows = []
        for row_name in df.index:
            rows.append(tuple(self.data(name_index=(row_name, col_name), role=Qt.BackgroundRole) for col_name in df.columns))

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

    def data(self, index=None, role=RawDataRole, i_index=None, name_index=None):
        # TableView asks the model for data to display, edit, paint etc
        # convert index integer values to index names for df._get_value() > fastest lookup
        # TODO create 'display' dataframe of all string values, 'background df' etc
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

        try:
            val = df._get_value(row, col)
        except KeyError:
            return None
        
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
                try:
                    return func(**dict(df=df, row=row, col=col, irow=irow, icol=icol, val=val, role=role, index=index))
                except:
                    return None
            
            style_vals = self.stylemap.get((row, col), None)
            if style_vals:
                if role == Qt.BackgroundRole:
                    color = style_vals[0]
                elif role == Qt.ForegroundRole:
                    color = style_vals[1]
                return QColor(color.split(' ')[1])

        # return named row/col index for use with df.loc
        elif role == self.NameIndexRole:
            return (row, col)
        
        elif role == self.iIndexRole:
            if irow is None:
                irow, icol = df.index.get_loc(row), df.columns.get_loc(col)
            return (irow, icol)

        return None

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
    
    @e
    def setData(self, index, val, role=Qt.EditRole, triggers=True, queue=False, update_db=True):
        if not index.isValid(): return False

        if role == Qt.EditRole and index.data() != val:
            irow, icol = self.getRowCol(index)
            row, col = index.data(role=self.NameIndexRole)
            df = self.df

            dtype = str(df.dtypes[icol]).lower()

            if dtype in ('float64', 'int64') and not f.isnum(val):
                val = None
            else:
                if dtype == 'object':
                    val = str(val)
                elif dtype == 'float64':
                    val = float(val)
                elif dtype == 'int64':
                    val = int(val)

            # keep original df copy in sync for future filtering
            self._df_orig.loc[row, col] = val
            df.loc[row, col] = val

            # either add items to the queue, or update single val
            if not queue:
                if update_db:
                    self.update_db(index=index, val=val)
            else:
                self.add_queue(vals={col: val}, irow=irow)

            self.dataChanged.emit(index, index)

            # stop other funcs from updating in a loop
            if triggers:
                func = self.parent.col_func_triggers.get(col, None)
                if not func is None:
                    func(index=index)
            
            return True
        
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
        try:
            icol = self.df.columns.get_loc(col)
        except KeyError:
            icol = None

        return icol

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

        e = dbt.Row(table_model=self, dbtable=dbtable, i=index.row())
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
        # insert new row to table view
        # m is dict with view_cols
        
        if i is None:
            i = self.rowCount()

        self.beginInsertRows(QModelIndex(), i, i + num_rows - 1)
        self._df = self.df.pipe(f.append_default_row)

        for col, val in m.items():
            icol = self.get_column_idx(col)
            if not icol is None:
                index = self.createIndex(i, icol)
                self.setData(index=index, val=val, update_db=False)

        self.endInsertRows()

    def append_row(self, data):
        # TODO use this instead of insert
        self.insert_row([data], self.rowCount())

    def removeRows(self, i, num_rows=1):
        # TODO build remove more than one row
        self.beginRemoveRows(QModelIndex(), i, i + num_rows - 1)
        df = self._df
        self._df = df.drop(df.index[i]).reset_index(drop=True)
        self.endRemoveRows()

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

def test_model():
    from . import startup
    from . import tables as tbls
    app = startup.get_qt_app()
    table_widget = tbls.EventLog()
    query = table_widget.query
    df = query.get_df(default=True)
    view = table_widget.view
    model = view.model()
    model.set_df(df)

    return model