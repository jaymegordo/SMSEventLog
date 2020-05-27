import sys
import logging
import operator as op
import time
from datetime import datetime as dt
from datetime import timedelta as delta
from timeit import default_timer as timer
from pathlib import Path
from collections import defaultdict as dd
from functools import partial

import pandas as pd
import qdarkstyle
from PyQt5.QtGui import QBrush, QColor, QFont, QIcon, QIntValidator, QKeyEvent, QKeySequence, QTextCursor
from PyQt5.QtCore import (QAbstractTableModel, QDate, QDateTime, QEvent, QFile, QModelIndex,
                        QObject, QPoint, QSettings, QSize, Qt, QTextStream,
                        QTimer, pyqtSignal, pyqtSlot, QVariant)
from PyQt5.QtWidgets import (QAbstractItemView, QAction, QApplication,
                            QCheckBox, QComboBox, QDateEdit, QDateTimeEdit, QDesktopWidget,
                            QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                            QGridLayout, QHBoxLayout, QItemDelegate, QInputDialog, QLabel,
                            QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
                            QPushButton, QSpacerItem, QSizePolicy, QSpinBox, QStyle,
                            QStyledItemDelegate, QStyleOptionComboBox, QTableView, QTabWidget,
                            QTextEdit, QVBoxLayout, QWidget, QWidgetAction)

from .. import dbmodel as dbm
from .. import eventlog as el
from .. import queries as qr
from .. import folders as fl
from .. import functions as f
from ..database import db