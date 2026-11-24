import os
import json
from typing import Dict, List, Any

# Application directories
APP_DIR = os.path.join(os.path.expanduser("~"), ".fb_media_downloader")
os.makedirs(APP_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(APP_DIR, "config.json")
HISTORY_FILE = os.path.join(APP_DIR, "history.json")

# Default settings
DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "FB_Downloads")

DEFAULT_CONFIG = {
    "download_dir": DEFAULT_DOWNLOAD_DIR,
    "theme": "dark",  # "dark", "light", "system"
    "cookies_source": "none",  # "none", "browser_chrome", "browser_firefox", "browser_edge", "file"
    "cookies_file_path": "",
    "language": "en",  # "en", "vi"
    "download_playlist": False,
    "max_playlist_items": 5
}

def load_config() -> Dict[str, Any]:
    """Loads configuration, creating it with defaults if it doesn't exist."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            # Ensure all default keys exist
            for key, val in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = val
            return config
    except Exception:
        return DEFAULT_CONFIG.copy()

def save_config(config: Dict[str, Any]) -> None:
    """Saves configuration to file."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving config: {e}")

def load_history() -> List[Dict[str, Any]]:
    """Loads download history, returning an empty list if not found."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(history: List[Dict[str, Any]]) -> None:
    """Saves download history to file."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving history: {e}")

def add_to_history(url: str, title: str, file_path: str, file_size: float, media_type: str) -> None:
    """Adds a new item to the download history."""
    from datetime import datetime
    history = load_history()
    
    new_item = {
        "url": url,
        "title": title,
        "file_path": file_path,
        "file_size": file_size,
        "download_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "media_type": media_type  # "video" or "audio"
    }
    
    # Remove duplicate file path to keep history clean (move to top)
    history = [item for item in history if item.get("file_path") != file_path]
    history.insert(0, new_item)
    
    # Limit history to 100 items
    history = history[:100]
    save_history(history)
