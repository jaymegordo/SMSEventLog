from PyQt5.QtCore import QSettings, QSize
from PyQt5.QtWidgets import QApplication, QMainWindow

# global functions to handle getting mainwindow/settings in dev or production independent of gui
# NOTE need to either move this out of .gui, or move .gui.__init__ imports somewhere else

global title, minsize, minsize_ss, minesite, customer
title = 'SMS Event Log'
minsize = QSize(200, 100)
minsize_ss = 'QLabel{min-width: 100px}'
minesite_default, customer = 'FortHills', 'Suncor'

def get_mainwindow():
    """Global function to find the (open) QMainWindow in application"""
    app = QApplication.instance()
    if not app is None:
        for widget in app.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                return widget
    return None

def get_minesite():
    """Get minesite from mainwindow, or use global default for dev > FortHills"""
    mainwindow = get_mainwindow()
    if not mainwindow is None:
        return mainwindow.minesite
    else:
        return minesite_default

def get_settings():
    from . import startup
    app = startup.get_qt_app()
    mainwindow = get_mainwindow()
    if not mainwindow is None:
        return mainwindow.settings
    else:
        return QSettings('sms', 'smseventlog')

def update_statusbar(msg, *args, **kw):
    mw = get_mainwindow()
    if not mw is None:
        mw.update_statusbar(msg, *args, **kw)