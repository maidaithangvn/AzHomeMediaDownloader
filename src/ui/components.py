import os
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from src.utils.helpers import format_bytes, open_path, reveal_in_file_manager

class HistoryCard(QFrame):
    """
    A premium card widget representing a downloaded item in the history list.
    Features modern layout, hover feedback, and quick action buttons.
    """
    # Emits file_path when an action is clicked
    open_file_requested = Signal(str)
    open_folder_requested = Signal(str)

    def __init__(self, item_data: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("history_card")
        self.item_data = item_data
        
        self.title = item_data.get("title", "Unknown Title")
        self.file_path = item_data.get("file_path", "")
        self.file_size = item_data.get("file_size", 0)
        self.download_time = item_data.get("download_time", "")
        self.media_type = item_data.get("media_type", "video")

        self.init_ui()

    def init_ui(self):
        # Layouts
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(15)

        # Media Type Icon
        self.icon_label = QLabel(self)
        self.icon_label.setFixedWidth(40)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.media_type == "video":
            self.icon_label.setText("🎥")
            self.icon_label.setStyleSheet("font-size: 24px; color: #7C4DFF;")
        else:
            self.icon_label.setText("🎵")
            self.icon_label.setStyleSheet("font-size: 24px; color: #107c41;")
        main_layout.addWidget(self.icon_label)

        # Info Layout (Title, Path/Size, Time)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        # Title Label with Tooltip
        self.title_label = QLabel(self.title, self)
        self.title_label.setStyleSheet("font-weight: 600; font-size: 14px;")
        self.title_label.setToolTip(self.title)
        self.title_label.setWordWrap(True)
        info_layout.addWidget(self.title_label)

        # Metadata Row (Size & Date)
        meta_label = QLabel(
            f"Dung lượng: {format_bytes(self.file_size)}   |   Thời gian: {self.download_time}", 
            self
        )
        meta_label.setStyleSheet("color: #888888; font-size: 12px;")
        info_layout.addWidget(meta_label)

        # Path Label
        path_label = QLabel(self.file_path, self)
        path_label.setStyleSheet("color: #777777; font-size: 11px;")
        path_label.setToolTip(self.file_path)
        info_layout.addWidget(path_label)

        main_layout.addLayout(info_layout, 1)

        # Action Buttons Layout
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)

        # "Open File" button
        self.btn_open = QPushButton("Xem File", self)
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.clicked.connect(self.on_open_file)
        actions_layout.addWidget(self.btn_open)

        # "Open Folder" button
        self.btn_folder = QPushButton("Mở Thư Mục", self)
        self.btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_folder.clicked.connect(self.on_open_folder)
        actions_layout.addWidget(self.btn_folder)

        main_layout.addLayout(actions_layout)

        # Real high-end hardware-accelerated 3D drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

    def on_open_file(self):
        if os.path.exists(self.file_path):
            try:
                open_path(self.file_path)
            except Exception as e:
                print(f"Lỗi mở file: {e}")
        self.open_file_requested.emit(self.file_path)

    def on_open_folder(self):
        if os.path.exists(self.file_path):
            try:
                reveal_in_file_manager(self.file_path)
            except Exception as e:
                print(f"Lỗi mở thư mục: {e}")
        else:
            folder = os.path.dirname(self.file_path)
            if os.path.exists(folder):
                try:
                    open_path(folder)
                except Exception as e:
                    print(f"Lỗi mở thư mục cha: {e}")
        self.open_folder_requested.emit(self.file_path)
