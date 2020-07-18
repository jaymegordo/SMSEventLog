# -*- mode: python -*-
# TODO exclude db_secret.txt from build
# TODO need to add pyodbc for windows binary

block_cipher = None
project_path = None

import os
import sys
import importlib
from PyInstaller.utils.hooks import collect_submodules

# NOTE this will need to be made dynamic for other devs to build project
if not sys.platform.startswith('win'):
    project_path = '/Users/Jayme/OneDrive/Python/SMS' 
else:
    project_path = 'Y:/OneDrive/Python/SMS'

sys.path.append(project_path)
from smseventlog import functions as f

datas = [
    ('smseventlog/data', 'data')]

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
    hookspath = ['/Users/Jayme/.local/share/virtualenvs/SMS-4WPEHYhu/lib/python3.8/site-packages/pyupdater/hooks']
    dist_folder = 'smseventlog_mac'
    
    # this saves ~20mb, but windows matplotlib needs tkinter for some reason
    excludes.extend(['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'])

elif f.is_win():
    binaries = [('C:/Windows/chromedriver.exe', 'selenium/webdriver')]
    hookspath = ['C:/Users/Jayme/.virtualenvs/SMS-27IjYSAU/Lib/site-packages/pyupdater/hooks']
    dist_folder = 'smseventlog_win'


a = Analysis([f.projectfolder / 'run.py'],
             pathex=[f.projectfolder],
             binaries=binaries,
             datas=datas,
             hiddenimports=hiddenimports,
             hookspath=hookspath,
             runtime_hooks=[],
             excludes=excludes,
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='SMS Event Log',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name=dist_folder)

