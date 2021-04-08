# -*- mode: python -*-

project_path = None

import os
import sys
import importlib
from PyInstaller.utils.hooks import collect_submodules
from pathlib import Path
import time
start = time.time()

import warnings
warnings.filterwarnings(
    action='ignore',
    category=SyntaxWarning,
    module=r'.*firefox_profile')

# NOTE hookspath and project_path will need to be made dynamic for other devs to build project
# TODO set up environment variables file for multiple users

if not sys.platform.startswith('win'):
    project_path = '/Users/Jayme/OneDrive/Python/SMS' 
else:
    project_path = 'Y:/OneDrive/Python/SMS'

sys.path.append(project_path) # so we can import from smseventlog
from smseventlog import (
    functions as f,
    VERSION)
from smseventlog.utils import (
    fileops as fl)

# check to make sure EL isn't running currently
procs = fl.find_procs_by_name('sms event log')
if procs:
    raise Exception('Close SMS Event Log.exe first!')

datas = [
    ('smseventlog/_resources', '_resources'),
    ('SQL/FactoryCampaign/ac_motor_inspections.sql', '_resources/SQL')]

# NOTE could also figure out how to write hooks for some of these instead of *gasp* modifying source files
    # ['tinycss2', '', ('VERSION',)],
    # ['cssselect2', '', ('VERSION',)],
    # ['cairosvg', '', ('VERSION',)],
    # ['cairocffi', '', ('VERSION',)],
package_imports = [
    ['pandas', 'io/formats/templates', ('',)],
    ['pyphen', 'dictionaries', ('',)],
    ['weasyprint', 'css', ('html5_ph.css', 'html5_ua.css')],
    ['plotly', 'package_data', ('',)],   
]

for package, subdir, files in package_imports:
    proot = os.path.dirname(importlib.import_module(package).__file__)
    datas.extend((os.path.join(proot, subdir, f), f'{package}/{subdir}') for f in files)

hiddenimports = [
    'scipy.special.cython_special',
    'kaleido',
    'plotly.validators',
    'sentry_sdk.integrations.django',
    'sentry_sdk.integrations.flask',
    'sentry_sdk.integrations.bottle',
    'sentry_sdk.integrations.falcon',
    'sentry_sdk.integrations.sanic',
    'sentry_sdk.integrations.celery',
    'sentry_sdk.integrations.rq',
    'sentry_sdk.integrations.aiohttp',
    'sentry_sdk.integrations.tornado',
    'sentry_sdk.integrations.sqlalchemy',
    'sqlalchemy.sql.default_comparator']

# needed for rendering plotly charts
# this makes ~6000 hidden imports.. pretty not ideal
hidden_modules = [
    'plotly.validators.bar',
    'plotly.validators.scatter',
    'plotly.validators.layout',
    'plotly.validators.barpolar',
    'plotly.validators.carpet',
    'plotly.validators.choropleth',
    'plotly.validators.contourcarpet',
    'plotly.validators.contour',
    'plotly.validators.heatmapgl',
    'plotly.validators.heatmap.colorbar',
    'plotly.validators.histogram2dcontour',
    'plotly.validators.histogram2d',
    'plotly.validators.histogram',
    'plotly.validators.mesh3d',
    'plotly.validators.parcoords',
    'plotly.validators.pie',
    'plotly.validators.scatter3d',
    'plotly.validators.scattercarpet',
    'plotly.validators.scattergeo',
    'plotly.validators.scattergl',
    'plotly.validators.scattermapbox',
    'plotly.validators.scatterpolargl',
    'plotly.validators.scatterpolar',
    'plotly.validators.scatterternary',
    'plotly.validators.surface',
    'plotly.validators.table',
    'smseventlog.queries']
    
for item in hidden_modules:
    hiddenimports.extend(collect_submodules(item))

print('Collected submodules:', f.deltasec(start))

excludes = ['IPython', 'zmq']
binaries = []

if f.is_mac():
    # binaries = [('/usr/local/bin/chromedriver', 'selenium/webdriver')]
    hookspath = [Path.home() / '.local/share/virtualenvs/SMS-4WPEHYhu/lib/python3.8/site-packages/pyupdater/hooks']
    dist_folder_name = 'smseventlog_mac'
    icon_name = 'sms_icon.icns'
    name_pyu = 'mac' # pyupdater needs to keep this name the same, is changed for final upload/dist
    
    # this saves ~20mb, but windows matplotlib needs tkinter for some reason
    excludes.extend(['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'])
    run_pyupdater = 'pyupdater' in os.environ.get('_', '')
    py_ext = ('so',)

elif f.is_win():
    # binaries = [('File we want to copy', 'folder we want to put it in')]
    # binaries are analyzed for dependencies, datas are not
    # binaries = [('C:/Windows/chromedriver.exe', 'selenium/webdriver')]

    # gtk used for weasyprint/cairo to render images in pdfs. costs ~20mb to zip
    # NOTE maybe try to download this separately to avoid including in bundle
    datas.append(('C:/Program Files/GTK3-Runtime Win64', 'GTK3-Runtime Win64'))
    binaries.append(('C:/Program Files/GTK3-Runtime Win64/bin', 'GTK3-Runtime Win64/bin'))

    hookspath = [Path.home() / '.virtualenvs/SMS-27IjYSAU/Lib/site-packages/pyupdater/hooks']
    dist_folder_name = 'smseventlog_win'
    icon_name = 'sms_icon.ico'
    name_pyu = 'win'
    run_pyupdater = os.environ.get('KMP_INIT_AT_FORK', None) is None # this key doesnt exist with pyu
    py_ext = ('pyd', 'dll')

upx = False
upx_exclude = ['vcruntime140.dll', 'ucrtbase.dll', 'Qt5Core.dll', 'Qt5Core.dll', 'Qt5DBus.dll', 'Qt5Gui.dll', 'Qt5Network.dll', 'Qt5Qml.dll', 'Qt5QmlModels.dll', 'Qt5Quick.dll', 'Qt5Svg.dll', 'Qt5WebSockets.dll', 'Qt5Widgets.dll', 'Qt5WinExtras.dll', 'chromedriver.exe']
if upx:
    # exclude libs from upx
    import pandas
    import PyQt5
    import scipy

    for mod in (pandas, PyQt5, scipy):
        p = Path(mod.__file__).parent
        upx_exclude.extend([p.name for p in fl.find_files_ext(p, py_ext)])

icon = str(f.resources / f'images/{icon_name}')

if not eval(os.getenv('RUN_PYINSTALLER', 'False')):
    print('**** PYUPDATER ****')
    name = name_pyu # running from pyupdater
    dist_folder_name = name
    console = False
else:
    print('**** PYINSTALLER ****')
    name = 'SMS Event Log' # running from pyinstaller
    console = True

# print(os.environ)
# raise Exception('abord')

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
          upx=upx,
          upx_exclude=['vcruntime140.dll', 'ucrtbase.dll'],
          console=console,  # console=False means don't show cmd (only seems to work on windows)
          runtime_tmpdir=None,
          icon=icon)

# using COLLECT means app will be '--onedir', cant use with '--onefile'
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=upx,
               upx_exclude=upx_exclude,
               name=dist_folder_name,
               icon=icon,
               console=console)

if f.is_mac():
    app = BUNDLE(
        coll,
        name=f'{name}.app',
        icon=icon,
        bundle_identifier='com.sms.smseventlog',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': 'YES',
            'NSAppleEventsUsageDescription': 'SMS Event Log would like to automate actions in other applications.',
            'CFBundleShortVersionString': VERSION,
            'CFBundleVersion': VERSION,
            },
        )

print('Finished:', f.deltasec(start))