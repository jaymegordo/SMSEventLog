import sentry_sdk
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from .. import functions as f
from . import delegates, dialogs, gui, refreshtables, tables, update
from .__init__ import *

try:
    # try setting app ID for windows only
    from PyQt5.QtWinExtras import QtWin # noqa
    app_id = f'com.sms.smseventlog.{VERSION}'
    print(app_id)
    QtWin.setCurrentProcessExplicitAppUserModelID(app_id)    
except ImportError:
    pass

def decorate_modules():
    # decorate all classes' methods in these modules with @e error handler
    modules = [delegates, dialogs, gui, refreshtables, tables, update]
    for module in modules:
        er.decorate_all_classes(module=module)

def init_sentry():
    sentry_sdk.init(
        dsn="https://66c22032a41b453eac4e0aac4fb03f82@o436320.ingest.sentry.io/5397255",
        integrations=[SqlalchemyIntegration()])

def launch():
    init_sentry()
    decorate_modules()
    app = get_qt_app()
    w = gui.MainWindow()

    w.show()
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
