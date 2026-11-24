#!/usr/bin/env bash
# Builds AzHome Media Downloader for macOS as an .app bundle inside a .dmg.
#
# Usage:  ./packaging/build_macos.sh        (MUST be run on a Mac: PyInstaller cannot cross-compile)
# Output: dist/macos/AzHomeMediaDownloader-<version>-<arch>.dmg   (arch = arm64 for Apple Silicon, x86_64 for Intel)
#
# Needs Python 3.10+ (python.org installer or Homebrew) and the Xcode Command Line Tools
# (`xcode-select --install`, provides sips/iconutil/codesign/hdiutil).
# Override the interpreter with:  PYTHON=/opt/homebrew/bin/python3 ./packaging/build_macos.sh
#
# FFmpeg is NOT bundled: the app finds a Homebrew install (brew install ffmpeg) or downloads a
# static build into ~/.fb_media_downloader/bin from its Settings page (bundling would break the code signature).
#
# The app is only ad-hoc signed (no Apple Developer ID), which is enough to run on Apple Silicon.
# On the first launch on another Mac, Gatekeeper blocks it: right-click the app > Open,
# or run:  xattr -dr com.apple.quarantine /Applications/AzHomeMediaDownloader.app
set -euo pipefail

APP_NAME="AzHomeMediaDownloader"
APP_TITLE="AzHome Media Downloader"
VERSION="${VERSION:-1.0.0}"
PYTHON="${PYTHON:-python3}"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARCH="$(uname -m)"
OUT_DIR="$PROJECT_DIR/dist/macos"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/azhome-build-XXXXXX")"
trap 'rm -rf "$WORK_DIR"' EXIT

if [ "$(uname -s)" != "Darwin" ]; then
    echo "This script must be run on macOS." >&2
    exit 1
fi

echo "==> Copying sources to $WORK_DIR"
mkdir -p "$WORK_DIR/src_copy"
tar -C "$PROJECT_DIR" \
    --exclude='__pycache__' --exclude='*.pyc' \
    -cf - src AzHomeMediaDownloader.spec requirements.txt | tar -C "$WORK_DIR/src_copy" -xf -
cd "$WORK_DIR/src_copy"

echo "==> Generating icon.icns"
ICONSET="$WORK_DIR/icon.iconset"
mkdir -p "$ICONSET"
SOURCE_ICON="src/ui/assets/icon.png"
for size in 16 32 128 256 512; do
    sips -z "$size" "$size" "$SOURCE_ICON" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z "$double" "$double" "$SOURCE_ICON" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o src/ui/assets/icon.icns

echo "==> Creating virtualenv and installing dependencies"
"$PYTHON" -m venv "$WORK_DIR/venv"
# shellcheck disable=SC1091
source "$WORK_DIR/venv/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt pyinstaller

echo "==> Running PyInstaller"
pyinstaller --noconfirm --clean \
    --distpath "$WORK_DIR/pyi_dist" --workpath "$WORK_DIR/pyi_work" \
    AzHomeMediaDownloader.spec

APP_BUNDLE="$WORK_DIR/pyi_dist/$APP_NAME.app"
[ -d "$APP_BUNDLE" ] || { echo "PyInstaller did not produce $APP_NAME.app"; exit 1; }

echo "==> Ad-hoc code signing (required on Apple Silicon)"
codesign --force --deep --sign - "$APP_BUNDLE"

echo "==> Creating .dmg"
STAGING="$WORK_DIR/dmg_staging"
mkdir -p "$STAGING" "$OUT_DIR"
cp -R "$APP_BUNDLE" "$STAGING/"
ln -s /Applications "$STAGING/Applications"
DMG_PATH="$OUT_DIR/$APP_NAME-$VERSION-$ARCH.dmg"
rm -f "$DMG_PATH"
hdiutil create -volname "$APP_TITLE" -srcfolder "$STAGING" -ov -format UDZO "$DMG_PATH" >/dev/null

echo
echo "Done: $DMG_PATH"
