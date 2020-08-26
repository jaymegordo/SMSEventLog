# -*- mode: python -*-
# TODO exclude db_secret.txt from build

project_path = None

import os
import sys
import importlib
from PyInstaller.utils.hooks import collect_submodules
from pathlib import Path

# NOTE hookspath and project_path will need to be made dynamic for other devs to build project
# TODO set up environment variables file for multiple users

if not sys.platform.startswith('win'):
    project_path = '/Users/Jayme/OneDrive/Python/SMS' 
else:
    project_path = 'Y:/OneDrive/Python/SMS'

sys.path.append(project_path) # so we can import from smseventlog
from smseventlog import functions as f

datas = [
    ('smseventlog/data', 'data')]

# NOTE could also figure out how to write hooks for some of these instead of *gasp* modifying source files
package_imports = [
    ['pandas', 'io/formats/templates', ('',)],
    ['tinycss2', '', ('VERSION',)],
    ['cssselect2', '', ('VERSION',)],
    ['cairocffi', '', ('VERSION',)],
    ['cairosvg', '', ('VERSION',)],
    ['pyphen', 'dictionaries', ('',)],
    ['weasyprint', 'css', ('html5_ph.css', 'html5_ua.css')],
    ['plotly', 'package_data', ('',)],   
]

for package, subdir, files in package_imports:
    proot = os.path.dirname(importlib.import_module(package).__file__)
    datas.extend((os.path.join(proot, subdir, f), f'{package}/{subdir}') for f in files)

hiddenimports = ['scipy.special.cython_special']
hidden_modules = ['plotly.validators.bar', 'plotly.validators.scatter', 'plotly.validators.layout']
for item in hidden_modules:
    hiddenimports.extend(collect_submodules(item))

excludes = ['IPython']

if f.is_mac():
    binaries = [('/usr/local/bin/chromedriver', 'selenium/webdriver')]
    hookspath = [Path.home() / '.local/share/virtualenvs/SMS-4WPEHYhu/lib/python3.8/site-packages/pyupdater/hooks']
    dist_folder_name = 'smseventlog_mac'
    icon_name = 'sms_icon.icns'
    name_pyu = 'mac' # pyupdater needs to keep this name the same, is changed for final upload/dist
    
    # this saves ~20mb, but windows matplotlib needs tkinter for some reason
    excludes.extend(['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'])

elif f.is_win():
    binaries = [('C:/Windows/chromedriver.exe', 'selenium/webdriver')]
    hookspath = [Path.home() / '.virtualenvs/SMS-27IjYSAU/Lib/site-packages/pyupdater/hooks']
    dist_folder_name = 'smseventlog_win'
    icon_name = 'sms_icon.ico'
    name_pyu = 'win'

icon = str(f.datafolder / f'images/{icon_name}')

# TODO check if run with pyinstaller or pyupdater
if True:
    name = name_pyu
    dist_folder_name = name
else:
    name = 'SMS Event Log'

a = Analysis([f.projectfolder / 'run.py'],
             pathex=[f.buildfolder],
             binaries=binaries,
             datas=datas,
             hiddenimports=hiddenimports,
             hookspath=hookspath,
             runtime_hooks=[],
             excludes=excludes,
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data)

# TODO need to figure out which other files upx is messing up

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True, # False if using --onedir
          name=name,
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          upx_exclude=['vcruntime140.dll', 'ucrtbase.dll'],
          console=False,  # console=False means don't show cmd (only seems to work on windows)
          runtime_tmpdir=None,
          icon=icon)

# using COLLECT means app will be '--onedir', cant use with '--onefile'
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               upx_exclude=['vcruntime140.dll', 'ucrtbase.dll'],
               name=dist_folder_name,
               icon=icon,
               console=False)

if f.is_mac():
    app = BUNDLE(coll,
                name=f'{name}.app',
                icon=icon,
                bundle_identifier=None)