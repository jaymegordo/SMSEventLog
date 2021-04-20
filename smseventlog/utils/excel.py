import re
from copy import copy as cp
from pathlib import Path

import openpyxl as xl
from datascroller import scroll
from openpyxl.formatting.formatting import ConditionalFormattingList
from openpyxl.formula.translate import Translator
from openpyxl.worksheet.cell_range import CellRange, MultiCellRange
from openpyxl.worksheet.table import Table, TableStyleInfo

from .__init__ import *

log = getlog(__name__)
p = Path.home() / 'desktop/Activity Record - Jayme Gordon.xlsx'


class ExcelModel():
    def __init__(self):
        wb = xl.load_workbook(p)
        ws = wb['ActLog'] # default table
        tbl = ws.tables['Table1']
        max_row = ws.max_row
        new_row = ws.max_row + 1

        m_formula_cols = dict(actlog=2)
        
        f.set_self(vars())
    
    def get_vars(self):
        return self.p, self.wb, self.ws, self.tbl
    
    def get_tbl(self, ws):
        """Return first table of worksheet"""
        return ws.tables[list(ws.tables)[0]]
    
    def close(self, display=True):
        if display:
            self.display_df()

        self.wb.save(p)
        self.wb.close()
    
    def add_row(self, m: dict, name: str='ActLog'):
        """Add row(s) to excel table
        
        Parameters
        ----------
        m : dict | list
        """
        ws = self.wb[name]
        tbl = self.get_tbl(ws=ws)
        cols = f.lower_cols(tbl.column_names)
        row = ws.max_row

        # convert dict m to list
        lst = m if isinstance(m, list) else [m]
        n = len(lst)

        # adjust table range and cond formats
        tbl.ref = inc_rng(tbl.ref, n=n)
        max_col = len(tbl.column_names)
        self.adjust_cond_formats(n=n, name=name)
        
        # fill formula cols down
        formula_col = self.m_formula_cols.get(name.lower(), None)
        if not formula_col is None:
            self.fill_formula(col=formula_col, n=n)

        for m in lst:
            row += 1

            for col_name, val in m.items():
                col = cols.index(col_name) + 1 # get col int from colname
                ws.cell(row, col).value = val

            for col in range(max_col):
                col += 1
                cell = ws.cell(row - 1, col)
                new_cell = ws.cell(row, col)

                new_cell.alignment = cp(cell.alignment)
                new_cell.number_format = cp(cell.number_format)
    
    def delete_row(self, n: int=1):
        ws, tbl, row = self.ws, self.tbl, self.max_row

        for _ in range(n):
            ws.delete_rows(idx=ws.max_row)
        
        tbl.ref = inc_rng(tbl.ref, n=-1 * n)
        self.adjust_cond_formats(n=-1 * n)
    
    def fill_formula(self, col, n: int=1, name: str='ActLog'):
        """Copy cell formula down in col"""
        ws = self.wb[name]
        # NOTE ws max row kinda messy, checks max row with table/formats, NOT values
        start_row = self.max_row

        for i in range(n):
            c = ws.cell(start_row + i, col)
            ws.cell(start_row + i + 1, col).value = Translator(c.value, origin=c.coordinate) \
                .translate_formula(inc_rng(c.coordinate))

    def get_df(self, name='ActLog'):
        """Return df from excel table"""
        ws = self.wb[name]
        tbl = self.get_tbl(ws=ws)
        max_col = len(tbl.column_names)

        data = np.array(list(ws.values)[1:])[:, :max_col]
        cols = next(ws.values)[:max_col]

        drop_cols = dict(actlog=['sum_duration']) \
            .get(name.lower(), None)

        df = pd.DataFrame(data=data, columns=cols) \
            .pipe(f.lower_cols)
        
        if not drop_cols is None:
            df = df.drop(columns=drop_cols)

        if name == 'ActLog':
            # add sum duration to first row per date
            df_sum = df[['date']].drop_duplicates('date', keep='first') \
                .reset_index() \
                .merge(right=df.groupby('date', as_index=False).duration.sum()) \
                .set_index('index')[['duration']] \
                .rename(columns=dict(duration='sum'))

            cols = ['date', 'sum', 'duration', 'task', 'task_type']
            df = df.merge(right=df_sum, how='left', left_index=True, right_index=True) \
                [cols] \
                # .assign(sum_dur=lambda x: x.sum_dur.astype(str).replace(dict(nan='')))

        return df
    
    def show_like(self, s):
        """Show last n items containing search string in task"""
        df = self.get_df()
        df = df[df.task.str.contains(s, case=False, na=False)]
        scroll(df)

    def display_df(self, n: int=10, df: pd.DataFrame=None):
        """Display last n rows of table"""
        if df is None:
            df = self.get_df()

        df = df.tail(n)
        f.terminal_df(df)

    def adjust_cond_formats(self, n: int=1, name: str='ActLog'):
        """Extend conditional formatting by one row
        - have to delete then re-add cond formats"""
        ws = self.wb[name]
        orig_format = cp(ws.conditional_formatting)
        ws.conditional_formatting = ConditionalFormattingList() # clear formats

        for cond in orig_format:
            ws.conditional_formatting.add(
                inc_rng(cond.sqref, n=n),
                cond.cfRule[0])

def get_matching_task(df, task):
    """Return category if task exists already"""
    df = df[df.task.str.lower() == task]

    try:
        return df.iloc[0, df.columns.get_loc('task_type')].title()
    except:
        return ''

def add_defaults(d: dt=None, em=None):
    """Add default rows for current date"""
    if em is None:
        em = ExcelModel()
    
    if d is None:
        d = dt.now()
    
    day = d.strftime('%a')

    df = em.get_df(name='Default') \
        .pipe(lambda df: df[df.day==day]) \
        .drop(columns='day') \
        .assign(
            duration=lambda x: x.duration.astype(float),
            date=dt.now().date())

    lst = list(df.to_dict(orient='index').values())
    em.add_row(m=lst)
    em.close()

def update_time(task, duration: float=1.0, d: dt=None, category=None, em=None):
    """Add row to table with new task data"""
    if em is None:
        em = ExcelModel()

    if isinstance(d, str):
        d = dt.strptime(d, '%Y-%m-%d')
    
    if category is None:
        category = get_matching_task(df=em.get_df(), task=task)

    m = dict(
        date=d,
        duration=duration,
        task=f'{task[0].upper()}{task[1:]}',
        task_type=category.title())

    em.add_row(m=m, name='ActLog')
    em.close()

def delete_row(n: int=1, em=None):
    if em is None:
        em = ExcelModel()

    em.delete_row(n=n)
    em.close()

def inc_rng(rng: str, n: int=1):
    """increment or expand cell range by 1 row"""
    expr = r'\d+$'
    rng = str(rng)
    row = int(re.search(expr, rng)[0])
    return re.sub(expr, str(row + n), rng)
