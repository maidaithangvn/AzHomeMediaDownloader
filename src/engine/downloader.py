import os
import re
import yt_dlp
from typing import Dict, Any, Optional, Callable
from src.utils.helpers import get_ffmpeg_path


def _friendly_cookie_error(error: Exception, cookies_source: str) -> str:
    """Turn common yt-dlp browser-cookie failures into actionable guidance."""
    message = str(error)
    lowered = message.lower()
    if cookies_source.startswith("browser_") and (
        "could not copy" in lowered
        or "cookie database" in lowered
        or "cookies" in lowered and "permission" in lowered
    ):
        browser = cookies_source.removeprefix("browser_").capitalize()
        return (
            f"Không thể đọc Cookies từ {browser}. Hãy đóng hoàn toàn {browser} "
            "(kể cả trong Task Manager), kiểm tra đúng profile rồi thử lại. "
            "Nếu vẫn lỗi, dùng file cookies.txt hoặc chạy lại ứng dụng với cùng tài khoản Windows "
            "đang đăng nhập trình duyệt.\n\nChi tiết kỹ thuật: " + message
        )
    return message

def clean_media_title(title: str) -> str:
    if not title:
        return ""
    # Remove "X views · Y reactions | " or "X views | "
    cleaned = re.sub(
        r'^\d+(?:\.\d+)?(?:K|M|B)?\s+views?\s*(?:·\s*\d+(?:\.\d+)?(?:K|M|B)?\s+reactions?)?\s*\|\s*',
        '',
        title,
        flags=re.IGNORECASE
    )
    # Remove "X_views_Y_reactions_" or "X_views_"
    cleaned = re.sub(
        r'^\d+(?:\.\d+)?(?:K|M|B)?_views_(?:\d+(?:\.\d+)?(?:K|M|B)?_reactions_)?',
        '',
        cleaned,
        flags=re.IGNORECASE
    )
    return cleaned.strip()

def get_yt_dlp_opts(
    download_dir: str,
    cookies_source: str = "none",
    cookies_file_path: str = "",
    format_type: str = "hd",  # "hd", "sd", "audio"
    progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
    postprocessor_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
    noplaylist: bool = True,
    playlist_items: str = "1-5"
) -> Dict[str, Any]:
    """
    Generates yt-dlp configuration options based on parameters.
    """
    ydl_opts = {
        'outtmpl': os.path.join(download_dir, '%(title).80s.%(ext)s'),
        'restrictfilenames': True,
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'noplaylist': noplaylist,
        'playlist_items': playlist_items,
    }

    # Add ffmpeg path if available
    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path:
        ydl_opts['ffmpeg_location'] = os.path.dirname(ffmpeg_path)

    # Configure formats
    if format_type == "hd":
        # Best video quality + best audio quality, merged into mp4 or mkv
        ydl_opts['format'] = 'bestvideo+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
    elif format_type == "sd":
        # Video with resolution <= 480p + best audio quality
        ydl_opts['format'] = 'bestvideo[height<=480]+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
    elif format_type == "audio":
        # Best audio only, converted to mp3 if ffmpeg is available, otherwise download raw audio
        ydl_opts['format'] = 'bestaudio/best'
        if ffmpeg_path:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

    # Configure cookies for private videos
    if cookies_source == "browser_chrome":
        ydl_opts['cookiesfrombrowser'] = ('chrome',)
    elif cookies_source == "browser_firefox":
        ydl_opts['cookiesfrombrowser'] = ('firefox',)
    elif cookies_source == "browser_edge":
        ydl_opts['cookiesfrombrowser'] = ('edge',)
    elif cookies_source == "file" and cookies_file_path and os.path.exists(cookies_file_path):
        ydl_opts['cookiefile'] = cookies_file_path

    # Add progress hook if provided
    if progress_hook:
        ydl_opts['progress_hooks'] = [progress_hook]

    # Add postprocessor hook if provided
    if postprocessor_hook:
        ydl_opts['postprocessor_hooks'] = [postprocessor_hook]

    return ydl_opts

def analyze_url(
    url: str,
    cookies_source: str = "none",
    cookies_file_path: str = "",
    noplaylist: bool = True,
    playlist_items: str = "1-5",
    download_dir: str = "",
    format_type: str = "hd",
    history_titles: list = None
) -> Dict[str, Any]:
    """
    Analyzes the Facebook URL and retrieves media metadata without downloading.
    Returns a dictionary of metadata (title, duration, thumbnail, etc.).
    """
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': noplaylist,
        'playlist_items': '1-50' if not noplaylist else playlist_items,
        'extract_flat': 'in_playlist',  # Tối ưu: Không lấy full stream details cho list
    }

    # Apply cookies
    if cookies_source == "browser_chrome":
        ydl_opts['cookiesfrombrowser'] = ('chrome',)
    elif cookies_source == "browser_firefox":
        ydl_opts['cookiesfrombrowser'] = ('firefox',)
    elif cookies_source == "browser_edge":
        ydl_opts['cookiesfrombrowser'] = ('edge',)
    elif cookies_source == "file" and cookies_file_path and os.path.exists(cookies_file_path):
        ydl_opts['cookiefile'] = cookies_file_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Formats extraction for user visibility if needed
            formats = []
            for f in info.get('formats', []):
                if f.get('vcodec') != 'none' or f.get('acodec') != 'none':
                    formats.append({
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'resolution': f.get('resolution') or f"{f.get('width')}x{f.get('height')}",
                        'filesize': f.get('filesize') or f.get('filesize_approx'),
                        'note': f.get('format_note')
                    })

            final_playlist_items = playlist_items
            all_already_downloaded = False
            
            # Scan existing files in download_dir and map their cleaned names to full paths
            existing_files_cleaned = {}
            if download_dir and os.path.exists(download_dir):
                try:
                    for filename in os.listdir(download_dir):
                        full_path = os.path.join(download_dir, filename)
                        if os.path.isfile(full_path):
                            cleaned_name = clean_media_title(filename).strip().lower()
                            existing_files_cleaned[cleaned_name] = full_path
                except Exception as e:
                    print(f"[DEBUG] Error listing directory: {e}")

            # Prepare set of cleaned downloaded titles from history
            downloaded_titles_cleaned = {clean_media_title(t).strip().lower() for t in (history_titles or []) if t}

            if not noplaylist and 'entries' in info and download_dir:
                entries = list(info.get('entries', []))  # Convert generator to list
                info['entries'] = entries  # Store back for later use
                undownloaded_indices = []
                max_items = 5
                if "-" in playlist_items:
                    try:
                        parts = playlist_items.split("-")
                        max_items = int(parts[1]) - int(parts[0]) + 1
                    except:
                        pass
                
                entry_titles_list = []
                with yt_dlp.YoutubeDL({'outtmpl': os.path.join(download_dir, '%(title).80s.%(ext)s'), 'restrictfilenames': True}) as temp_ydl:
                    for idx, entry in enumerate(entries):
                        if not entry:
                            continue
                        
                        entry_title = entry.get("title", "")
                        is_duplicate = False
                        
                        # 1. Check by history titles
                        entry_title_cleaned = clean_media_title(entry_title).strip().lower()
                        if entry_title_cleaned and entry_title_cleaned in downloaded_titles_cleaned:
                            is_duplicate = True
                            print(f"[DEBUG] SKIP playlist item (history): [{idx+1}] {entry_title}")
                            
                        # 2. Check by file path existence
                        if not is_duplicate:
                            predicted_filepath = temp_ydl.prepare_filename(entry)
                            if format_type == "audio" and get_ffmpeg_path() and not predicted_filepath.endswith(".mp3"):
                                base, _ = os.path.splitext(predicted_filepath)
                                predicted_filepath = base + ".mp3"
                            
                            predicted_filename = os.path.basename(predicted_filepath)
                            predicted_cleaned = clean_media_title(predicted_filename).strip().lower()
                            
                            if predicted_cleaned in existing_files_cleaned:
                                is_duplicate = True
                                print(f"[DEBUG] SKIP playlist item (clean match): [{idx+1}] {predicted_filepath}")
                            elif os.path.exists(predicted_filepath):
                                is_duplicate = True
                                print(f"[DEBUG] SKIP playlist item (file exists): [{idx+1}] {predicted_filepath}")
                                
                        if not is_duplicate:
                            undownloaded_indices.append(idx + 1)
                            entry_titles_list.append({"index": idx + 1, "title": entry_title})
                            print(f"[DEBUG] NEW playlist item: [{idx+1}] {entry_title}")
                            if len(undownloaded_indices) >= max_items:
                                break
                                
                if undownloaded_indices:
                    final_playlist_items = ",".join(map(str, undownloaded_indices))
                else:
                    all_already_downloaded = True
                    
                print(f"[DEBUG] Final playlist_items: {final_playlist_items}, all_downloaded: {all_already_downloaded}")

            # Build entry_titles for non-playlist single videos
            if not locals().get('entry_titles_list'):
                entry_titles_list = []

            # Smart duplicate checking for single videos (FB, YT, TikTok, etc.)
            if 'entries' not in info and download_dir:
                video_title = info.get("title", "")
                is_duplicate = False
                
                # 1. Check by history titles
                video_title_cleaned = clean_media_title(video_title).strip().lower()
                if video_title_cleaned and video_title_cleaned in downloaded_titles_cleaned:
                    is_duplicate = True
                    print(f"[DEBUG] Single video SKIP (history match): {video_title}")
                
                # 2. Check by file path existence
                if not is_duplicate:
                    with yt_dlp.YoutubeDL({'outtmpl': os.path.join(download_dir, '%(title).80s.%(ext)s'), 'restrictfilenames': True}) as temp_ydl:
                        predicted_filepath = temp_ydl.prepare_filename(info)
                        if format_type == "audio":
                            base, _ = os.path.splitext(predicted_filepath)
                            predicted_mp3 = base + ".mp3"
                            predicted_m4a = base + ".m4a"
                            
                            predicted_mp3_cleaned = clean_media_title(os.path.basename(predicted_mp3)).strip().lower()
                            predicted_m4a_cleaned = clean_media_title(os.path.basename(predicted_m4a)).strip().lower()
                            
                            if predicted_mp3_cleaned in existing_files_cleaned or predicted_m4a_cleaned in existing_files_cleaned:
                                is_duplicate = True
                                print(f"[DEBUG] Single video SKIP (clean audio match): {predicted_filepath}")
                            elif os.path.exists(predicted_mp3) or os.path.exists(predicted_m4a):
                                is_duplicate = True
                                print(f"[DEBUG] Single video SKIP (audio file exists): {predicted_filepath}")
                        else:
                            predicted_filename = os.path.basename(predicted_filepath)
                            predicted_cleaned = clean_media_title(predicted_filename).strip().lower()
                            
                            if predicted_cleaned in existing_files_cleaned:
                                is_duplicate = True
                                print(f"[DEBUG] Single video SKIP (clean video match): {predicted_filepath}")
                            elif os.path.exists(predicted_filepath):
                                is_duplicate = True
                                print(f"[DEBUG] Single video SKIP (video file exists): {predicted_filepath}")
                                
                if is_duplicate:
                    all_already_downloaded = True

            return {
                "success": True,
                "title": info.get("title", "Video Facebook"),
                "duration": info.get("duration", 0),
                "thumbnail": info.get("thumbnail", ""),
                "description": info.get("description", ""),
                "uploader": info.get("uploader", "Facebook User"),
                "formats": formats,
                "playlist_items": final_playlist_items,
                "all_already_downloaded": all_already_downloaded,
                "entry_titles": entry_titles_list,
                "raw_info": info
            }
    except Exception as e:
        return {
            "success": False,
            "error": _friendly_cookie_error(e, cookies_source)
        }

def download_media(
    url: str,
    download_dir: str,
    cookies_source: str = "none",
    cookies_file_path: str = "",
    format_type: str = "hd",
    progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
    postprocessor_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
    noplaylist: bool = True,
    playlist_items: str = "1-5"
) -> Dict[str, Any]:
    """
    Downloads media from the given Facebook URL.
    """
    # Ensure download directory exists
    os.makedirs(download_dir, exist_ok=True)

    ydl_opts = get_yt_dlp_opts(
        download_dir=download_dir,
        cookies_source=cookies_source,
        cookies_file_path=cookies_file_path,
        format_type=format_type,
        progress_hook=progress_hook,
        postprocessor_hook=postprocessor_hook,
        noplaylist=noplaylist,
        playlist_items=playlist_items
    )

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filepath = None
            title = info.get("title", "Video Facebook")
            downloaded_files = []
            
            # If it is a playlist, extract ALL downloaded entries
            if 'entries' in info:
                entries = info.get('entries', [])
                for entry in entries:
                    if not entry:
                        continue
                    entry_title = entry.get("title")
                    entry_filepath = None
                    req_downloads = entry.get('requested_downloads', [])
                    if req_downloads and isinstance(req_downloads, list):
                        entry_filepath = req_downloads[0].get('filepath')
                    if not entry_filepath:
                        entry_filepath = entry.get('_filename') or ydl.prepare_filename(entry)
                        
                    if entry_filepath and format_type == "audio" and get_ffmpeg_path() and not entry_filepath.endswith(".mp3"):
                        base, _ = os.path.splitext(entry_filepath)
                        entry_filepath = base + ".mp3"
                        
                    if entry_filepath and os.path.exists(entry_filepath):
                        downloaded_files.append({
                            "title": entry_title or "Song",
                            "filepath": entry_filepath,
                            "filesize": os.path.getsize(entry_filepath)
                        })
                
                if entries and entries[0]:
                    first_entry = entries[0]
                    title = first_entry.get("title", title)
                    req_downloads = first_entry.get('requested_downloads', [])
                    if req_downloads and isinstance(req_downloads, list):
                        filepath = req_downloads[0].get('filepath')
                    if not filepath:
                        filepath = first_entry.get('_filename') or ydl.prepare_filename(first_entry)
            else:
                req_downloads = info.get('requested_downloads', [])
                if req_downloads and isinstance(req_downloads, list):
                    filepath = req_downloads[0].get('filepath')
                
            if not filepath or not os.path.exists(filepath):
                filepath = info.get('_filename') or ydl.prepare_filename(info)
                
            if filepath and format_type == "audio" and get_ffmpeg_path() and not filepath.endswith(".mp3"):
                base, _ = os.path.splitext(filepath)
                filepath = base + ".mp3"
                
            return {
                "success": True,
                "title": title,
                "filepath": filepath,
                "duration": info.get("duration", 0),
                "filesize": os.path.getsize(filepath) if os.path.exists(filepath) else 0,
                "downloaded_files": downloaded_files
            }
    except Exception as e:
        return {
            "success": False,
            "error": _friendly_cookie_error(e, cookies_source)
        }
