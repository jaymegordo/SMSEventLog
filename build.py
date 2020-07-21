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

cwd = Path.cwd()

if sys.platform.startswith('win'):
    name = 'smseventlog_win'
    # icon_name = 'sms_icon.ico'
else:
    name = 'smseventlog_mac'
    # icon_name = 'sms_icon.icns'

spec_file = str(cwd / 'smseventlog.spec')
workpath = str(cwd / f'build/{name}')

args = ['--clean', '--noconsole', '--noconfirm', f'--workpath={workpath}', spec_file]

if sys.platform.startswith('win'):
    # --upx-dir is path to folder containing upx.exe (need to download upx from github)
    upx = str(Path.home() / 'Desktop/upx-3.96-win64')
    args.append(f'--upx-dir={upx}')

s_args = f'pyinstaller args: {args}'
print(s_args)

PyInstaller.__main__.run(args)

print(s_args)

# zip the file