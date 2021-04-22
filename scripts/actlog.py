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
    nargs='?',
    const=dt.now().date().strftime('%Y-%m-%d'),
    default=None)

cli.add_argument(
    '-c',
    '--category',
    type=str,
    default=None)

cli.add_argument(
    '--dlt',
    nargs='?',
    type=int,
    const=1,
    default=None,
    help='Delete table row(s).')

cli.add_argument(
    '-n',
    '--nrows',
    nargs='?',
    type=int,
    default=None,
    const=10,
    help='Number of rows to delete.')

cli.add_argument(
    '-s',
    '--show',
    nargs='?',
    type=int,
    const=10,
    default=None,
    help='Print table to console.')

cli.add_argument(
    '--sum',
    nargs='?',
    type=int,
    const=20,
    default=None,
    help='Show summary duration of last n dates.')

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
    # log.info(a)
    print('\n')

    if a.open:
        import subprocess
        args = ['open', str(ex.p)]
        subprocess.Popen(args)
        exit()

    em = ex.ExcelModel()

    if a.dlt:
        ex.delete_row(n=a.dlt, em=em)
    elif a.show:
        em.display_df(n=a.show, d_lower=a.date)
    elif a.like:
        em.show_like(s=a.like)
    elif a.init:
        # init defaults for ALL missing days
        ex.add_defaults(em=em)
    elif a.sum:
        em.show_df_sum(n=a.sum)
    else:
        ex.update_time(task=a.task, duration=a.dur, d=a.date, category=a.category, n=a.nrows)
        print(f'\nWow, {a.dur} hours? That was a great use of your time Jayme! Good work!')