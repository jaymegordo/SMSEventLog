import functools
import inspect
import logging
import sys
import traceback
import types

import sentry_sdk
from sentry_sdk import capture_exception, push_scope
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.tornado import TornadoIntegration

from .__init__ import SYS_FROZEN, VERSION, getlog

base_log = getlog(__name__)


def global_exception_hook(*exc_info):
    """Custom exception hook to catch all errors in central location
    
    Parameters
    ---------
    exc_info : tuple\n
        Comes from sys.exc_info() - (exc_type, exc, exc_traceback)
    """
    try:
        log_error(display=True, exc_info=exc_info)
    except:
        # if any issues with custom err handling, always try pass back to sentry, then base
        base_log.error('Custom excepthook failed, falling back to sentry', exc_info=True)

        if hasattr(sys, 'sentry_excepthook'):
            sys.sentry_excepthook(*exc_info)
        else:
            base_log.debug('Failing back to sys.__excepthook__')
            sys.__excepthook__(*exc_info)


def get_func_name(func, *args, **kw):
    """Get function full name from func obj
    >>> get_func_name(func)
    >>> 'smseventlog.gui.whatever'
    """
    if func is None:
        return

    try:
        return inspect.getmodule(func).__name__
    except:
        base_log.warning(f'Failed to get func name: {func}')
        return ''

def get_logger_from_func(func):
    """Get logger from func's module"""
    try:
        log = getlog(get_func_name(func))
    except:
        # ^ no evidence of this ever failing
        log = base_log
        log.warning('Failed to get logger for func.')
    
    return log

def get_func_name_from_tb(tb):
    """Get function name from traceback, EXCLUDING lambda funcs
    - Used to get 'good' function name instead of 'couldnt run function <lambda>' """
    try:
        exclude = ('<', 'lambda')
        lst_funcs = [item.split(' in ')[1].split('\n')[0] for item in traceback.format_tb(tb)]
        return list(filter(lambda x: not any(item in x for item in exclude), lst_funcs))[0]
    except:
        base_log.warning('Couldn\'t extract function name from traceback.')
        return tb.tb_frame.f_code.co_name

def errlog(msg=None, err=True, warn=False, display=False, default=None, status_msg=False):
    """Wrapper to try/except func, log error, don't show to user, and return None
    - NOTE this suppresses the error unless display=True

    Parameters
    ----------
    msg : str, optional
        Message to add to log, by default ''\n
    err : bool, optional
        log.error message, by default False\n
    warn : bool, optional
        log.warn message, by default False
    """
    def decorator(func):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                log = get_logger_from_func(func)
                err_msg = f'Failed: {func.__name__}'
                if not msg is None:
                    err_msg = f'{err_msg} | {msg}'

                if status_msg:
                    from .gui._global import update_statusbar
                    update_statusbar(msg)
                elif warn:
                    log.warning(err_msg)
                elif err:
                    log_error(msg=msg, display=display, func=func, exc_info=sys.exc_info())

                return default # default obj to return
        
        return wrapper
    
    return decorator

def sentry_before_send(event, hint):
    """NOTE - not used, here for example. Traceback 'Raw' shows same info on sentry"""
    event['extra']['exception'] = [''.join(
        traceback.format_exception(*hint['exc_info']))]
    return event

@errlog('Failed to init Sentry')
def init_sentry():
    sentry_sdk.init(
        dsn="https://66c22032a41b453eac4e0aac4fb03f82@o436320.ingest.sentry.io/5397255",
        integrations=[SqlalchemyIntegration(), TornadoIntegration(), AioHttpIntegration()],
        release=f'sms-event-log@{VERSION}')
        # before_send=sentry_before_send)

def test_wrapper(func):
    # handle all errors in Web, allow suppression of errors if eg user closes window

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            print('Im wrapped!')
            return func(*args, **kwargs)
        except:
            print(f'failed to execute func: {func.__name__}')
    
    return wrapper

def wrap_all_class_methods_static(obj, err_func=None, exclude=None):
    # use inspect.getattr_static to avoid calling @property methods during inspect

    if not isinstance(exclude, list): exclude = [exclude]
    if err_func is None: err_func = test_wrapper

    for name in dir(obj):
        fn = inspect.getattr_static(obj, name) # if getattr called here, it would evaluate the @property

        if isinstance(fn, types.FunctionType) and not 'init' in name and not name in exclude:
            # print(name, fn)
            meth = getattr(obj, name)
            setattr(obj, name, err_func(meth))

def wrap_all_class_methods(obj, err_func, exclude=None):
    if not isinstance(exclude, list): exclude = [exclude]
    # wrap an already instantiated object's functions with err handler
    for name, fn in inspect.getmembers(obj):
        if isinstance(fn, types.MethodType) and not 'init' in name and not name in exclude:
            setattr(obj, name, err_func(fn))

def wrap_all_class_funcs(cls, err_func=None):
    # wrap all funcs in uninstantiated class defn with @e error handler
    
    # use default err handler @e
    if err_func is None: err_func = getattr(sys.modules[__name__], 'e')

    module_name = inspect.getmodule(cls).__file__.split('/')[-1]
    for name, fn in inspect.getmembers(cls):
        if isinstance(fn, types.FunctionType):
            # print(f'{module_name}\t{name}:\t{fn}')
            setattr(cls, name, err_func(fn))
    
    return cls

def decorate_all_classes(module_name=None, module=None, err_func=None):      
    # get all classes in module and add the @e decorator to handle errors
    # pass either module or module name, but need both

    if module is None: module = sys.modules[module_name]
    if module_name is None: module_name = module.__name__

    for name, obj in inspect.getmembers(module):
        # only wrap classes definied in the module, not other imports
        if inspect.isclass(obj) and obj.__module__ == module_name:
            wrap_all_class_funcs(obj, err_func=err_func)

def e(func):
    """Error handler/wrapper for the gui
    - All methods of gui objects (eg TableWidget, TableView) wrapped with this
    - NOTE not used anymore"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):

        try:
            try:
                return func(*args, **kwargs)
            except TypeError:
                return func(args[0]) # for signals passed with self, + other args that aren't needed *split
        except Exception as e:
            func_name = func.__name__
            log = get_logger_from_func(func) 

            print(f'\n\nfunc: {func_name}, args: {args}, kwargs: {kwargs}\n\n')
            log_error(func=func, exc=e, log=log, display=True)

    return wrapper

def get_last_func_name():
    """Return function name from most recent traceback"""
    # sys.exc_info:
    # (<class 'ZeroDivisionError'>, ZeroDivisionError('division by zero'), <traceback object at 0x7f84b92c1100>)
    try:
        tb = sys.exc_info()[-1] # most recent exception
        stk = traceback.extract_tb(tb, 1)
        return stk[0][2] # func name
    except:
        return 'Unknown Function'

def format_traceback(split=False):
    """Get current error and format traceback as text"""
    msg = traceback.format_exc() \
        .replace('Traceback (most recent call last):\n', '')
    
    if split:
        check_text = 'During handling of the above exception, another exception occurred:\n'
        if check_text in msg:
            msg = ''.join(msg.split(check_text)[1:])
    
    return msg

def build_message(msg=None, tb_msg=None):
    if tb_msg is None:
        tb_msg = format_traceback()

    if not msg is None:
        msg = f'{msg}:\n'

    return f'{msg}{tb_msg}'

def print_error(msg=''):
    if not SYS_FROZEN:
        msg = build_message(msg) # add traceback
        print(f'\n\n*------------------*\n{msg}')

def log_error(msg: str=None, exc: Exception=None, display: bool=False, log=None, prnt=False, func=None, func_name=None, exc_info: tuple=None, **kw):
    """Base func to log/handle errors
    - eg, ignore things like 'NoInternetError' or 'NoRowSelectedError'

    Parameters
    ----------
    msg : str, optional
        Simple message to add to start of traceback, by default None\n
    exc : Exception, optional
        Exception object used to check exc time to add extra info to display msg, by default None\n
    display : bool, optional\n
    log : logging.Logger, optional
        Logger, passed from calling module, by default None\n
    prnt : bool, optional
        Msg will be printed if not running in frozen app, by default False\n
    func: optional
        Function object\n
        Already formatted traceback string, may have been passed in from different thread, so cant build here
    exc_info : tuple
        comes from sys.excepthook, (exc_type, exc_value, exc_traceback)
    """
    if prnt:
        print_error(msg)

    # err came from excepthook, extract info
    if not exc_info is None:
        kw['tb_msg'] = ''.join(traceback.format_exception(*exc_info))
        exc_type, exc, tb = exc_info
        func_name = get_func_name_from_tb(tb=tb)
        
        if log is None:
            try:
                log = getlog(inspect.getmodule(tb).__name__) # 'smseventlog.gui.my_module'
            except:
                log = base_log
                log.warning(f'failed to get logger from tb')

    if func_name is None:
        func_name = get_func_name(func)
    
    if exc is None:
        exc = sys.exc_info()[1] # doesnt work if comes from excepthook, but all good
    
    # get extra errors if raised with 'from'
    excs = [exc]
    if hasattr(exc, '__cause__'):
        excs.append(exc.__cause__)

    # Suppress error if 'expected' (NoInternet, NoRowSelected)
    for _exc in excs:
        if issubclass(type(_exc), ExpectedError):
            return

    if display:
        display_error(exc=exc, func_name=func_name, msg=msg, **kw)

    if not log is None:
        # exc_info = True makes sentry/logger collect it
        if exc_info is None:
            exc_info = True

        if msg is None:
            msg = str(exc)

        log.error(msg, exc_info=exc_info)
        return
    
    # unhandled exception, pass back to sentry if we don't handle - doesn't ever get here
    if not exc_info is None:
        sys.sentry_excepthook(*exc_info)

def display_error(func_name: str=None, tb_msg: str=None, exc: Exception=None, log=None, msg: str=None, **kw):
    """Display error message to user in gui dialog

    Parameters
    ----------
    func_name : str, optional
        Name of function to display in message header, by default None\n
    err : str, optional
        formatted traceback message, by default None\n
    exception : Exception, optional
        Used to check exception type and add extra info, by default None\n
    msg : str, optional
        Custom message to pass in, if None use default
    """
    if func_name is None:
        func_name = get_last_func_name() # fallback to try getting from traceback

    if msg is None:
        msg = f'Couldn\'t run function: {func_name}'
    
    msg = f'{msg}\n\nThis error has been logged.\n'

    if isinstance(exc, SMSDatabaseError) or (not log is None and 'database' in log.name):
        msg = f'{msg}\nIf this is a database or network related error, check your network connection, then try doing Database > Reset Database Connection.'

    tb_msg = format_traceback() if tb_msg is None else tb_msg

    from .gui.dialogs import show_err_msg
    show_err_msg(text=msg, detailed_text=tb_msg)


# Custom error classes
class Error(Exception):
    """Base class for custom exceptions"""
    def update_statusbar(self, msg=None, **kw):
        from .gui._global import update_statusbar
        update_statusbar(msg=msg, **kw)
    
    def show_warn_dialog(self, msg=None):
        from .gui.dialogs import msg_simple
        msg_simple(msg)
    
class FakeError(Error):
    """Easy obvious fake error to throw for testing"""
    def __init__(self, message='Fake Error'):
        super().__init__(message)

class ExpectedError(Error):
    """Exceptions derrived from this class will not be logged.
    - Usually just show status message and ignore"""
    pass

class SMSDatabaseError(Error):
    """Raised when something goes wrong with the database connection"""
    def __init__(self, message='General database error'):
        super().__init__(message)

class NoInternetError(ExpectedError):
    """Raised if no internet connection detected."""
    def __init__(self, message='No internet connection available.'):
        super().__init__(message)
            
        base_log.warning('No internet connection.')
        msg = 'WARNING: No internet connection detected. Please check your connection and try again.'
        self.update_statusbar(msg=msg)

class NoRowSelectedError(ExpectedError):
    """Raised if no internet connection detected."""
    def __init__(self, message='No row selected in table.'):
        super().__init__(message)
        self.update_statusbar(msg=message, warn=True)

class InputError(ExpectedError):
    """Raised if incorrect input from dialog."""
    def __init__(self, message='Incorrect input.'):
        super().__init__(message)
        self.show_warn_dialog(msg=message)

sys._excepthook = sys.excepthook # save original excepthook
init_sentry() # sentry overrides excepthook, need to init first to override it
sys.sentry_excepthook = sys.excepthook # call events back to sentry if we want
sys.excepthook = global_exception_hook # assign custom excepthook