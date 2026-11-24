import os
import sys
import ssl
import shutil
import platform
import subprocess
import tarfile
import urllib.request
import zipfile
import tempfile
from typing import Optional, Callable, Dict, List, Tuple

from src.config import APP_DIR

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"

# GUI apps launched from Finder/desktop menus do not inherit the shell PATH,
# so common package-manager locations are searched explicitly.
_EXTRA_BIN_DIRS = ["/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin", "/usr/bin"]

# Static FFmpeg builds per (system, machine). Each entry is a list of mirrors;
# a mirror is the list of archive URLs needed to obtain both ffmpeg and ffprobe.
_FFMPEG_MIRRORS: Dict[Tuple[str, str], List[List[str]]] = {
    ("windows", "x86_64"): [
        ["https://github.com/GyanD/codexffmpeg/releases/download/7.1/ffmpeg-7.1-essentials_build.zip"],
    ],
    ("linux", "x86_64"): [
        ["https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"],
    ],
    ("linux", "arm64"): [
        ["https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz"],
    ],
    ("darwin", "x86_64"): [
        ["https://evermeet.cx/ffmpeg/getrelease/zip",
         "https://evermeet.cx/ffmpeg/getrelease/ffprobe/zip"],
        ["https://ffmpeg.martin-riedl.de/redirect/latest/macos/amd64/release/ffmpeg.zip",
         "https://ffmpeg.martin-riedl.de/redirect/latest/macos/amd64/release/ffprobe.zip"],
    ],
    ("darwin", "arm64"): [
        ["https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/release/ffmpeg.zip",
         "https://ffmpeg.martin-riedl.de/redirect/latest/macos/arm64/release/ffprobe.zip"],
        ["https://www.osxexperts.net/ffmpeg80arm.zip",
         "https://www.osxexperts.net/ffprobe80arm.zip"],
    ],
}


def _exe_name(name: str) -> str:
    return f"{name}.exe" if IS_WINDOWS else name


def _platform_key() -> Tuple[str, str]:
    system = "windows" if IS_WINDOWS else ("darwin" if IS_MACOS else "linux")
    machine = platform.machine().lower()
    if machine in ("amd64", "x86_64", "x64"):
        machine = "x86_64"
    elif machine in ("aarch64", "arm64"):
        machine = "arm64"
    if system == "windows":
        machine = "x86_64"
    return system, machine


def get_bin_dir() -> str:
    """
    Returns the bin/ directory shipped with the application, supporting both
    development mode and packaged PyInstaller executable mode.
    """
    if getattr(sys, 'frozen', False):
        # One-file PyInstaller builds extract bundled files into _MEIPASS.
        # A one-folder build keeps them next to the executable.
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        # Dev mode: bin/ folder is in the project root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    return os.path.join(base_dir, "bin")


def get_user_bin_dir() -> str:
    """User-writable bin/ directory used for auto-downloaded FFmpeg."""
    return os.path.join(APP_DIR, "bin")


def get_ffmpeg_path() -> Optional[str]:
    """
    Looks for ffmpeg in the system PATH, common package-manager locations,
    the bundled bin/ directory and the user's bin/ directory (in that order).
    Returns the absolute path to the ffmpeg executable, or None if not found.
    """
    ffmpeg_sys = shutil.which("ffmpeg")
    if ffmpeg_sys:
        return ffmpeg_sys

    ffmpeg_name = _exe_name("ffmpeg")
    search_dirs = [] if IS_WINDOWS else _EXTRA_BIN_DIRS
    for directory in [*search_dirs, get_bin_dir(), get_user_bin_dir()]:
        candidate = os.path.join(directory, ffmpeg_name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


def _ssl_context() -> ssl.SSLContext:
    """Build a verified TLS context suited to the current platform.

    Windows users may have a trusted antivirus/proxy root installed in the
    Windows certificate store but not in certifi.  Prefer the system store on
    Windows, while frozen macOS builds use certifi because they may not expose
    a usable system CA path.
    """
    if IS_WINDOWS:
        return ssl.create_default_context()
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _download_file(url: str, dest_path: str, on_progress: Callable[[float, float, float], None]) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AzHomeMediaDownloader"})
    # Download into a caller-owned temporary path.  The caller only extracts
    # after the complete archive has arrived, so a failed download cannot
    # leave a half-written FFmpeg binary in the user's bin directory.
    with urllib.request.urlopen(request, timeout=60, context=_ssl_context()) as response, \
            open(dest_path, "wb") as out_file:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = response.read(256 * 1024)
            if not chunk:
                break
            out_file.write(chunk)
            done += len(chunk)
            if total > 0:
                on_progress(done / total, done / (1024 * 1024), total / (1024 * 1024))


def _extract_ffmpeg_binaries(archive_path: str, target_dir: str) -> None:
    """Extracts ffmpeg/ffprobe from a zip or tar archive into target_dir."""
    wanted = {_exe_name("ffmpeg"), _exe_name("ffprobe")}

    def save(name: str, source) -> None:
        target_path = os.path.join(target_dir, name)
        temp_path = f"{target_path}.part"
        with open(temp_path, "wb") as target:
            shutil.copyfileobj(source, target)
        os.replace(temp_path, target_path)
        if not IS_WINDOWS:
            os.chmod(target_path, 0o755)

    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            for member in zip_ref.namelist():
                name = os.path.basename(member)
                if name in wanted:
                    with zip_ref.open(member) as source:
                        save(name, source)
    else:
        with tarfile.open(archive_path, "r:*") as tar_ref:
            for member in tar_ref.getmembers():
                name = os.path.basename(member.name)
                if member.isfile() and name in wanted:
                    source = tar_ref.extractfile(member)
                    if source is not None:
                        with source:
                            save(name, source)


def download_ffmpeg(
    progress_callback: Optional[Callable[[float, str], None]] = None,
    target_dir: Optional[str] = None,
) -> bool:
    """
    Downloads a portable static FFmpeg build for the current OS/CPU and
    extracts ffmpeg/ffprobe into target_dir (defaults to the user's bin/ dir).
    """
    target_dir = target_dir or get_user_bin_dir()
    os.makedirs(target_dir, exist_ok=True)

    mirrors = _FFMPEG_MIRRORS.get(_platform_key())
    if not mirrors:
        if progress_callback:
            progress_callback(-1.0, f"Lỗi tải FFmpeg: chưa hỗ trợ nền tảng {_platform_key()}")
        return False

    last_error = "không rõ"
    for urls in mirrors:
        work_dir = tempfile.mkdtemp(prefix="ffmpeg_dl_")
        try:
            if progress_callback:
                progress_callback(0.0, "Đang kết nối tới máy chủ tải FFmpeg...")

            for index, url in enumerate(urls):
                archive_path = os.path.join(work_dir, f"archive_{index}")

                def on_progress(fraction: float, done_mb: float, total_mb: float, index: int = index) -> None:
                    if progress_callback:
                        overall = (index + fraction) / len(urls)
                        progress_callback(
                            overall,
                            f"Đang tải FFmpeg: {fraction * 100:.1f}% ({done_mb:.1f}MB / {total_mb:.1f}MB)"
                        )

                _download_file(url, archive_path, on_progress)
                if progress_callback:
                    progress_callback(1.0, "Đang giải nén FFmpeg...")
                _extract_ffmpeg_binaries(archive_path, target_dir)

            if not (os.path.isfile(os.path.join(target_dir, _exe_name("ffmpeg")))):
                raise RuntimeError("Không tìm thấy ffmpeg trong file tải về")

            if progress_callback:
                progress_callback(1.0, "Đã cài đặt FFmpeg thành công!")
            return True
        except Exception as e:
            last_error = str(e)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    if progress_callback:
        progress_callback(-1.0, f"Lỗi tải FFmpeg: {last_error}")
    return False


def _external_env() -> Dict[str, str]:
    """
    Environment for launching system programs from a PyInstaller build:
    restores the loader paths PyInstaller overrides, which otherwise make
    system apps (xdg-open, file managers) load the bundled libraries.
    """
    env = os.environ.copy()
    if getattr(sys, 'frozen', False):
        for var in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
            original = env.get(f"{var}_ORIG")
            if original is not None:
                env[var] = original
            else:
                env.pop(var, None)
    return env


def open_path(path: str) -> None:
    """Opens a file or folder with the OS default application."""
    if IS_WINDOWS:
        os.startfile(path)
    elif IS_MACOS:
        subprocess.Popen(["open", path], env=_external_env())
    else:
        subprocess.Popen(["xdg-open", path], env=_external_env(), start_new_session=True)


def reveal_in_file_manager(path: str) -> None:
    """Shows a file selected in the OS file manager (folder only on Linux)."""
    if IS_WINDOWS:
        subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
    elif IS_MACOS:
        subprocess.Popen(["open", "-R", path], env=_external_env())
    else:
        open_path(os.path.dirname(os.path.abspath(path)))


def format_bytes(n_bytes: float) -> str:
    """
    Formats bytes into a human-readable string (e.g., 10.4 MB).
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if n_bytes < 1024.0:
            return f"{n_bytes:.2f} {unit}"
        n_bytes /= 1024.0
    return f"{n_bytes:.2f} PB"

def format_seconds(seconds: float) -> str:
    """
    Formats seconds into MM:SS or HH:MM:SS format.
    """
    if seconds is None or seconds < 0:
        return "00:00"

    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def get_resource_path(relative_path: str) -> str:
    """
    Returns the absolute path to a resource, supporting both dev mode
    and packaged PyInstaller mode (using sys._MEIPASS).
    """
    import sys
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, relative_path)
