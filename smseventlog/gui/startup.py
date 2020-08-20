from .__init__ import *
from . import gui, tables, dialogs, refreshtables # importing these to wrap errors
from .. import functions as f
import sentry_sdk
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk import configure_scope

def decorate_modules():
    # decorate all classes' methods in these modules with @e error handler
    modules = [gui, tables, dialogs, refreshtables]
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
        
        app.setWindowIcon(QIcon(str(f.datafolder / 'images/SMS_Icon.png')))
        app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        app.setStyle('Fusion')

        app.setFont(QFont('Calibri', f.config_platform['font size']))
    
    return app
