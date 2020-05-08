# command line script to import fault, haul, or fix dls folders

import sys
from pathlib import Path
import argparse
from datetime import datetime as dt

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
    "--range",  # name on the CLI - drop the `--` for positional/required parameters
    nargs="*",  # 0 or more values expected => creates a list
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

if __name__ == '__main__':
    def get_units(lower, upper):
        return [f'F{unit}' for unit in range(lower, upper + 1)]
    
    a = CLI.parse_args()
    units, ftype, rng, startdate, batch = a.units, a.ftype, a.range, a.startdate, a.batch
    
    if startdate:
        d = dt.strptime(startdate, '%Y-%m-%d')
    else:
        d = dt(2019,1,1)
    
    if batch:
        lower = 300 + (batch - 1) * 10
        upper = lower + 9
        units = get_units(lower, upper)

    if rng:
        lower = int(rng[0].replace('F', ''))
        upper = int(rng[-1].replace('F', ''))
        units = get_units(lower, upper)
    
    print(f'ftype: {ftype}, units: {units}')
    fl.process_files(ftype=ftype, units=units, d_lower=d)
