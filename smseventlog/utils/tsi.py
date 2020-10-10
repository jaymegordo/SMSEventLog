from .__init__ import *
from ..gui import dialogs as dlgs
from . import fileops as fl

def attach_docs(ef=None):
    """Prompt user to select tsi docs and downloads to attach to tsiwebpage"""
    lst_files = []

    # show FileDialog and select docs to attach to TSI
    lst = dlgs.get_filepaths(p_start=ef._p_event)
    if not lst is None:
        lst_files.extend(lst)

    # Select download zip
    p_dls = ef.p_unit / 'Downloads'
    p_dls_year = p_dls / f'{ef.year}'
    p_start = p_dls_year if p_dls_year.exists() else p_dls
    lst = dlgs.get_filepaths(p_start=p_start)
    if not lst is None:
        lst_files.extend(lst)

    return lst_files

def example_ef(uid=None):
    # get eventfolder
    from .. import eventfolders as efl
    if uid is None:
        uid = 101133020820

    return efl.example(uid=uid)