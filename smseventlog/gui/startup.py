from .__init__ import *
from . import gui, tables, dialogs, refreshtables # importing these to wrap errors
from .. import functions as f

def decorate_modules():
    # decorate all classes' methods in these modules with @e error handler
    modules = [gui, tables, dialogs, refreshtables]
    for module in modules:
        er.decorate_all_classes(module=module)

def launch():
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