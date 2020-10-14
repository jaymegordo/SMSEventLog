import sys
import warnings
warnings.filterwarnings("ignore", "(?s).*MATPLOTLIBDATA.*", category=UserWarning)

if __name__ == '__main__':
    from smseventlog.gui import startup
    sys.exit(startup.launch())
