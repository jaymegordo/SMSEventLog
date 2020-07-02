# -*- mode: python -*-

block_cipher = None

import os
import importlib
from PyInstaller.utils.hooks import collect_submodules

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


a = Analysis(['/Users/Jayme/OneDrive/Python/SMS/run.py'],
             pathex=['/Users/Jayme/OneDrive/Python/SMS'],
             binaries=[('/usr/local/bin/chromedriver', 'selenium/webdriver')],
             datas=datas,
             hiddenimports=hiddenimports,
             hookspath=['/Users/Jayme/.local/share/virtualenvs/SMS-4WPEHYhu/lib/python3.8/site-packages/pyupdater/hooks'],
             runtime_hooks=[],
             excludes=['IPython', 'FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
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
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='mac')

