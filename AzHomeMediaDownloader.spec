# -*- mode: python ; coding: utf-8 -*-

import os
import sys

from PyInstaller.utils.hooks import collect_all


IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"


if IS_WINDOWS:
    icon_file = "src/ui/assets/icon.ico"
    ffmpeg_binaries = []

    for binary_name in ("ffmpeg.exe", "ffprobe.exe"):
        binary_path = os.path.join("bin", binary_name)
        if os.path.isfile(binary_path):
            ffmpeg_binaries.append((binary_path, "bin"))
elif IS_MACOS:
    icon_file = "src/ui/assets/icon.icns"
    ffmpeg_binaries = []
else:
    icon_file = "src/ui/assets/icon.png"
    ffmpeg_binaries = []


# Collect PySide6, Qt plugins and native binaries for the packaged app.
pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all(
    "PySide6"
)

all_binaries = pyside6_binaries + ffmpeg_binaries
all_datas = [("src", "src")] + pyside6_datas


a = Analysis(
    ["src/main.py"],
    pathex=[],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=pyside6_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)


if IS_WINDOWS:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="AzHomeMediaDownloader",
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
        icon=icon_file if os.path.exists(icon_file) else None,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="AzHomeMediaDownloader",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_file if os.path.exists(icon_file) else None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name="AzHomeMediaDownloader",
    )

    if IS_MACOS:
        app = BUNDLE(
            coll,
            name="AzHomeMediaDownloader.app",
            icon=icon_file if os.path.exists(icon_file) else None,
            bundle_identifier="top.azhome.mediadownloader",
            info_plist={
                "CFBundleName": "AzHome Media Downloader",
                "CFBundleDisplayName": "AzHome Media Downloader",
                "CFBundleShortVersionString": "1.0.0",
                "NSHighResolutionCapable": True,
            },
        )
