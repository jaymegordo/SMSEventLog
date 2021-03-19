import argparse
import re
from pathlib import Path

import openpyxl as xl
from openpyxl.formatting.formatting import ConditionalFormattingList
from openpyxl.formula.translate import Translator
from openpyxl.worksheet.cell_range import CellRange, MultiCellRange
from openpyxl.worksheet.table import Table, TableStyleInfo
from smseventlog.__init__ import *
from copy import copy as cp

log = getlog(__name__)

cli = argparse.ArgumentParser()

cli.add_argument(
    '-t',
    '--task',  
    type=str,
    default='')

cli.add_argument(
    'dur',  
    type=float,
    default=1.0)

cli.add_argument(
    '-d',
    '--date',
    type=str,
    default=dt.now().date().strftime('%Y-%m-%d'))

cli.add_argument(
    '-c',
    '--category',
    type=str,
    default='')

def update_time(task, duration: float=1.0, d: dt=None, category=None):
    # p = Path('/Users/Jayme/OneDrive/Desktop/Activity Record - Jayme Gordon.xlsx')
    p = Path.home() / 'desktop/Activity Record - Jayme Gordon.xlsx'
    wb = xl.load_workbook(p)
    ws = wb['Sheet1']
    tbl = ws.tables['Table1']

    if d is None:
        d = dt.now().date()

    row = ws.max_row + 1

    # add one row to table.. not sure why this was so messy
    tbl.ref = inc_rng(tbl.ref)

    m = {1: d, 3: duration, 4: task, 5: category}
    for col, val in m.items(): 
        ws.cell(row, col).value = val
    
    for col in range(1, 6):
        cell = ws.cell(row - 1, col)
        new_cell = ws.cell(row, col)
        new_cell.alignment = cp(cell.alignment)
        new_cell.number_format = cp(cell.number_format)

    # copy formula down in col B
    c = ws.cell(row - 1, 2)
    ws.cell(row, 2).value = Translator(c.value, origin=c.coordinate) \
        .translate_formula(inc_rng(c.coordinate))

    adjust_cond_formats(ws=ws)

    wb.save(p)
    wb.close()
    log.info(f'{p.name} updated.')

def inc_rng(rng: str, n: int=1):
    """increment or expand cell range by 1 row"""
    expr = r'\d+$'
    rng = str(rng)
    row = int(re.search(expr, rng)[0])
    return re.sub(expr, str(row + n), rng)

def adjust_cond_formats(ws):
    """Extend conditional formatting by one row
    - have to delete then re-add cond formats"""
    orig_format = cp(ws.conditional_formatting)
    ws.conditional_formatting = ConditionalFormattingList() # clear formats

    for cond in orig_format:
        ws.conditional_formatting.add(
            inc_rng(cond.sqref),
            cond.cfRule[0])


if __name__ == '__main__':
    a = cli.parse_args()
    log.info(a)
    update_time(task=a.task, duration=a.dur, d=a.date, category=a.category)

