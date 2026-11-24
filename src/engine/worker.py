from PySide6.QtCore import QThread, Signal
from typing import Dict, Any, Optional
from src.engine.downloader import analyze_url, download_media
from src.utils.helpers import format_bytes, format_seconds

class AnalyzeWorker(QThread):
    """
    Background worker for analyzing Facebook URLs.
    Prevents the UI from freezing while scraping metadata.
    """
    finished = Signal(dict)

    def __init__(
        self, 
        url: str, 
        cookies_source: str = "none", 
        cookies_file_path: str = "",
        noplaylist: bool = True,
        playlist_items: str = "1-5",
        download_dir: str = "",
        format_type: str = "hd",
        history_titles: list = None
    ):
        super().__init__()
        self.url = url
        self.cookies_source = cookies_source
        self.cookies_file_path = cookies_file_path
        self.noplaylist = noplaylist
        self.playlist_items = playlist_items
        self.download_dir = download_dir
        self.format_type = format_type
        self.history_titles = history_titles or []

    def run(self):
        result = analyze_url(
            self.url,
            cookies_source=self.cookies_source,
            cookies_file_path=self.cookies_file_path,
            noplaylist=self.noplaylist,
            playlist_items=self.playlist_items,
            download_dir=self.download_dir,
            format_type=self.format_type,
            history_titles=self.history_titles
        )
        self.finished.emit(result)


class DownloadWorker(QThread):
    """
    Background worker for downloading media from Facebook.
    Provides real-time progress updates through Qt Signals.
    """
    progress = Signal(dict)
    finished = Signal(dict)

    def __init__(
        self, 
        url: str, 
        download_dir: str, 
        cookies_source: str = "none", 
        cookies_file_path: str = "",
        format_type: str = "hd",
        noplaylist: bool = True,
        playlist_items: str = "1-5"
    ):
        super().__init__()
        self.url = url
        self.download_dir = download_dir
        self.cookies_source = cookies_source
        self.cookies_file_path = cookies_file_path
        self.format_type = format_type
        self.noplaylist = noplaylist
        self.playlist_items = playlist_items
        self.is_cancelled = False

    def run(self):
        def yt_dlp_progress_hook(d: Dict[str, Any]):
            if self.is_cancelled:
                raise Exception("Tác vụ đã bị hủy bởi người dùng.")

            if d.get('status') == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                
                percent = 0.0
                if total > 0:
                    percent = (downloaded / total) * 100.0
                
                speed_val = d.get('speed') or 0
                speed_str = f"{format_bytes(speed_val)}/s" if speed_val > 0 else "-- KB/s"
                
                eta_val = d.get('eta') or 0
                eta_str = format_seconds(eta_val) if eta_val > 0 else "--:--"
                
                progress_info = {
                    "status": "downloading",
                    "percent": percent,
                    "downloaded": format_bytes(downloaded),
                    "total": format_bytes(total) if total > 0 else "Unknown",
                    "speed": speed_str,
                    "eta": eta_str
                }
                self.progress.emit(progress_info)
                
            elif d.get('status') == 'finished':
                progress_info = {
                    "status": "finished",
                    "percent": 100.0,
                    "speed": "0 B/s",
                    "eta": "00:00"
                }
                self.progress.emit(progress_info)

        def yt_dlp_postprocessor_hook(d: Dict[str, Any]):
            if self.is_cancelled:
                raise Exception("Tác vụ đã bị hủy bởi người dùng.")

            pp_name = d.get('postprocessor', '')
            status = d.get('status', '')
            
            msg = "Đang xử lý ghép nối/chuyển đổi..."
            if pp_name == "ExtractAudio":
                if status == "started":
                    msg = "Đang chuyển đổi sang MP3 (Có thể mất vài phút với file lớn)..."
                elif status == "finished":
                    msg = "Đã hoàn thành chuyển đổi MP3!"
            elif pp_name == "Merger":
                if status == "started":
                    msg = "Đang ghép nối luồng video HD & âm thanh..."
                elif status == "finished":
                    msg = "Đã hoàn thành ghép nối HD!"
            
            progress_info = {
                "status": "postprocessing",
                "percent": 100.0,
                "speed": msg,
                "eta": "--:--"
            }
            self.progress.emit(progress_info)

        result = download_media(
            url=self.url,
            download_dir=self.download_dir,
            cookies_source=self.cookies_source,
            cookies_file_path=self.cookies_file_path,
            format_type=self.format_type,
            progress_hook=yt_dlp_progress_hook,
            postprocessor_hook=yt_dlp_postprocessor_hook,
            noplaylist=self.noplaylist,
            playlist_items=self.playlist_items
        )
        
        self.finished.emit(result)

    def cancel(self):
        """Signals the downloader to stop."""
        self.is_cancelled = True
