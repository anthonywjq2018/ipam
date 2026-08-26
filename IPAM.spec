# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# 获取项目根目录
PROJECT_DIR = Path(__file__).parent.absolute()

# 数据文件收集
datas = [
    (str(PROJECT_DIR / 'templates'), 'templates'),
    (str(PROJECT_DIR / 'static'), 'static'),
    (str(PROJECT_DIR / 'data'), 'data'),
]

# 隐式导入
hiddenimports = [
    'flask',
    'paramiko',
    'cryptography',
    'sqlite3',
    'csv',
    'json',
    'datetime',
    're',
    'threading',
]

# 二进制文件（如果有）
binaries = []

a = Analysis(
    ['app.py'],
    pathex=[str(PROJECT_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'pandas', 'pytest',
        'IPython', 'jupyter', 'notebook', 'sphinx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='IPAM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windows 下无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可指定 .ico 文件
    version='version_info.txt' if os.path.exists('version_info.txt') else None,
)