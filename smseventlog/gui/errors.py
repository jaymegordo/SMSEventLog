import inspect
import types
import sys
import functools

from .. import functions as f
from PyQt5.QtWidgets import QMessageBox

   
def wrap_all_class_funcs(cls, err_func=None):
    
    # use default err handler @e
    if err_func is None: err_func = getattr(sys.modules[__name__], 'e')

    # wrap all methods in class obj with @e error handler
    module_name = inspect.getmodule(cls).__file__.split('/')[-1]
    for name, fn in inspect.getmembers(cls):
        if isinstance(fn, types.FunctionType):
            # print(f'{module_name}\t{name}:\t{fn}')
            setattr(cls, name, err_func(fn))
    
    return cls

def decorate_all_classes(module_name=None, module=None):      
    # get all classes in module and add the @e decorator to handle errors

    # pass either module or module name, but need both
    if module is None: module = sys.modules[module_name]
    if module_name is None: module_name = module.__name__

    for name, obj in inspect.getmembers(module):
        # only wrap classes definied in the module, not other imports
        if inspect.isclass(obj) and obj.__module__ == module_name:
            wrap_all_class_funcs(obj)

def e(func):
    # error handler/wrapper for the gui

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # logger = create_logger(func)
        try:
            try:
                return func(*args, **kwargs)
            except TypeError:
                return func(args[0]) # for signals passed with self, + other args that aren't needed *split
        except:
            print(f'func: {func.__name__}, args: {args}, kwargs: {kwargs}')
            f.send_error()
            
            # show error message to user
            from .dialogs import BiggerBox
            msg = f'Could not run function:\n\n{func.__name__}\n'
            dlg = BiggerBox(icon=QMessageBox.Critical, text=msg) 
            dlg.setWindowTitle('Error')
            dlg.setDetailedText(f.format_traceback())
            dlg.exec_()
            
            # logger.exception(err)
            # raise  # re-raise the exception
    return wrapper