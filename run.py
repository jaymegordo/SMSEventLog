import sys
from pathlib import Path

print('run.py starting')

from smseventlog.gui import startup

if __name__ == '__main__':
    sys.exit(startup.launch())
