"""
Script to update activity log time entries
"""
import argparse

from smseventlog.__init__ import dt, getlog, np, pd
from smseventlog.utils import excel as ex


log = getlog(__name__)
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
    help=f'Open excel file: {ex.p}')

cli.add_argument(
    '-l',
    '--like',
    nargs='?',
    type=str,
    const=True,
    default=None,
    help=f'Show matching rows.')

cli.add_argument(
    '-i',
    '--init',
    nargs='?',
    type=str,
    const=True,
    default=None,
    help=f'Add default rows for current day.')

if __name__ == '__main__':
    a = cli.parse_args()
    log.info(a)
    print('\n')

    if a.open:
        import subprocess
        args = ['open', str(ex.p)]
        subprocess.Popen(args)
        exit()

    em = ex.ExcelModel()

    if a.dlt:
        ex.delete_row(n=a.nrows, em=em)
    elif a.show:
        em.display_df()
    elif a.like:
        em.show_like(s=a.like)
    elif a.init:
        ex.add_defaults(em=em)
    else:
        ex.update_time(task=a.task, duration=a.dur, d=a.date, category=a.category)
        print(f'\nWow, {a.dur} hours? That was a great use of your time Jayme! Good work!')