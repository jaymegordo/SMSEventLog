import sys
from pathlib import Path
import warnings
warnings.filterwarnings("ignore", "(?s).*MATPLOTLIBDATA.*", category=UserWarning)

print('run.py starting')

from smseventlog.gui import startup

if __name__ == '__main__':
    sys.exit(startup.launch())
