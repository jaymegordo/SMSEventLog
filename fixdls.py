import sys
from pathlib import Path
import argparse
from datetime import datetime as dt

import smseventlog.folders as fl

CLI=argparse.ArgumentParser()
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
    units = args.units
    rng = args.range
    d_lower = dt(2019,1,1)

    if rng:
      lower = int(rng[0].replace('F', ''))
      upper = int(rng[-1].replace('F', ''))

      for unit in range(lower, upper + 1):
        unit = f'F{unit}'
        fl.fix_dls(unit=unit, d_lower=d_lower)

    elif units:
        for unit in units:
            unit = unit.replace(' ', '')
            fl.fix_dls(unit=unit, d_lower=d_lower)
    else:
        fl.fix_dls_all_units(d_lower=d_lower)
