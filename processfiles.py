# command line script to import fault, haul, or fix dls folders

import sys
from pathlib import Path
import argparse
from datetime import datetime as dt, timedelta as delta

import smseventlog.folders as fl

CLI=argparse.ArgumentParser()
CLI.add_argument(
    '--ftype',  
    type=str,
    default=None)

CLI.add_argument(
    "--units",  # name on the CLI - drop the `--` for positional/required parameters
    nargs="*",  # 0 or more values expected => creates a list
    type=str,
    default=[])

CLI.add_argument(
    "--range",  
    nargs="*",  
    type=str,
    default=[])

CLI.add_argument( # process units in 5 batches of 10
    '--batch',  
    type=int,
    default=None)

CLI.add_argument(
    '--startdate',  
    type=str,
    default=None)

CLI.add_argument(
    '--all_units',
    type=str,
    default=False
)

if __name__ == '__main__':
    def get_units(lower, upper):
        return [f'F{unit}' for unit in range(lower, upper + 1)]
    
    a = CLI.parse_args()
    units, ftype, rng, startdate, batch, all_units = a.units, a.ftype, a.range, a.startdate, a.batch, a.all_units
           
    if startdate:
        d = dt.strptime(startdate, '%Y-%m-%d')
    else:
        d = dt.now() + delta(days=-31)

    if all_units:
        print('fix dls all units')
        fl.fix_dls_all_units(d_lower=d)
    else:
        print(f'ftype: {ftype}, units: {units}')
        fl.process_files(ftype=ftype, units=units, d_lower=d)

    print('** finished processfiles **')