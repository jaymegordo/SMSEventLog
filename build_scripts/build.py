"""
Build using pyinstaller only (not pyupdater) to quickly build a local frozen version of the app (not used much anymore)

NOTE Only the following command-line options have an effect when building from a spec file:
--upx-dir=
--distpath=
--workpath=
--noconfirm
--ascii
--clean
"""

import PyInstaller.__main__
from pathlib import Path
import sys
import argparse
import os

CLI=argparse.ArgumentParser()
# CLI.add_argument(
#     '--upx',  
#     type=bool,
#     default=False)

CLI.add_argument(
    '--zip',  
    type=bool,
    default=False)

a = CLI.parse_args()

if sys.platform.startswith('win'):
    project_path = 'Y:/OneDrive/Python/SMS'
    name = 'smseventlog_win'
else:
    project_path = '/Users/Jayme/OneDrive/Python/SMS'
    name = 'smseventlog_mac'

sys.path.append(project_path) # so we can import from smseventlog

from smseventlog import (
    functions as f)
from smseventlog.utils import (
    fileops as fl)

spec_file = str(f.projectfolder / 'smseventlog.spec')
p_build = f.buildfolder / f'build/{name}'
p_dist = f.buildfolder / 'dist'

args = ['--log-level=WARN', '--clean', '--noconfirm', f'--workpath={str(p_build)}', f'--distpath={str(p_dist)}', spec_file]

# if f.is_win():
#     # --upx-dir is path to folder containing upx.exe (need to download upx from github)
#     upx = str(Path.home() / 'Desktop/upx-3.96-win64')
#     args.append(f'--upx-dir={upx}')

s_args = f'pyinstaller args: {args}'
print(s_args)

os.environ['RUN_PYINSTALLER'] = 'True'

PyInstaller.__main__.run(args)

os.environ['RUN_PYINSTALLER'] = 'False'
print(s_args)
print('**** DONE ****')

# move exe, zip package for distribution to users
# dont need to do this anymore.. dont need a zipped version for anything
# if f.is_win() and a.zip:
#     p_share = f.projectfolder / 'dist'
#     name_exe = 'SMS Event Log.exe'
#     fl.copy_file(p_src=p_dist / f'{name}/{name_exe}', p_dst=p_share / name_exe, overwrite=True)
#     print('Done - exe created and copied.')

#     p_zip = fl.zip_folder(p=p_dist / name, p_new=p_share / name)
#     print(f'folder zipped: {p_zip}')
