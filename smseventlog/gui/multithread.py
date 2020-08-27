import sys
import traceback

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from .. import functions as f


class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class Worker(QRunnable):
    def __init__(self, func, *args, **kw):
        super().__init__()
        signals = WorkerSignals()
        kw['progress_callback'] = signals.progress
        f.set_self(vars())

    @pyqtSlot()
    def run(self):

        try:
            result = self.func(*self.args, **self.kw)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done
