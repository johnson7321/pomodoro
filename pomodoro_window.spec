# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

# Pull in customtkinter completely (data, binaries, submodules)
for pkg in ('customtkinter',):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h
    hiddenimports += collect_submodules(pkg)

# darkdetect is used internally by customtkinter for "System" mode
hiddenimports += collect_submodules('darkdetect')

# Also matplotlib backends used by our charts
hiddenimports += [
    'matplotlib.backends.backend_tkagg',
    'matplotlib.backends._backend_tk',
]

# Our own package
hiddenimports += [
    'pomodoro',
    'pomodoro.config',
    'pomodoro.theme',
    'pomodoro.core',
    'pomodoro.core.timer_engine',
    'pomodoro.core.csv_logger',
    'pomodoro.core.hosts_blocker',
    'pomodoro.core.win11_effects',
    'pomodoro.ui',
    'pomodoro.ui.widgets',
    'pomodoro.ui.main_window',
    'pomodoro.ui.history_chart',
    'pomodoro.ui.history_list',
    'pomodoro.ui.blocked_sites_window',
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='pomodoro_window',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
