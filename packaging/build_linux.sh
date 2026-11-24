#!/usr/bin/env bash
# Builds AzHome Media Downloader for Linux (Ubuntu/Debian) and packages it as a .deb.
#
# Usage:  ./packaging/build_linux.sh            (run on Linux, needs python3-venv and dpkg-deb)
# Output: dist/linux/azhome-media-downloader_<version>_<arch>.deb
#
# Build on the OLDEST Ubuntu you want to support: the bundled binaries need
# at least the glibc version of the machine that built them.
set -euo pipefail

APP_ID="azhome-media-downloader"
APP_TITLE="AzHome Media Downloader"
VERSION="${VERSION:-1.0.0}"
MAINTAINER="${MAINTAINER:-AzHome Team <noreply@azhome.top>}"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$PROJECT_DIR/dist/linux"
# Build on a native filesystem (project folders on NTFS/exFAT/network drives lack symlinks and exec bits)
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/azhome-build-XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT

ARCH="$(dpkg --print-architecture)"
PKG_NAME="${APP_ID}_${VERSION}_${ARCH}"

echo "==> Copying sources to $WORK_DIR"
mkdir -p "$WORK_DIR/src_copy"
tar -C "$PROJECT_DIR" \
    --exclude='__pycache__' --exclude='*.pyc' \
    -cf - src AzHomeMediaDownloader.spec requirements.txt | tar -C "$WORK_DIR/src_copy" -xf -

echo "==> Creating virtualenv and installing dependencies"
if ! python3 -m venv "$WORK_DIR/venv" 2>/dev/null; then
    # Stock Ubuntu Desktop ships without python3-venv/ensurepip: bootstrap pip manually
    echo "    python3-venv not installed, bootstrapping pip with get-pip.py"
    rm -rf "$WORK_DIR/venv"
    python3 -m venv --without-pip "$WORK_DIR/venv"
    "$WORK_DIR/venv/bin/python" - <<'PY'
import urllib.request
urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", "/tmp/azhome-get-pip.py")
PY
    "$WORK_DIR/venv/bin/python" /tmp/azhome-get-pip.py --quiet
    rm -f /tmp/azhome-get-pip.py
fi
# shellcheck disable=SC1091
source "$WORK_DIR/venv/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r "$WORK_DIR/src_copy/requirements.txt" pyinstaller

echo "==> Running PyInstaller"
cd "$WORK_DIR/src_copy"
pyinstaller --noconfirm --clean \
    --distpath "$WORK_DIR/pyi_dist" --workpath "$WORK_DIR/pyi_work" \
    AzHomeMediaDownloader.spec

APP_BUNDLE="$WORK_DIR/pyi_dist/AzHomeMediaDownloader"
[ -x "$APP_BUNDLE/AzHomeMediaDownloader" ] || { echo "PyInstaller output missing"; exit 1; }

echo "==> Assembling .deb"
PKG_ROOT="$WORK_DIR/$PKG_NAME"
mkdir -p "$PKG_ROOT/DEBIAN" "$PKG_ROOT/opt/$APP_ID" "$PKG_ROOT/usr/bin" "$PKG_ROOT/usr/share/applications"
cp -a "$APP_BUNDLE/." "$PKG_ROOT/opt/$APP_ID/"

cat > "$PKG_ROOT/usr/bin/$APP_ID" <<EOF
#!/bin/sh
exec /opt/$APP_ID/AzHomeMediaDownloader "\$@"
EOF
chmod 755 "$PKG_ROOT/usr/bin/$APP_ID"

cat > "$PKG_ROOT/usr/share/applications/$APP_ID.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_TITLE
Comment=Tải video, reels và âm thanh HD từ Facebook, YouTube, TikTok
Exec=$APP_ID
Icon=$APP_ID
Terminal=false
Categories=AudioVideo;Network;
Keywords=download;video;youtube;facebook;tiktok;
EOF

# Icons in the standard hicolor sizes (QImage works without a display)
for size in 512 256 128 64 48; do
    mkdir -p "$PKG_ROOT/usr/share/icons/hicolor/${size}x${size}/apps"
done
QT_QPA_PLATFORM=offscreen python - "$PROJECT_DIR/src/ui/assets/icon.png" "$PKG_ROOT/usr/share/icons/hicolor" "$APP_ID" <<'PY'
import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

source, target_root, app_id = sys.argv[1:4]
image = QImage(source)
for size in (512, 256, 128, 64, 48):
    scaled = image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    scaled.save(f"{target_root}/{size}x{size}/apps/{app_id}.png")
PY

INSTALLED_KB="$(du -sk "$PKG_ROOT" | cut -f1)"
cat > "$PKG_ROOT/DEBIAN/control" <<EOF
Package: $APP_ID
Version: $VERSION
Section: video
Priority: optional
Architecture: $ARCH
Installed-Size: $INSTALLED_KB
Depends: ffmpeg, libxcb-cursor0, libxkbcommon-x11-0, libegl1, libgl1
Maintainer: $MAINTAINER
Homepage: https://azhome.top
Description: $APP_TITLE
 Download high-quality videos, reels and audio from Facebook, YouTube,
 TikTok and other sites, powered by yt-dlp and FFmpeg.
EOF

find "$PKG_ROOT" -type d -exec chmod 755 {} +
find "$PKG_ROOT/usr/share" -type f -exec chmod 644 {} +

mkdir -p "$OUT_DIR"
dpkg-deb --root-owner-group -Zxz --build "$PKG_ROOT" "$OUT_DIR/$PKG_NAME.deb"

echo
echo "Done: $OUT_DIR/$PKG_NAME.deb"
echo "Install with:  sudo apt install $OUT_DIR/$PKG_NAME.deb"
