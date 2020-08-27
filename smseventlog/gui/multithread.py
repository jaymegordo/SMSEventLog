import sys
import traceback
import logging

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from .. import functions as f

log = logging.getLogger(__name__)

# a multithread worker object - see:
# https://www.learnpyqt.com/courses/concurrent-execution/multithreading-pyqt-applications-qthreadpool/

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class Worker(QRunnable):
    def __init__(self, func, mw=None, *args, **kw):
        super().__init__()
        signals = WorkerSignals()
        kw['progress_callback'] = signals.progress
        signals.error.connect(f.send_error)
        f.set_self(vars())

    @pyqtSlot()
    def run(self):

        try:
            result = self.func(*self.args, **self.kw)
        except:
            # traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            # self.signals.error.emit((exctype, value, traceback.format_exc()))
            self.signals.error.emit(str(exctype))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

    def add_signals(self, signals=None):
        # add signals as list of tuples of:
        if not isinstance(signals, list): signals = [signals]
        # ('signal', m_args) > eg dict(func=self._install_update, args=None, kw=None)

        for sig, m in signals:

            try:
                getattr(self.signals, sig).connect(
                    m.get('func', None),
                    *m.get('args', ()),
                    **m.get('kw', {}))
            except:
                self.signals.error.emit(f'failed to connect signal: {sig, m}')

        return self

    def start(self):
        mw = self.mw
        if not mw is None and hasattr(mw, 'threadpool'):
            mw.threadpool.start(self)
        else:
            log.error('Multithread Worker has no mainwindow or threadpool to start.')