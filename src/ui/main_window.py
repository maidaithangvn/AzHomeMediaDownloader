import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QStackedWidget,
    QLabel, QLineEdit, QPushButton, QComboBox, QFileDialog, QProgressBar,
    QScrollArea, QGroupBox, QMessageBox, QFrame, QSizePolicy, QCheckBox, QSpinBox
)
from PySide6.QtCore import Qt, QTimer, Slot, QUrl, QThread, Signal
from PySide6.QtGui import QClipboard, QGuiApplication, QDesktopServices, QIcon, QPixmap

from src.config import load_config, save_config, load_history, add_to_history, save_history
from src.ui.styles import DARK_STYLE, LIGHT_STYLE
from src.ui.components import HistoryCard
from src.engine.worker import AnalyzeWorker, DownloadWorker
from src.utils.helpers import (
    get_ffmpeg_path, download_ffmpeg, format_seconds, format_bytes, get_resource_path,
    open_path, reveal_in_file_manager
)
from src.utils.translations import t, set_language

class MainWindow(QMainWindow):
    """
    The main window of the Facebook Media Downloader application.
    Implements multi-tab navigation, Fluent Design stylesheets,
    asynchronous operations, and smart features like clipboard sensing.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AzHome Media Downloader - Tải Video Facebook, YouTube, TikTok")
        self.setMinimumSize(950, 650)
        
        # Set Window Icon
        icon_path = get_resource_path("src/ui/assets/icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Load configurations
        self.config = load_config()
        set_language(self.config.get("language", "en"))
        self.history = load_history()
        
        # Core state variables
        self.analyze_worker = None
        self.download_worker = None
        self.ffmpeg_download_thread = None
        self.analyzed_metadata = None
        
        # UI Setup
        self.init_ui()
        self.apply_theme(self.config.get("theme", "dark"))
        
        # Initialize Clipboard Monitor
        self.clipboard = QGuiApplication.clipboard()
        self.clipboard.dataChanged.connect(self.on_clipboard_changed)
        
        # Trigger initial check on startup
        QTimer.singleShot(1000, self.check_clipboard_on_start)

    def init_ui(self):
        # Main central widget with horizontal layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Left Sidebar Navigation
        self.sidebar = QListWidget(self)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(200)
        self.sidebar.addItem(t("tab_download"))
        self.sidebar.addItem(t("tab_history"))
        self.sidebar.addItem(t("tab_settings"))
        self.sidebar.addItem(t("tab_about"))
        self.sidebar.currentRowChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.sidebar)

        # Right side content area
        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)

        # 1.1 Header Section
        header_layout = QHBoxLayout()
        self.page_title = QLabel(t("title_download"), self)
        self.page_title.setObjectName("title_label")
        header_layout.addWidget(self.page_title)
        
        header_layout.addStretch()
        
        # Theme toggle button
        self.btn_theme = QPushButton("🌙 Dark Mode", self)
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.btn_theme)
        
        right_layout.addLayout(header_layout)

        # 1.2 Stacked Content Pages
        self.pages = QStackedWidget(self)
        
        # Create pages
        self.create_download_page()
        self.create_history_page()
        self.create_settings_page()
        self.create_about_page()
        
        right_layout.addWidget(self.pages)
        main_layout.addWidget(right_panel, 1)

        # Select first tab by default
        self.sidebar.setCurrentRow(0)

    # --- PAGE CREATION METHODS ---

    def create_download_page(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        # Managed globally by styles.py to prevent forcing transparency on children

        page = QWidget(scroll)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Group 1: URL Input
        input_group = QGroupBox(t("group_url"), page)
        input_layout = QVBoxLayout(input_group)
        input_layout.setSpacing(10)

        url_row = QHBoxLayout()
        self.txt_url = QLineEdit(page)
        self.txt_url.setPlaceholderText(t("placeholder_url"))
        self.txt_url.textChanged.connect(self.on_url_input_changed)
        url_row.addWidget(self.txt_url)

        self.btn_paste = QPushButton(t("btn_paste"), page)
        self.btn_paste.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_paste.clicked.connect(self.paste_from_clipboard)
        url_row.addWidget(self.btn_paste)

        input_layout.addLayout(url_row)

        # Format selection + Analyze button row
        format_analyze_row = QHBoxLayout()
        format_analyze_row.setSpacing(10)
        format_analyze_row.addWidget(QLabel(t("lbl_format"), page))
        self.cbo_format = QComboBox(page)
        self.cbo_format.addItem(t("format_hd"), "hd")
        self.cbo_format.addItem(t("format_sd"), "sd")
        self.cbo_format.addItem(t("format_audio"), "audio")
        self.cbo_format.setCurrentIndex(2)  # Default to MP3
        self.cbo_format.setMinimumWidth(180)
        format_analyze_row.addWidget(self.cbo_format)
        format_analyze_row.addStretch()

        self.btn_analyze = QPushButton(t("btn_analyze"), page)
        self.btn_analyze.setObjectName("btn_primary")
        self.btn_analyze.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analyze.clicked.connect(self.start_analysis)
        format_analyze_row.addWidget(self.btn_analyze)

        input_layout.addLayout(format_analyze_row)
        
        # Small helper info text
        self.lbl_input_tip = QLabel(t("tip_clipboard"), page)
        self.lbl_input_tip.setStyleSheet("color: #7C4DFF; font-size: 13px; font-weight: 500;")
        input_layout.addWidget(self.lbl_input_tip)
        
        layout.addWidget(input_group)

        # Group 2: Analyzed Media Info Card (Hidden by default)
        self.media_info_card = QGroupBox(t("group_info"), page)
        self.media_info_card.setVisible(False)
        media_layout = QVBoxLayout(self.media_info_card)
        media_layout.setSpacing(8)

        self.lbl_media_title = QLabel(t("lbl_title"), page)
        self.lbl_media_title.setStyleSheet("font-weight: 600; font-size: 17px; color: #7C4DFF;")
        self.lbl_media_title.setWordWrap(True)
        media_layout.addWidget(self.lbl_media_title)

        meta_row = QHBoxLayout()
        self.lbl_media_uploader = QLabel(t("lbl_uploader"), page)
        self.lbl_media_uploader.setStyleSheet("color: #888888;")
        meta_row.addWidget(self.lbl_media_uploader)

        self.lbl_media_duration = QLabel(t("lbl_duration"), page)
        self.lbl_media_duration.setStyleSheet("color: #888888;")
        meta_row.addWidget(self.lbl_media_duration)
        
        meta_row.addStretch()
        media_layout.addLayout(meta_row)

        # Song list with checkboxes (for playlists)
        self.song_list_container = QGroupBox(t("group_song_list"), page)
        self.song_list_container.setVisible(False)
        song_list_outer = QVBoxLayout(self.song_list_container)
        song_list_outer.setContentsMargins(8, 8, 8, 8)
        song_list_outer.setSpacing(4)

        # Select all / Deselect all buttons
        select_btns_row = QHBoxLayout()
        btn_select_all = QPushButton(t("btn_select_all"), page)
        btn_select_all.setFixedHeight(34)
        btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select_all.clicked.connect(lambda: self.toggle_all_songs(True))
        select_btns_row.addWidget(btn_select_all)
        btn_deselect_all = QPushButton(t("btn_deselect_all"), page)
        btn_deselect_all.setFixedHeight(34)
        btn_deselect_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_deselect_all.clicked.connect(lambda: self.toggle_all_songs(False))
        select_btns_row.addWidget(btn_deselect_all)
        select_btns_row.addStretch()
        song_list_outer.addLayout(select_btns_row)

        self.song_list_scroll = QScrollArea(page)
        self.song_list_scroll.setWidgetResizable(True)
        self.song_list_scroll.setMinimumHeight(80)
        self.song_list_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.song_list_scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Managed globally by styles.py
        
        self.song_list_widget = QWidget(page)
        self.song_list_widget.setStyleSheet("background: transparent;")
        self.song_list_layout = QVBoxLayout(self.song_list_widget)
        self.song_list_layout.setContentsMargins(0, 0, 0, 0)
        self.song_list_layout.setSpacing(4)
        self.song_list_layout.addStretch()
        
        self.song_list_scroll.setWidget(self.song_list_widget)
        self.song_list_scroll.viewport().setStyleSheet("background: transparent;")
        song_list_outer.addWidget(self.song_list_scroll)

        media_layout.addWidget(self.song_list_container)

        # Download Path + Action row (compact)
        lbl_save = QLabel(t("lbl_save_folder"), page)
        lbl_save.setStyleSheet("margin-top: 4px;")
        media_layout.addWidget(lbl_save)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.txt_download_dir = QLineEdit(self.config.get("download_dir"), page)
        self.txt_download_dir.setReadOnly(True)
        action_row.addWidget(self.txt_download_dir, 1)
        self.btn_browse = QPushButton(t("btn_select"), page)
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.clicked.connect(self.browse_download_folder)
        action_row.addWidget(self.btn_browse)
        self.btn_download = QPushButton(t("btn_download_now"), page)
        self.btn_download.setObjectName("btn_primary")
        self.btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download.setMinimumHeight(42)
        self.btn_download.clicked.connect(self.start_download)
        action_row.addWidget(self.btn_download)
        media_layout.addLayout(action_row)

        layout.addWidget(self.media_info_card, 1)  # stretch=1 to fill space

        # Group 3: Progress Card (Hidden by default)
        self.progress_card = QGroupBox(t("group_progress"), page)
        self.progress_card.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_card)
        progress_layout.setSpacing(10)

        self.lbl_progress_title = QLabel(t("lbl_downloading"), page)
        self.lbl_progress_title.setStyleSheet("font-weight: 600;")
        self.lbl_progress_title.setWordWrap(True)
        progress_layout.addWidget(self.lbl_progress_title)

        self.progress_bar = QProgressBar(page)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        stats_row = QHBoxLayout()
        self.lbl_progress_speed = QLabel(t("lbl_speed"), page)
        stats_row.addWidget(self.lbl_progress_speed)

        self.lbl_progress_eta = QLabel(t("lbl_eta"), page)
        stats_row.addWidget(self.lbl_progress_eta)

        self.lbl_progress_size = QLabel(t("lbl_size"), page)
        stats_row.addWidget(self.lbl_progress_size)
        
        stats_row.addStretch()
        progress_layout.addLayout(stats_row)

        self.btn_cancel_download = QPushButton(t("btn_cancel"), page)
        self.btn_cancel_download.setObjectName("btn_danger")
        self.btn_cancel_download.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel_download.clicked.connect(self.cancel_download)
        progress_layout.addWidget(self.btn_cancel_download)

        layout.addWidget(self.progress_card)

        scroll.setWidget(page)
        self.pages.addWidget(scroll)

    def create_history_page(self):
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel(t("lbl_history_desc"), page))
        header_row.addStretch()
        
        self.btn_clear_history = QPushButton(t("btn_clear_history"), page)
        self.btn_clear_history.setObjectName("btn_danger")
        self.btn_clear_history.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_history.clicked.connect(self.clear_all_history)
        header_row.addWidget(self.btn_clear_history)
        
        layout.addLayout(header_row)

        # Scrollable area for cards
        self.history_scroll = QScrollArea(page)
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll.setFrameShape(QFrame.Shape.NoFrame)
        # Managed globally by styles.py

        self.history_container = QWidget(self.history_scroll)
        self.history_list_layout = QVBoxLayout(self.history_container)
        self.history_list_layout.setContentsMargins(0, 0, 0, 0)
        self.history_list_layout.setSpacing(10)
        self.history_list_layout.addStretch() # Push items to top

        self.history_scroll.setWidget(self.history_container)
        layout.addWidget(self.history_scroll)

        # Empty history label
        self.lbl_empty_history = QLabel(t("lbl_empty_history"), page)
        self.lbl_empty_history.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty_history.setStyleSheet("color: #888888; font-size: 14px; margin-top: 50px;")
        layout.addWidget(self.lbl_empty_history)

        self.pages.addWidget(page)
        
        # Populate initially
        self.refresh_history_ui()

    def create_settings_page(self):
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        # Group 1: General Configuration
        general_group = QGroupBox(t("group_general"), page)
        general_layout = QVBoxLayout(general_group)
        general_layout.setSpacing(12)

        # Default folder configuration
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel(t("lbl_default_folder"), page))
        self.txt_settings_dir = QLineEdit(self.config.get("download_dir"), page)
        self.txt_settings_dir.setReadOnly(True)
        folder_layout.addWidget(self.txt_settings_dir)
        btn_settings_browse = QPushButton(t("btn_select_folder"), page)
        btn_settings_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings_browse.clicked.connect(self.change_settings_download_folder)
        folder_layout.addWidget(btn_settings_browse)
        general_layout.addLayout(folder_layout)

        # Playlist configuration row
        playlist_layout = QHBoxLayout()
        self.chk_download_playlist = QCheckBox(t("lbl_download_playlist"), page)
        self.chk_download_playlist.setChecked(self.config.get("download_playlist", False))
        playlist_layout.addWidget(self.chk_download_playlist)
        
        playlist_layout.addWidget(QLabel(t("lbl_max_playlist_items"), page))
        self.spin_max_playlist_items = QSpinBox(page)
        self.spin_max_playlist_items.setRange(1, 100)
        self.spin_max_playlist_items.setValue(self.config.get("max_playlist_items", 5))
        self.spin_max_playlist_items.setFixedWidth(120)
        playlist_layout.addWidget(self.spin_max_playlist_items)
        playlist_layout.addStretch()
        general_layout.addLayout(playlist_layout)

        # Connect auto-save signals
        self.chk_download_playlist.stateChanged.connect(self.auto_save_playlist_settings)
        self.spin_max_playlist_items.valueChanged.connect(self.auto_save_playlist_settings)

        # Language Selection row
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel(t("lbl_language"), page))
        self.cbo_language = QComboBox(page)
        self.cbo_language.addItem("English", "en")
        self.cbo_language.addItem("Tiếng Việt", "vi")
        self.cbo_language.setCurrentIndex(self.cbo_language.findData(self.config.get("language", "en")))
        lang_layout.addWidget(self.cbo_language)
        
        btn_save_lang = QPushButton(t("btn_save_language"), page)
        btn_save_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_lang.clicked.connect(self.save_language_settings)
        lang_layout.addWidget(btn_save_lang)
        general_layout.addLayout(lang_layout)

        layout.addWidget(general_group)

        # Group 2: Facebook Cookies Setup (For private video downloading)
        cookies_group = QGroupBox(t("group_cookies"), page)
        cookies_layout = QVBoxLayout(cookies_group)
        cookies_layout.setSpacing(12)

        cookies_info = QLabel(t("cookies_desc"), page)
        cookies_info.setStyleSheet("color: #888888; font-size: 12px;")
        cookies_layout.addWidget(cookies_info)

        source_row = QHBoxLayout()
        source_row.addWidget(QLabel(t("lbl_cookies_source"), page))
        self.cbo_cookies_source = QComboBox(page)
        self.cbo_cookies_source.addItem(t("cookies_none"), "none")
        self.cbo_cookies_source.addItem(t("cookies_chrome"), "browser_chrome")
        self.cbo_cookies_source.addItem(t("cookies_firefox"), "browser_firefox")
        self.cbo_cookies_source.addItem(t("cookies_edge"), "browser_edge")
        self.cbo_cookies_source.addItem(t("cookies_file"), "file")
        self.cbo_cookies_source.currentTextChanged.connect(self.on_cookies_source_changed)
        source_row.addWidget(self.cbo_cookies_source)
        cookies_layout.addLayout(source_row)

        # Cookies file selection row
        self.cookies_file_row = QHBoxLayout()
        self.cookies_file_row.addWidget(QLabel(t("lbl_cookies_path"), page))
        self.txt_cookies_path = QLineEdit(self.config.get("cookies_file_path"), page)
        self.cookies_file_row.addWidget(self.txt_cookies_path)
        self.btn_cookies_browse = QPushButton(t("btn_select_file"), page)
        self.btn_cookies_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cookies_browse.clicked.connect(self.browse_cookies_file)
        self.cookies_file_row.addWidget(self.btn_cookies_browse)
        cookies_layout.addLayout(self.cookies_file_row)
        
        # Initially hide file selection if source is not 'file'
        self.on_cookies_source_changed(self.config.get("cookies_source"))
        self.cbo_cookies_source.setCurrentIndex(self.cbo_cookies_source.findData(self.config.get("cookies_source")))

        # Save cookies settings button
        btn_save_cookies = QPushButton(t("btn_save_cookies"), page)
        btn_save_cookies.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_cookies.clicked.connect(self.save_cookies_settings)
        cookies_layout.addWidget(btn_save_cookies)

        layout.addWidget(cookies_group)

        # Group 3: FFmpeg Portable Downloader
        ffmpeg_group = QGroupBox(t("group_ffmpeg"), page)
        ffmpeg_layout = QVBoxLayout(ffmpeg_group)
        ffmpeg_layout.setSpacing(10)

        self.lbl_ffmpeg_status = QLabel(t("lbl_ffmpeg_checking"), page)
        self.lbl_ffmpeg_status.setStyleSheet("font-weight: 600;")
        ffmpeg_layout.addWidget(self.lbl_ffmpeg_status)

        self.btn_download_ffmpeg = QPushButton(t("btn_download_ffmpeg"), page)
        self.btn_download_ffmpeg.setObjectName("btn_primary")
        self.btn_download_ffmpeg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_download_ffmpeg.clicked.connect(self.start_ffmpeg_download)
        ffmpeg_layout.addWidget(self.btn_download_ffmpeg)

        self.ffmpeg_progress_bar = QProgressBar(page)
        self.ffmpeg_progress_bar.setValue(0)
        self.ffmpeg_progress_bar.setVisible(False)
        ffmpeg_layout.addWidget(self.ffmpeg_progress_bar)

        layout.addWidget(ffmpeg_group)
        layout.addStretch()

        self.pages.addWidget(page)
        
        # Check ffmpeg status on load
        self.check_ffmpeg_status()

    # --- UI INTERACTION LOGIC ---

    @Slot(int)
    def on_tab_changed(self, index: int):
        self.pages.setCurrentIndex(index)
        titles = [t("title_download"), t("title_history"), t("title_settings"), t("title_about")]
        if index < len(titles):
            self.page_title.setText(titles[index])
        
        # Refresh history when switching to history page
        if index == 1:
            self.refresh_history_ui()

    def toggle_theme(self):
        current_theme = self.config.get("theme", "dark")
        new_theme = "light" if current_theme == "dark" else "dark"
        self.config["theme"] = new_theme
        save_config(self.config)
        self.apply_theme(new_theme)

    def apply_theme(self, theme: str):
        if theme == "dark":
            self.setStyleSheet(DARK_STYLE)
            self.btn_theme.setText("☀️ Light Mode")
        else:
            self.setStyleSheet(LIGHT_STYLE)
            self.btn_theme.setText("🌙 Dark Mode")

    @Slot(str)
    def on_cookies_source_changed(self, source_text: str):
        # We need to find the data value since source_text could be the display name
        data_val = source_text
        index = self.cbo_cookies_source.findText(source_text)
        if index >= 0:
            data_val = self.cbo_cookies_source.itemData(index)
            
        is_file = data_val == "file"
        for i in range(self.cookies_file_row.count()):
            widget = self.cookies_file_row.itemAt(i).widget()
            if widget:
                widget.setVisible(is_file)

    def browse_download_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục tải về", self.txt_download_dir.text())
        if folder:
            self.txt_download_dir.setText(folder)
            self.config["download_dir"] = folder
            save_config(self.config)
            self.txt_settings_dir.setText(folder)

    def change_settings_download_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục tải về mặc định", self.txt_settings_dir.text())
        if folder:
            self.txt_settings_dir.setText(folder)
            self.txt_download_dir.setText(folder)
            self.config["download_dir"] = folder
            save_config(self.config)

    def browse_cookies_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn file cookies.txt", "", "Text Files (*.txt)")
        if file_path:
            self.txt_cookies_path.setText(file_path)

    def save_cookies_settings(self):
        source = self.cbo_cookies_source.currentData()
        path = self.txt_cookies_path.text()
        
        self.config["cookies_source"] = source
        self.config["cookies_file_path"] = path
        save_config(self.config)
        
        QMessageBox.information(self, "Cấu hình Cookies", "Đã lưu cài đặt Cookies thành công!")

    def save_language_settings(self):
        lang = self.cbo_language.currentData()
        self.config["language"] = lang
        self.config["download_playlist"] = self.chk_download_playlist.isChecked()
        self.config["max_playlist_items"] = self.spin_max_playlist_items.value()
        save_config(self.config)
        QMessageBox.information(self, t("title_settings"), t("msg_lang_saved"))

    def auto_save_playlist_settings(self):
        self.config["download_playlist"] = self.chk_download_playlist.isChecked()
        self.config["max_playlist_items"] = self.spin_max_playlist_items.value()
        save_config(self.config)

    # --- PORTABLE FFMPEG DOWNLOAD LOGIC ---

    def check_ffmpeg_status(self):
        ffmpeg_path = get_ffmpeg_path()
        if ffmpeg_path:
            self.lbl_ffmpeg_status.setText(t("msg_ffmpeg_found").format(name=os.path.basename(ffmpeg_path)))
            self.lbl_ffmpeg_status.setStyleSheet("color: #107c41; font-weight: 600;")
            self.btn_download_ffmpeg.setVisible(False)
            self.ffmpeg_progress_bar.setVisible(False)
        else:
            self.lbl_ffmpeg_status.setText(t("msg_ffmpeg_missing"))
            self.lbl_ffmpeg_status.setStyleSheet("color: #d83b01; font-weight: 600;")
            self.btn_download_ffmpeg.setVisible(True)

    def start_ffmpeg_download(self):
        self.btn_download_ffmpeg.setEnabled(False)
        self.ffmpeg_progress_bar.setVisible(True)
        self.ffmpeg_progress_bar.setValue(0)
        
        # Create a tiny Thread subclass to download FFmpeg in background
        class FFmpegDownloader(QThread):
            progress_updated = Signal(float, str)
            finished = Signal(bool)
            
            def run(self):
                success = download_ffmpeg(self.progress_callback)
                self.finished.emit(success)
                
            def progress_callback(self, progress: float, msg: str):
                self.progress_updated.emit(progress, msg)

        self.ffmpeg_download_thread = FFmpegDownloader(self)
        self.ffmpeg_download_thread.progress_updated.connect(self.on_ffmpeg_download_progress)
        self.ffmpeg_download_thread.finished.connect(self.on_ffmpeg_download_finished)
        self.ffmpeg_download_thread.start()

    def on_ffmpeg_download_progress(self, progress: float, msg: str):
        if progress >= 0:
            self.ffmpeg_progress_bar.setValue(int(progress * 100))
            self.lbl_ffmpeg_status.setText(msg)
            self.lbl_ffmpeg_status.setStyleSheet("color: #7C4DFF;")
        else:
            self.lbl_ffmpeg_status.setText(msg)
            self.lbl_ffmpeg_status.setStyleSheet("color: #d83b01;")

    def on_ffmpeg_download_finished(self, success: bool):
        self.btn_download_ffmpeg.setEnabled(True)
        if success:
            self.ffmpeg_progress_bar.setVisible(False)
            self.check_ffmpeg_status()
            QMessageBox.information(self, "Tải FFmpeg", "Tải xuống và cài đặt FFmpeg thành công!")
        else:
            self.btn_download_ffmpeg.setVisible(True)
            QMessageBox.critical(self, "Tải FFmpeg", "Không thể tải xuống FFmpeg. Vui lòng kiểm tra kết nối mạng hoặc thử lại sau.")

    # --- CLIPBOARD SENSING LOGIC ---

    def check_clipboard_on_start(self):
        # Scan clipboard on startup to see if facebook/youtube/tiktok link is there
        text = self.clipboard.text().strip()
        if self.is_supported_url(text):
            self.txt_url.setText(text)
            self.lbl_input_tip.setText("💡 Phát hiện liên kết hỗ trợ trong Clipboard, đã tự động dán!")

    def on_clipboard_changed(self):
        text = self.clipboard.text().strip()
        if self.is_supported_url(text):
            self.lbl_input_tip.setText("💡 Clipboard có liên kết mới! Click 'Dán link' hoặc dán trực tiếp.")

    def paste_from_clipboard(self):
        text = self.clipboard.text().strip()
        if not text:
            self.lbl_input_tip.setText("⚠️ Clipboard trống! Hãy sao chép link trước.")
            return
        self.txt_url.setText(text)
        if self.is_supported_url(text):
            self.lbl_input_tip.setText("✅ Đã dán link hỗ trợ thành công!")
        else:
            self.lbl_input_tip.setText("⚠️ Đã dán, nhưng link có thể không thuộc nền tảng hỗ trợ.")

    def is_supported_url(self, url: str) -> bool:
        url = url.lower()
        supported_domains = ["facebook.com", "fb.watch", "fb.gg", "youtube.com", "youtu.be", "tiktok.com"]
        return any(domain in url for domain in supported_domains)

    def on_url_input_changed(self, text: str):
        # Reset analyzed card if input changes meaningfully
        if self.analyzed_metadata and text != self.analyzed_metadata.get("url"):
            self.media_info_card.setVisible(False)
            self.analyzed_metadata = None

    # --- ANALYZE URL LOGIC ---

    def start_analysis(self):
        # If already running, act as Stop button
        if hasattr(self, "analyze_worker") and self.analyze_worker and self.analyze_worker.isRunning():
            self.stop_analysis()
            return

        url = self.txt_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Lỗi phân tích", "Vui lòng nhập đường dẫn Video trước!")
            return
            
        if not self.is_supported_url(url):
            reply = QMessageBox.question(
                self, "Xác nhận liên kết", 
                "Đường dẫn có vẻ không thuộc các nền tảng hỗ trợ chính thức (FB, YT, TikTok). Bạn vẫn muốn tiếp tục phân tích?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Enable button as Stop button during analysis
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("🛑 Dừng quét")
        self.media_info_card.setVisible(False)
        self.lbl_input_tip.setText("Đang phân tích liên kết ngầm, vui lòng đợi...")

        # Build Worker - filter history by current media type for smart duplicate detection
        current_media_type = "audio" if self.cbo_format.currentData() == "audio" else "video"
        history_titles = [
            item.get("title", "") for item in self.history
            if item.get("media_type") == current_media_type
        ]
        self.analyze_worker = AnalyzeWorker(
            url=url,
            cookies_source=self.config.get("cookies_source", "none"),
            cookies_file_path=self.config.get("cookies_file_path", ""),
            noplaylist=not self.config.get("download_playlist", False),
            playlist_items=f"1-{self.config.get('max_playlist_items', 5)}",
            download_dir=self.txt_download_dir.text(),
            format_type=self.cbo_format.currentData(),
            history_titles=history_titles
        )
        self.analyze_worker.finished.connect(self.on_analysis_finished)
        self.analyze_worker.start()

    def stop_analysis(self):
        if hasattr(self, "analyze_worker") and self.analyze_worker:
            self.analyze_worker.terminate()
            self.analyze_worker.wait()
            self.analyze_worker = None
            
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("🔍 Phân tích")
        self.lbl_input_tip.setText("Đã dừng quét theo yêu cầu.")

    def on_analysis_finished(self, result: dict):
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("🔍 Phân tích")

        if result.get("success"):
            self.analyzed_metadata = result
            self.analyzed_metadata["url"] = self.txt_url.text().strip()
            
            # Check if all items already downloaded
            if result.get("all_already_downloaded"):
                self.media_info_card.setVisible(False)
                self.analyzed_metadata = None
                
                is_audio = self.cbo_format.currentData() == "audio"
                media_label = "bài hát" if is_audio else "video"
                
                if result.get("entry_titles"):
                    self.lbl_input_tip.setText(f"✅ Tất cả {media_label} trong danh sách phát này đã được tải về rồi!")
                    QMessageBox.information(
                        self, "Đã tải hết",
                        f"🎉 Tất cả {media_label} trong danh sách phát này đã có trong thư mục tải về hoặc lịch sử tải.\n\n"
                        "Hãy thử dán một liên kết khác để tải thêm nội dung mới!"
                    )
                else:
                    self.lbl_input_tip.setText(f"✅ {media_label.capitalize()} này đã được tải về rồi!")
                    QMessageBox.information(
                        self, "Đã tải về",
                        f"🎉 {media_label.capitalize()} này đã có trong thư mục tải về hoặc lịch sử tải.\n\n"
                        f"Tiêu đề: {result.get('title')}\n\n"
                        "Bạn có thể phát file từ tab Lịch sử hoặc dán liên kết khác để tải."
                    )
                return
            
            # Display analyzed card
            self.media_info_card.setVisible(True)
            self.lbl_media_title.setText(result.get("title", "Video Facebook"))
            self.lbl_media_uploader.setText(f"Người đăng: {result.get('uploader', 'Facebook User')}")
            self.lbl_media_duration.setText(f"Thời lượng: {format_seconds(result.get('duration', 0))}")
            
            # Populate song list if playlist
            entry_titles = result.get("entry_titles", [])
            self.song_checkboxes = []
            # Clear old checkboxes
            for i in reversed(range(self.song_list_layout.count())):
                item = self.song_list_layout.itemAt(i)
                w = item.widget()
                if w:
                    w.deleteLater()
                    
            if entry_titles:
                self.song_list_container.setVisible(True)
                for i, entry in enumerate(entry_titles):
                    cb = QCheckBox(f"{i+1}. {entry['title']}")
                    cb.setChecked(True)
                    cb.setProperty("playlist_index", entry["index"])
                    self.song_list_layout.insertWidget(i, cb)
                    self.song_checkboxes.append(cb)
                self.lbl_input_tip.setText(f"✅ Tìm thấy {len(entry_titles)} bài mới! Bỏ chọn bài không cần, rồi nhấn Tải ngay.")
            else:
                self.song_list_container.setVisible(False)
                self.lbl_input_tip.setText("✅ Đã phân tích xong! Nhấn Tải ngay để tải về.")
        else:
            self.lbl_input_tip.setText("❌ Không thể phân tích link. Có thể link bị lỗi hoặc cần cấu hình Cookies đăng nhập.")
            error_msg = result.get("error", "Lỗi không xác định")
            # Truncate long yt-dlp errors to keep dialog readable
            if len(error_msg) > 300:
                error_msg = error_msg[:300] + "..."
            QMessageBox.critical(
                self, "Lỗi phân tích link", 
                f"Không thể phân tích đường dẫn này.\n\nChi tiết lỗi:\n{error_msg}\n\nMẹo: Hãy thử cấu hình Cookies lấy từ Chrome/Edge trong tab Cấu hình nếu video thuộc Group kín hoặc Fanpage giới hạn."
            )

    # --- DOWNLOAD MEDIA LOGIC ---

    def toggle_all_songs(self, checked: bool):
        for cb in getattr(self, 'song_checkboxes', []):
            cb.setChecked(checked)

    def start_download(self):
        if not self.analyzed_metadata:
            QMessageBox.warning(self, "Tải xuống", "Vui lòng phân tích link thành công trước khi tải!")
            return

        url = self.analyzed_metadata.get("url")
        title = self.analyzed_metadata.get("title")
        format_type = self.cbo_format.currentData()
        download_dir = self.txt_download_dir.text()

        # Check FFmpeg warning if HD is chosen
        if format_type == "hd" and not get_ffmpeg_path():
            reply = QMessageBox.question(
                self, "Thiếu thư viện ghép nối HD",
                "Hệ thống chưa cài đặt thư viện ghép nối video HD (FFmpeg).\n"
                "Nếu tiếp tục, video tải về sẽ là phiên bản chất lượng thường hoặc có thể thiếu âm thanh.\n\n"
                "Bạn có muốn chuyển sang tải chất lượng thường (SD) không?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.cbo_format.setCurrentIndex(1) # Change to SD
                format_type = "sd"

        # Lock UI
        self.btn_download.setEnabled(False)
        self.btn_analyze.setEnabled(False)
        self.btn_paste.setEnabled(False)
        self.txt_url.setEnabled(False)
        self.sidebar.setEnabled(False) # Prevent switching tabs during download

        # Display progress card
        self.progress_card.setVisible(True)
        self.lbl_progress_title.setText(f"Đang tải: {title}")
        self.progress_bar.setValue(0)
        self.lbl_progress_speed.setText("Tốc độ: Đang chuẩn bị...")
        self.lbl_progress_eta.setText("Còn lại: --:--")
        self.lbl_progress_size.setText("Dung lượng: -- / --")

        # Build smart playlist_items from user-selected checkboxes
        checked_indices = []
        for cb in getattr(self, 'song_checkboxes', []):
            if cb.isChecked():
                checked_indices.append(str(cb.property("playlist_index")))
        
        if checked_indices:
            smart_playlist_items = ",".join(checked_indices)
        else:
            smart_playlist_items = self.analyzed_metadata.get(
                "playlist_items", f"1-{self.config.get('max_playlist_items', 5)}"
            )
        self.download_worker = DownloadWorker(
            url=url,
            download_dir=download_dir,
            cookies_source=self.config.get("cookies_source", "none"),
            cookies_file_path=self.config.get("cookies_file_path", ""),
            format_type=format_type,
            noplaylist=not self.config.get("download_playlist", False),
            playlist_items=smart_playlist_items
        )
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.start()

    def on_download_progress(self, progress_info: dict):
        percent = progress_info.get("percent", 0.0)
        self.progress_bar.setValue(int(percent))
        
        status = progress_info.get("status")
        if status == "postprocessing":
            self.lbl_progress_speed.setText(progress_info.get('speed', ''))
            self.lbl_progress_eta.setText("Còn lại: Đang xử lý hậu kỳ...")
            self.lbl_progress_size.setText("Dung lượng: Đang hoàn tất...")
        else:
            self.lbl_progress_speed.setText(f"Tốc độ: {progress_info.get('speed', '-- KB/s')}")
            self.lbl_progress_eta.setText(f"Còn lại: {progress_info.get('eta', '--:--')}")
            
            downloaded = progress_info.get("downloaded", "--")
            total = progress_info.get("total", "--")
            self.lbl_progress_size.setText(f"Dung lượng: {downloaded} / {total}")

    def on_download_finished(self, result: dict):
        # Unlock UI
        self.btn_download.setEnabled(True)
        self.btn_analyze.setEnabled(True)
        self.btn_paste.setEnabled(True)
        self.txt_url.setEnabled(True)
        self.sidebar.setEnabled(True)
        self.progress_card.setVisible(False)

        if result.get("success"):
            # Success! Add to history
            downloaded_files = result.get("downloaded_files", [])
            if downloaded_files:
                for file_info in downloaded_files:
                    add_to_history(
                        url=self.analyzed_metadata.get("url"),
                        title=file_info.get("title", "Video Facebook"),
                        file_path=file_info.get("filepath", ""),
                        file_size=file_info.get("filesize", 0),
                        media_type="audio" if self.cbo_format.currentData() == "audio" else "video"
                    )
            else:
                add_to_history(
                    url=self.analyzed_metadata.get("url"),
                    title=result.get("title", "Video Facebook"),
                    file_path=result.get("filepath", ""),
                    file_size=result.get("filesize", 0),
                    media_type="audio" if self.cbo_format.currentData() == "audio" else "video"
                )
            # Reload history memory
            self.history = load_history()
            
            # Create a premium interactive QMessageBox
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Tải thành công 🎉")
            
            is_audio = self.cbo_format.currentData() == "audio"
            play_label = "▶️ Phát Nhạc" if is_audio else "▶️ Phát Video"
            
            msg_box.setText(
                f"<b>Đã tải thành công file về máy!</b><br><br>"
                f"<b>Tiêu đề:</b> {result.get('title')}<br>"
                f"<b>Đường dẫn:</b> {result.get('filepath')}"
            )
            
            play_btn = msg_box.addButton(play_label, QMessageBox.ButtonRole.ActionRole)
            folder_btn = msg_box.addButton("📁 Mở Thư Mục", QMessageBox.ButtonRole.ActionRole)
            ok_btn = msg_box.addButton("Đóng (OK)", QMessageBox.ButtonRole.AcceptRole)
            
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.exec()
            
            clicked_btn = msg_box.clickedButton()
            if clicked_btn == play_btn:
                try:
                    open_path(result.get("filepath"))
                except Exception as e:
                    QMessageBox.warning(self, "Lỗi mở file", f"Không thể mở file trực tiếp: {str(e)}")
            elif clicked_btn == folder_btn:
                try:
                    reveal_in_file_manager(result.get("filepath"))
                except Exception as e:
                    QMessageBox.warning(self, "Lỗi mở thư mục", f"Không thể mở thư mục: {str(e)}")
            # Clear fields for next download
            self.txt_url.clear()
            self.media_info_card.setVisible(False)
            self.analyzed_metadata = None
        else:
            QMessageBox.critical(
                self, "Lỗi tải video", 
                f"Tải video thất bại.\n\nChi tiết lỗi:\n{result.get('error', 'Lỗi không xác định')}"
            )

    def cancel_download(self):
        if self.download_worker:
            self.download_worker.cancel()
            self.download_worker.terminate()
            self.download_worker.wait()
            self.download_worker = None
            
            # Unlock UI
            self.btn_download.setEnabled(True)
            self.btn_analyze.setEnabled(True)
            self.btn_paste.setEnabled(True)
            self.txt_url.setEnabled(True)
            self.sidebar.setEnabled(True)
            self.progress_card.setVisible(False)
            
            QMessageBox.warning(self, "Hủy tải", "Tác vụ tải đã bị hủy bởi người dùng.")

    # --- HISTORY MANAGEMENT LOGIC ---

    def refresh_history_ui(self):
        # Clear existing widgets from list layout (excluding the stretch)
        for i in reversed(range(self.history_list_layout.count())):
            item = self.history_list_layout.itemAt(i)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not self.history:
            self.lbl_empty_history.setVisible(True)
            self.btn_clear_history.setVisible(False)
            self.history_scroll.setVisible(False)
        else:
            self.lbl_empty_history.setVisible(False)
            self.btn_clear_history.setVisible(True)
            self.history_scroll.setVisible(True)

            # Insert cards at top
            for item in self.history:
                card = HistoryCard(item, self.history_container)
                self.history_list_layout.insertWidget(0, card)

    def clear_all_history(self):
        reply = QMessageBox.question(
            self, "Xóa lịch sử", "Bạn có chắc chắn muốn xóa toàn bộ lịch sử danh sách đã tải xuống không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history = []
            save_history([])
            self.refresh_history_ui()
            QMessageBox.information(self, "Lịch sử", "Đã xóa toàn bộ lịch sử thành công.")

    def create_about_page(self):
        # Scroll area for long About page and advertisements
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        # Managed globally by styles.py

        page = QWidget(scroll)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        about_group = QGroupBox("Thông tin phần mềm & Tác giả", page)
        about_layout = QVBoxLayout(about_group)
        about_layout.setSpacing(15)
        about_layout.setContentsMargins(20, 20, 20, 20)

        # App Logo/Name
        logo_lbl = QLabel(page)
        logo_path = get_resource_path("src/ui/assets/icon.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(scaled_pixmap)
            logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            about_layout.addWidget(logo_lbl)

        title_lbl = QLabel("AzHome Media Downloader", page)
        title_lbl.setStyleSheet("font-size: 26px; font-weight: bold; color: #7C4DFF;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(title_lbl)

        version_lbl = QLabel("Phiên bản v1.0.0 (Stable)", page)
        version_lbl.setStyleSheet("color: #888888; font-size: 15px;")
        version_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        about_layout.addWidget(version_lbl)

        # Decorative line
        line = QFrame(page)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #2d2d2d; max-height: 1px;")
        about_layout.addWidget(line)

        # Introduction description
        intro_text = QLabel(
            "Phần mềm được phát triển bởi đội ngũ <b>AzHome</b>, giúp người dùng tải các nội dung "
            "video, reels, âm thanh chất lượng cao nhất (HD) từ các nền tảng lớn như <b>Facebook, YouTube, TikTok</b> một cách nhanh chóng "
            "và hoàn toàn miễn phí.<br><br>"
            "Chúng tôi cam kết bảo mật thông tin tài khoản và mang lại trải nghiệm tối ưu nhất "
            "cho người sử dụng trên Windows, macOS và Linux.", page
        )
        intro_text.setStyleSheet("font-size: 15px;")
        intro_text.setWordWrap(True)
        about_layout.addWidget(intro_text)

        # Usage Guide Section
        guide_line = QFrame(page)
        guide_line.setFrameShape(QFrame.Shape.HLine)
        guide_line.setFrameShadow(QFrame.Shadow.Sunken)
        guide_line.setStyleSheet("background-color: #2d2d2d; max-height: 1px;")
        about_layout.addWidget(guide_line)

        guide_title = QLabel("📖 Hướng dẫn sử dụng", page)
        guide_title.setStyleSheet("font-weight: bold; font-size: 18px; color: #7C4DFF; margin-top: 5px;")
        about_layout.addWidget(guide_title)

        guide_text = QLabel(
            "<b>Bước 1:</b> Sao chép (Copy) đường dẫn video/nhạc từ Facebook, YouTube hoặc TikTok.<br>"
            "<b>Bước 2:</b> Dán link vào ô nhập liệu (hoặc nhấn nút <b>📋 Dán link</b>).<br>"
            "<b>Bước 3:</b> Chọn <b>Định dạng tải về</b> (Video HD, SD, hoặc Âm thanh MP3).<br>"
            "<b>Bước 4:</b> Nhấn nút <b>🔍 Phân tích</b> — phần mềm sẽ quét và hiển thị thông tin.<br>"
            "<b>Bước 5:</b> Xem danh sách bài hát (nếu là playlist), bỏ chọn bài không cần.<br>"
            "<b>Bước 6:</b> Nhấn <b>⬇️ Tải ngay</b> và chờ hoàn thành!<br><br>"
            "<b>💡 Tính năng thông minh:</b><br>"
            "• <b>Lọc trùng tự động:</b> Bài hát đã tải sẽ không tải lại, tự bù bài mới cho đủ số lượng.<br>"
            "• <b>Tải danh sách phát:</b> Bật trong tab <b>⚙️ Cấu hình</b>, đặt số lượng tối đa và tải hàng loạt.<br>"
            "• <b>Xem trước danh sách:</b> Bỏ chọn bài không muốn tải trước khi bấm Tải.<br>"
            "• <b>FFmpeg tích hợp:</b> Tải FFmpeg trong tab Cấu hình để ghép video HD và chuyển đổi MP3 chất lượng cao.", page
        )
        guide_text.setStyleSheet("font-size: 15px;")
        guide_text.setWordWrap(True)
        about_layout.addWidget(guide_text)

        # Author Card
        author_card = QFrame(page)
        author_card.setObjectName("author_card")
        author_layout = QVBoxLayout(author_card)
        author_layout.setSpacing(8)
        author_layout.setContentsMargins(15, 15, 15, 15)

        author_lbl = QLabel("<b>Tác giả:</b> AzHome Team", page)
        author_lbl.setStyleSheet("font-size: 15px;")
        author_layout.addWidget(author_lbl)

        web_row = QHBoxLayout()
        web_title_lbl = QLabel("<b>Website chính thức:</b>", page)
        web_title_lbl.setStyleSheet("font-size: 15px;")
        web_row.addWidget(web_title_lbl)

        web_link = QPushButton("azhome.top/gioi-thieu 🌐", page)
        web_link.setFlat(True)
        web_link.setCursor(Qt.CursorShape.PointingHandCursor)
        web_link.setStyleSheet("color: #7C4DFF; text-decoration: underline; font-weight: bold; text-align: left; background: transparent; border: none; padding: 0;")
        web_link.clicked.connect(self.open_author_website)
        web_row.addWidget(web_link)
        web_row.addStretch()
        author_layout.addLayout(web_row)

        about_layout.addWidget(author_card)

        # Decorative line for Advertisement
        line_ads = QFrame(page)
        line_ads.setFrameShape(QFrame.Shape.HLine)
        line_ads.setFrameShadow(QFrame.Shadow.Sunken)
        line_ads.setStyleSheet("background-color: #2d2d2d; max-height: 1px; margin-top: 10px;")
        about_layout.addWidget(line_ads)

        # Advertisement for AzHome Construction Management
        ads_title = QLabel("🛠️ Hệ sinh thái Quản lý Xây dựng AzHome (Chuyển đổi số công trình)", page)
        ads_title.setStyleSheet("font-weight: bold; font-size: 16px; color: #7C4DFF; margin-top: 5px;")
        about_layout.addWidget(ads_title)

        ads_body = QLabel(
            "Ngoài các công cụ tiện ích, <b>AzHome</b> tự hào mang đến bộ giải pháp quản lý thi công công trình toàn diện:<br>"
            "• <b>Quản lý BOQ & Dự toán:</b> Tự động hóa khâu nhập liệu, quản lý và đối chiếu bảng khối lượng thầu.<br>"
            "• <b>Báo cáo sản lượng & Tiến độ:</b> Cập nhật tiến độ thi công thực tế tại công trường hàng ngày trực quan.<br>"
            "• <b>Tự động hóa hồ sơ thanh toán:</b> Đối chiếu thanh toán 3 cấp (Hạng mục -> Nhóm -> Mốc thanh toán), xuất hồ sơ tự động.<br><br>"
            "<i>Sử dụng công nghệ quản trị hiện đại giúp tối ưu hóa 30% thời gian làm việc và chi phí vận hành cho mọi dự án xây dựng của bạn.</i>", page
        )
        ads_body.setStyleSheet("font-size: 15px; color: #888888;")
        ads_body.setWordWrap(True)
        about_layout.addWidget(ads_body)
        
        # Add decorative spacer
        about_layout.addStretch()

        layout.addWidget(about_group)
        layout.addStretch()

        scroll.setWidget(page)
        self.pages.addWidget(scroll)

    def open_author_website(self):
        QDesktopServices.openUrl(QUrl("https://azhome.top/gioi-thieu"))
