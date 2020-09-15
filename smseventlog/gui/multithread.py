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
    error = pyqtSignal(str, str, object)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class Worker(QRunnable):
    def __init__(self, func, mw=None, *args, **kw):
        super().__init__()
        signals = WorkerSignals()
        # kw['progress_callback'] = signals.progress
        signals.error.connect(send_error)
        f.set_self(vars())

    @pyqtSlot()
    def run(self):

        try:
            result = self.func(*self.args, **self.kw)
        except:
            # exctype, value = sys.exc_info()[:2]
            # self.signals.error.emit((exctype, value, traceback.format_exc()))
            
            # need to use logger internal to thread to properly capture stack trace
            msg = f'Multithread Error - {self.func.__name__}' #\n{f.format_traceback()}'
            log.error(msg, exc_info=True)

            # also emit for gui to display
            self.signals.error.emit('Multithread Error', f.format_traceback(), self.func)
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

    def add_signals(self, signals=None):
        # add signals as list of tuples of:
        # eg: ('signal', m_args) > eg dict(func=self._install_update, args=None, kw=dict(uid=uid))
        if not isinstance(signals, list): signals = [signals]

        for sig, m in signals:
            try:
                # use lambda to connect func when result finished, and pass result func extra args
                getattr(self.signals, sig).connect(
                    lambda x: m.get('func', None)(x, *m.get('args', ()), **m.get('kw', {})))
            except:
                self.signals.error.emit(f'Failed to connect signal: {sig, m}', f.format_traceback())

        return self

    def start(self):
        mw = self.mw
        if not mw is None and hasattr(mw, 'threadpool'):
            mw.threadpool.start(self)
        else:
            log.error('Multithread Worker has no mainwindow or threadpool to start.')
    
def send_error(msg, err=None, func=None):
    # wrapper to send **kw args to f.send_error from a signal in different thread
    # This error handling is so messy I'm sorry future me or someone else..
    if err is None:
        err = traceback.format_exc()
    
    if not func is None:
        msg = f'{msg} - {func.__name__}'
    
    f.send_error(msg=msg, err=err, logger=None, display=True, func=func)
