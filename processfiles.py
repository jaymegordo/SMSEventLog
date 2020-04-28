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

if __name__ == '__main__':
    args = CLI.parse_args()
    units, ftype = args.units, args.ftype
    rng = args.range
    d_lower = dt(2020,1,1)

    if rng:
        lower = int(rng[0].replace('F', ''))
        upper = int(rng[-1].replace('F', ''))

        units = [f'F{unit}' for unit in range(lower, upper + 1)]
    
    print(f'ftype: {ftype}, units: {units}')
    fl.process_files(ftype=ftype, units=units, d_lower=d_lower)
