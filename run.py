import sys
from pathlib import Path

# from fbs_runtime.application_context.PyQt5 import ApplicationContext

print('run.py starting')

from smseventlog.gui import startup

# Main control function
if __name__ == '__main__':
    # appctxt = ApplicationContext()
    sys.exit(startup.launch())
