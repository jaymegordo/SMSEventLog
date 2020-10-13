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

try:
    from PyQt5.QtWidgets import QMessageBox
except ModuleNotFoundError:
    pass

from .__init__ import SYS_FROZEN, VERSION


def init_sentry():
    sentry_sdk.init(
        dsn="https://66c22032a41b453eac4e0aac4fb03f82@o436320.ingest.sentry.io/5397255",
        integrations=[SqlalchemyIntegration(), TornadoIntegration(), AioHttpIntegration()],
        release=f'sms-event-log@{VERSION}')

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
    # error handler/wrapper for the gui
    @functools.wraps(func)
    def wrapper(*args, **kwargs):

        try:
            try:
                return func(*args, **kwargs)
            except TypeError:
                return func(args[0]) # for signals passed with self, + other args that aren't needed *split
        except Exception as e:
            func_name = func.__name__
            log = logging.getLogger(inspect.getmodule(func).__name__) # get logger from func's module

            print(f'\n\nfunc: {func_name}, args: {args}, kwargs: {kwargs}')
            log_error(func=func, exc=e, log=log, display=True, prnt=True)

    return wrapper

def get_func_name():
    """Return function name from most recent traceback"""
    # sys.exc_info:
    # (<class 'ZeroDivisionError'>, ZeroDivisionError('division by zero'), <traceback object at 0x7f84b92c1100>)
    try:
        tb = sys.exc_info()[-1] # most recent exception
        stk = traceback.extract_tb(tb, 1)
        return stk[0][2] # func name
    except:
        return 'Unknown Function'

def format_traceback():
    """Get current error and format traceback as text"""
    msg = traceback.format_exc() \
        .replace('Traceback (most recent call last):\n', '')
       
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

def log_error(msg: str=None, exc: Exception=None, display: bool=False, log=None, prnt=False, func=None, tb_msg: str=None, func_name=None, **kw):
    """Main func to manually log errors

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
    """ 
    if prnt or not 'linux' in sys.platform:
        print_error(msg) # always print if not SYS_FROZEN

    if func_name is None:
        func_name = func.__name__ if not func is None else None
    
    if exc is None:
        exc = sys.exc_info()[1]

    if display:
        display_error(exc=exc, func_name=func_name)

    if not log is None:
        log.error(msg, exc_info=True)
        # if SYS_FROZEN or True:
        #     # traceback isn't manually captured by sentry when frozen yet.
            
        #     with push_scope() as scope:
        #         scope.set_tag('traceback', traceback.format_exc())
        #         # scope.level = 'warning'
        #         # will be tagged with my-tag="my value"
        #         print(f'Capturing exception: {type(exc)}')
        #         capture_exception(exc) # sys.exc_info()[1]


def display_error(func_name: str=None, tb_msg: str=None, exc: Exception=None, log=None):
    """Display error message to user in gui dialog

    Parameters
    ----------
    func_name : str, optional
        Name of function to display in message header, by default None\n
    err : str, optional
        formatted traceback message, by default None\n
    exception : Exception, optional
        Used to check exception type and add extra info, by default None\n
    """    
    if func_name is None:
        func_name = get_func_name() # fallback to try getting from traceback

    msg = f'Couldn\'t run function: {func_name}\n\nThis error has been logged.\n'

    if isinstance(exc, SMSDatabaseError) or (not log is None and 'database' in log.name):
        msg = f'{msg}\nIf this is a database or network related error, check your network connection, then try doing Database > Reset Database Connection.'

    tb_msg = format_traceback() if tb_msg is None else tb_msg

    from .gui.dialogs import ErrMsg
    dlg = ErrMsg(text=msg, detailed_text=tb_msg) 
    dlg.exec_()

def create_logger(func=None):
    # NOTE not used yet
    logger = logging.getLogger("example_logger")
    logger.setLevel(logging.INFO)
    
    fh = logging.FileHandler("/path/to/test.log")
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt)
    fh.setFormatter(formatter)
    # add handler to logger object
    logger.addHandler(fh)
    return logger

def errlog(msg='', err=False, warn=False):
    """Wrapper to try/except func, log error, don't show to user, and return None
    - NOTE this suppresses the error!

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
            except:
                log = logging.getLogger(inspect.getmodule(func).__name__)
                err_msg = f'Failed: {func.__name__} | {msg}'

                if warn:
                    log.warning(err_msg)
                elif err:
                    log.error(err_msg, exc_info=True)

                return None
        
        return wrapper
    
    return decorator

# Custom error classes
class Error(Exception):
    """Base class for other exceptions"""
    pass

class SMSDatabaseError(Error):
    """Raised when something goes wrong with the database connection"""
    def __init__(self, message='General database error'):
        super().__init__(message)
