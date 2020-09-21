

from .. import functions as f
from .. import errors as er
from . import delegates, dialogs, gui, refreshtables, tables, update
from .__init__ import *

try:
    # try setting app ID for windows only
    from PyQt5.QtWinExtras import QtWin # noqa
    app_id = f'com.sms.smseventlog' # .{VERSION}' > dont include version, windows thinks its a different app
    print(app_id)
    QtWin.setCurrentProcessExplicitAppUserModelID(app_id)    
except ImportError:
    pass

def decorate_modules():
    # decorate all classes' methods in these modules with @e error handler
    modules = [delegates, dialogs, gui, refreshtables, tables, update]
    for module in modules:
        er.decorate_all_classes(module=module)

def launch():
    er.init_sentry()
    decorate_modules()
    app = get_qt_app()
    w = gui.MainWindow()

    w.show()
    app.processEvents()
    w.after_init()
    return app.exec_()

def get_qt_app():
    app = QApplication.instance()
    
    if app is None:
        # need to set these for proper scaling on windows
        if hasattr(Qt, 'AA_EnableHighDpiScaling'):
            QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        app = QApplication([sys.executable])
        
        app.setWindowIcon(QIcon(str(f.datafolder / 'images/sms_icon.png')))
        app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        app.setStyle('Fusion')

        app.setFont(QFont('Calibri', f.config_platform['font size']))
    
    return app
