from .. import functions as f
from .. import errors as er
from . import delegates, dialogs, gui, refreshtables, tables, update
from .__init__ import *

log = getlog(__name__)

try:
    # try setting app ID for windows only
    from PyQt5.QtWinExtras import QtWin # noqa
    app_id = f'com.sms.smseventlog' # .{VERSION}' > dont include version, windows thinks its a different app
    QtWin.setCurrentProcessExplicitAppUserModelID(app_id)    
except ImportError:
    pass

def decorate_modules():
    # decorate all classes' methods in these modules with @e error handler
    modules = [delegates, dialogs, gui, refreshtables, tables, update]
    for module in modules:
        er.decorate_all_classes(module=module)

@er.errlog('Error in main process.')
def launch():
    log.info(f'\n\n\n{dt.now():%Y-%m-%d %H:%M} | init | {VERSION}')

    from PyQt5.QtGui import QScreen # just used for default

    er.init_sentry()
    decorate_modules()
    app = get_qt_app()

    s = QSettings('sms', 'smseventlog', app)

    pixmap = QPixmap(str(f.resources / 'images/sms_icon.png'))
    splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
    splash.showMessage(f'SMS Event Log\nVersion {VERSION}', color=Qt.white)

    # move splash screen, this is pretty janky
    try:
        last_center = s.value('screen', defaultValue=app.screens()[0].geometry().center())
        splash_rect = splash.frameGeometry()
        splash_rect.moveCenter(last_center)
        splash.move(splash_rect.topLeft())
    except:
        log.warning('Couldn\'t move splash screen.')

    splash.show()
    app.processEvents()

    w = gui.MainWindow()
    w.setUpdatesEnabled(False)
    w.show()
    w.setUpdatesEnabled(True)
    app.processEvents()

    w.after_init()
    splash.finish(w)

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
        
        app.setWindowIcon(QIcon(str(f.resources / 'images/sms_icon.png')))
        app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        app.setStyle('Fusion')

        app.setFont(QFont('Calibri', f.config_platform['font size']))
    
    return app
