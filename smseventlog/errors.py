import functools
import inspect
import logging
import sys
import types

import sentry_sdk
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.tornado import TornadoIntegration
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

try:
    from PyQt5.QtWidgets import QMessageBox
except ModuleNotFoundError:
    pass

from . import functions as f
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
        except:
            func_name = func.__name__
            log = logging.getLogger(inspect.getmodule(func).__name__) # get logger from func's module
            log.error(func_name, exc_info=True) # exc_info=True > sentry always captures stack trace

            print(f'func: {func_name}, args: {args}, kwargs: {kwargs}')
            f.send_error() # just print stack trace to terminal
            display_error(func_name=func_name)

    return wrapper

def display_error(func_name=None, err=None):
    # show error message to user
    from .gui.dialogs import BiggerBox
    msg = f'Couldn\'t run function:\n\n{func_name}\n'
    dlg = BiggerBox(icon=QMessageBox.Critical, text=msg) 
    dlg.setWindowTitle('Error')

    err = f.format_traceback() if err is None else err
    dlg.setDetailedText(err)
    dlg.exec_()

def errlog(msg='', err=False, warn=False):
    """Wrapper to try/except func and log error and return None

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