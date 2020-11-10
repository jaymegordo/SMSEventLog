import sys

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot
from smseventlog.__init__ import getlog

from .. import errors as er
from .. import functions as f

log = getlog(__name__)

# a multithread worker object - see:
# https://www.learnpyqt.com/courses/concurrent-execution/multithreading-pyqt-applications-qthreadpool/

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str, object)
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
        """Run task in background worker thread"""
        try:
            result = self.func(*self.args, **self.kw)
        except:
            msg = f'Multithread Error - {self.func.__name__}'
            self.signals.error.emit(msg, sys.exc_info())
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

    def add_signals(self, signals: list=None):
        """Add signals 
        
        Parameters
        ----------
        signals : list\n
            list of tuples of ('signal_name', dict(**kw))
        
        Examples
        -------
        Worker.add_signals(
            signals=('result', dict(func=self._install_update, args=None, kw=dict(uid=uid))

        Returns
        ------
        Worker (self)
        """
        if not isinstance(signals, list): signals = [signals]

        for sig, m in signals:
            try:
                # use lambda to connect func when result finished, and pass result func extra args
                getattr(self.signals, sig).connect(
                    lambda x: m.get('func', None)(x, *m.get('args', ()), **m.get('kw', {})))
            except:
                self.signals.error.emit(f'Failed to connect signal: {sig}, {m}', sys.exc_info())

        return self

    def start(self):
        mw = self.mw
        if not mw is None and hasattr(mw, 'threadpool'):
            mw.threadpool.start(self)
        else:
            log.error('Multithread Worker has no mainwindow or threadpool to start.', exc_info=True)
    
def send_error(msg=None, exc_info=None):
    """Wrapper to send **kw args to er.log_error from a signal in different thread"""   
    er.log_error(msg=msg, exc_info=exc_info, display=True)
