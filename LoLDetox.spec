# -*- mode: python ; coding: utf-8 -*-
# Tek premium EXE: arayüz + motor + overlay + watcher

a = Analysis(
    ['lol_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['lol_engine', 'lol_config', 'lol_homoglyph', 'lol_chat_detector', 'lol_enter_hook', 'lol_i18n'],
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
    name='LoLDetox',
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
