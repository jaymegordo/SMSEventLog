import argparse
import re
from copy import copy as cp
from pathlib import Path

import openpyxl as xl
from openpyxl.formatting.formatting import ConditionalFormattingList
from openpyxl.formula.translate import Translator
from openpyxl.worksheet.cell_range import CellRange, MultiCellRange
from openpyxl.worksheet.table import Table, TableStyleInfo
from smseventlog import functions as f
from smseventlog.__init__ import dt, getlog, np, pd

log = getlog(__name__)
p = Path.home() / 'desktop/Activity Record - Jayme Gordon.xlsx'

cli = argparse.ArgumentParser()

cli.add_argument(
    '-t',
    '--task', 
    type=str,
    default='',
    help='Task text.')

cli.add_argument(
    '-d',
    '--dur',  
    type=float,
    default=1.0,
    help='Task duration in hours.')

cli.add_argument(
    '-dt',
    '--date',
    type=str,
    default=dt.now().date().strftime('%Y-%m-%d'))

cli.add_argument(
    '-c',
    '--category',
    type=str,
    default=None)

cli.add_argument(
    '--dlt',
    nargs='?',
    type=bool,
    const=True,
    default=None,
    help='Delete table row(s).')

cli.add_argument(
    '-n',
    '--nrows',
    type=int,
    default=1,
    help='Number of rows to delete.')

cli.add_argument(
    '-s',
    '--show',
    nargs='?',
    type=bool,
    const=True,
    default=None,
    help='Print table to console.')

cli.add_argument(
    '-o',
    '--open',
    nargs='?',
    type=bool,
    const=True,
    default=None,
    help=f'Open excel file: {p}')

class ExcelModel():
    def __init__(self):
        wb = xl.load_workbook(p)
        ws = wb['Sheet1']
        tbl = ws.tables['Table1']
        max_row = ws.max_row
        new_row = ws.max_row + 1
        
        f.set_self(vars())
    
    def get_vars(self):
        return self.p, self.wb, self.ws, self.tbl
    
    def close(self, display=True):
        if display:
            self.display_df()

        self.wb.save(p)
        self.wb.close()
    
    def add_row(self, m: dict, n: int=1):
        """Add row to excel table"""
        ws, tbl, row = self.ws, self.tbl, self.new_row

        tbl.ref = inc_rng(tbl.ref)

        for col, val in m.items(): 
            ws.cell(row, col).value = val

        # NOTE 6 should be max tbl.columns
        for col in range(1, 6):
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
    
    def fill_formula(self, col):
        """Copy cell formula down in col"""
        ws = self.ws
        c = ws.cell(self.max_row, col)
        ws.cell(self.new_row, col).value = Translator(c.value, origin=c.coordinate) \
            .translate_formula(inc_rng(c.coordinate))

    def get_df(self):
        """Return df from excel table
        - NOTE should set last col better
        """
        ws = self.ws

        data = np.array(list(ws.values)[1:])[:, :5]
        cols = next(ws.values)[:5]

        return pd.DataFrame(data=data, columns=cols) \
            .pipe(f.lower_cols) \
            .drop(columns='sum_duration')

    def display_df(self):
        """Display last rows of table"""
        f.terminal_df(self.get_df().tail(10))

    def adjust_cond_formats(self, n: int=1):
        """Extend conditional formatting by one row
        - have to delete then re-add cond formats"""
        ws = self.ws
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

def update_time(task, duration: float=1.0, d: dt=None, category=None):
    """Add row to table with new task data"""
    em = ExcelModel()

    if isinstance(d, str):
        d = dt.strptime(d, '%Y-%m-%d')
    
    if category is None:
        category = get_matching_task(df=em.get_df(), task=task)

    m = {1: d, 3: duration, 4: task, 5: category}
    em.add_row(m=m)
    em.fill_formula(col=2)
    em.adjust_cond_formats()
    em.close()

def delete_row(n: int=1):
    em = ExcelModel()
    em.delete_row(n=n)
    em.close()

def inc_rng(rng: str, n: int=1):
    """increment or expand cell range by 1 row"""
    expr = r'\d+$'
    rng = str(rng)
    row = int(re.search(expr, rng)[0])
    return re.sub(expr, str(row + n), rng)


if __name__ == '__main__':
    a = cli.parse_args()
    log.info(a)
    print('\n')

    if a.dlt:
        delete_row(n=a.nrows)
    elif a.show:
        em = ExcelModel()
        em.display_df()
    elif a.open:
        import subprocess
        args = ['open', str(p)]
        subprocess.Popen(args)
    else:
        update_time(task=a.task, duration=a.dur, d=a.date, category=a.category)
        print(f'\nWow, {a.dur} hours? That was a great use of your time Jayme! Good work!')

