"""
run pyinstaller from python script (easier) and with platform-specific args

Only the following command-line options have an effect when building from a spec file:

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
from smseventlog import (
    folders as fl,
    functions as f)

cwd = Path.cwd()

if f.is_win():
    name = 'smseventlog_win'
    # icon_name = 'sms_icon.ico'
else:
    name = 'smseventlog_mac'
    # icon_name = 'sms_icon.icns'

spec_file = str(cwd / 'smseventlog.spec')
p_build = f.buildfolder / f'build/{name}'
p_dist = f.buildfolder / 'dist'

args = ['--clean', '--noconsole', '--noconfirm', f'--workpath={str(p_build)}', f'--distpath={str(p_dist)}', spec_file]

if f.is_win():
    # --upx-dir is path to folder containing upx.exe (need to download upx from github)
    upx = str(Path.home() / 'Desktop/upx-3.96-win64')
    args.append(f'--upx-dir={upx}')

s_args = f'pyinstaller args: {args}'
print(s_args)

PyInstaller.__main__.run(args)

print(s_args)

# move exe, zip package for distribution to users
if f.is_win():
    p_share = f.projectfolder / 'dist'
    name_exe = 'SMS Event Log.exe'
    fl.copy_file(p_src=p_dist / f'{name}/{name_exe}', p_dst=p_share / name_exe, overwrite=True)
    print('Done - exe created and copied.')

    p_zip = fl.zip_folder(p=p_dist / name, p_new=p_share / name)
    print(f'folder zipped: {p_zip}')