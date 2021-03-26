import os
import sys
import warnings

warnings.filterwarnings("ignore", "(?s).*MATPLOTLIBDATA.*", category=UserWarning)

if __name__ == '__main__':
    os.environ['IS_QT_APP'] = 'True' # set env variable for qt app
    from smseventlog.gui import startup
    sys.exit(startup.launch())
