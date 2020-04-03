# -*- mode: python -*-

block_cipher = None


a = Analysis(['/Users/Jayme/OneDrive/Python/SMS/run.py'],
             pathex=['/Users/Jayme/OneDrive/Python/SMS'],
             binaries=[],
             datas=[('smseventlog/data', 'data')],
             hiddenimports=[],
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
          name='mac',
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
