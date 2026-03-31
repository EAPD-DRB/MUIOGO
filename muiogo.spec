# -*- mode: python ; coding: utf-8 -*-
# muiogo.spec — PyInstaller spec for MUIOGO (Windows)
# ---------------------------------------------------------------------------
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# --- PATH UTILITY ---
# Prevents build crashes if certain directories (like solvers) are missing locally.
def get_optional_data(src, dest):
    if os.path.exists(src):
        return (src, dest)
    return None

# ---------------------------------------------------------------------------
# Hidden imports — Bundling complex scientific and web libraries
# ---------------------------------------------------------------------------
hidden_imports = (
    collect_submodules('pandas')
    + collect_submodules('numpy')
    + collect_submodules('openpyxl')
    + collect_submodules('flask')
    + collect_submodules('waitress')
    + collect_submodules('boto3')
    + collect_submodules('botocore')
    + [
        'jinja2.ext',
        'pkg_resources.py31compat',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.timedeltas',
        'openpyxl.styles',
        'openpyxl.utils',
        'numpy.core._methods',
    ]
)

# ---------------------------------------------------------------------------
# Data files — Mapping the WebAPP structure
# ---------------------------------------------------------------------------
# Core UI and Logic files
webapp_datas = [
    ('WebAPP/App',            'WebAPP/App'),
    ('WebAPP/AppResults',     'WebAPP/AppResults'),
    ('WebAPP/Classes',        'WebAPP/Classes'),
    ('WebAPP/DataStorage',    'WebAPP/DataStorage'),
    ('WebAPP/References',     'WebAPP/References'),
    ('WebAPP/Routes',         'WebAPP/Routes'),
    ('WebAPP/index.html',     'WebAPP'),
]

# Optional Solver Binaries (Only bundle if they exist on the build machine)
potential_solvers = [
    ('WebAPP/SOLVERs/COIN-OR',         'WebAPP/SOLVERs/COIN-OR'),
    ('WebAPP/SOLVERs/GLPK',            'WebAPP/SOLVERs/GLPK'),
    ('WebAPP/SOLVERs/model.v.5.4.txt', 'WebAPP/SOLVERs'),
]

for src, dest in potential_solvers:
    item = get_optional_data(src, dest)
    if item:
        webapp_datas.append(item)

collected_datas = (
    webapp_datas
    + collect_data_files('pandas')
    + collect_data_files('numpy')
    + collect_data_files('openpyxl')
    + collect_data_files('tzdata')
)

# ---------------------------------------------------------------------------
# Analysis & Build Configuration
# ---------------------------------------------------------------------------
a = Analysis(
    ['API/app.py'],
    pathex=['.'],
    binaries=[],
    datas=collected_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'IPython', 'matplotlib', 'scipy', 'sklearn'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='muiogo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'cbc.exe', 'glpsol.exe', 'coinblas.dll', 
        'coinlapack.dll', 'CoinUtils.dll', 'Cbc.dll', 'glpk_4_65.dll'
    ],
    name='muiogo',
)