# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

# CustomTkinter veri dosyalarını topluyoruz
datas = collect_data_files('customtkinter')

# Proje kaynak dosyalarını ve şablonları ekliyoruz
datas += [
    ('data/images/logo.png', 'data/images'),
    ('data/images/logo.ico', 'data/images'),
    ('taslak.docx', '.'),
    ('py_optik/logo.png', 'py_optik'),
    ('py_optik/icon.ico', 'py_optik'),
    ('py_optik/icon.png', 'py_optik'),
    ('py_optik/sablonlar.json', 'py_optik'),
    ('py_optik/shortcuts.json', 'py_optik'),
    ('py_optik/CEVAP1.Txt', 'py_optik'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'customtkinter',
        'PIL',
        'sqlalchemy',
        'pandas',
        'openpyxl',
        'docx',
        'pytesseract',
        'pypdf',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'cv2',
        'numpy',
        'fpdf2',
        'matplotlib',
        'py_optik.main',
    ],
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
    name='ERYSinav',
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
    icon=['data/images/logo.ico'],
)
