# Fluent Design Style Sheets for Dark and Light modes.
# Styled specifically for a premium modern Windows 11 feel.

DARK_STYLE = """
QMainWindow {
    background-color: #121212; /* Nền tối sâu hơn */
}

QWidget {
    font-family: "Segoe UI", "Segoe UI Variable", sans-serif;
    font-size: 14px;
    color: #e0e0e0;
}

/* Ép ScrollArea trong suốt để lộ nền MainWindow */
QScrollArea, QScrollArea > QWidget > QWidget {
    background: transparent;
    border: none;
}

/* Thanh cuộn (Scrollbar) tinh tế */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #333333;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #555555;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

/* Sidebar (Menu trái) */
QListWidget#sidebar {
    background-color: #18181b; /* Đậm hơn content một chút để phân tách */
    border: none;
    border-right: 1px solid #27272a;
    outline: 0;
    padding: 15px 10px;
}
QListWidget#sidebar::item {
    padding: 12px 16px;
    margin: 4px 0px;
    border-radius: 8px;
    color: #a1a1aa;
    font-size: 15px;
    font-weight: 500;
}
QListWidget#sidebar::item:hover {
    background-color: #27272a;
    color: #ffffff;
}
QListWidget#sidebar::item:selected {
    background-color: rgba(124, 77, 255, 0.15);
    border-left: 4px solid #7C4DFF;
    color: #7C4DFF;
    font-weight: bold;
}

/* Các trang nội dung */
QStackedWidget {
    background-color: #121212;
}

/* Khối GroupBox - Tạo chiều sâu 3D (Mấu chốt để hết đơn điệu) */
QGroupBox {
    background-color: #1e1e24;
    border: 1px solid #2d2d3a;
    border-radius: 12px;
    margin-top: 24px;
    padding: 20px 15px 15px 15px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 2px 10px;
    color: #9d7cff; /* Tím sáng */
    font-size: 13px;
    font-weight: bold;
    text-transform: uppercase;
}

/* Thẻ nhập liệu (Input) */
QLineEdit, QSpinBox {
    background-color: #121212;
    border: 1px solid #333340;
    border-radius: 6px;
    padding: 10px 12px;
    color: #ffffff;
}
QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #7C4DFF;
    background-color: #16161a;
}
QLineEdit:disabled { background-color: #1a1a1a; color: #555; }

/* Custom QSpinBox Buttons to prevent overlapping and match theme */
QSpinBox {
    padding-right: 36px;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #1e1e24;
    subcontrol-origin: border;
    width: 22px;
    border: none;
}
QSpinBox::up-button {
    subcontrol-position: top right;
    border-top-right-radius: 6px;
    margin-top: 1px;
    margin-right: 1px;
}
QSpinBox::down-button {
    subcontrol-position: bottom right;
    border-bottom-right-radius: 6px;
    margin-bottom: 1px;
    margin-right: 1px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #2a2a35;
}
QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
    background-color: #121212;
}
QSpinBox::up-arrow {
    image: none;
    width: 0px;
    height: 0px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-bottom: 5px solid #a1a1aa;
}
QSpinBox::down-arrow {
    image: none;
    width: 0px;
    height: 0px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #a1a1aa;
}

/* ComboBox */
QComboBox {
    background-color: #121212;
    border: 1px solid #333340;
    border-radius: 6px;
    padding: 10px 12px;
    color: #ffffff;
}
QComboBox:hover { border: 1px solid #555566; }
QComboBox::drop-down { border: none; width: 30px; }
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #a1a1aa;
    margin-top: 4px;
}
QComboBox QAbstractItemView {
    background-color: #1e1e24;
    border: 1px solid #333340;
    color: #ffffff;
    selection-background-color: #7C4DFF;
}

/* Nút bấm thường (Khắc phục lỗi mất chữ) */
QPushButton {
    background-color: #27272a;
    border: 1px solid #3f3f46;
    border-radius: 6px;
    padding: 10px 18px;
    color: #ffffff; /* Ép cứng màu chữ */
    font-weight: 600;
}
QPushButton:hover {
    background-color: #3f3f46;
    border-color: #52525b;
}
QPushButton:pressed { background-color: #18181b; }

/* Nút bấm Chính (Call to Action) */
QPushButton#btn_primary {
    background-color: #7C4DFF;
    border: 1px solid #651fff;
    color: #ffffff;
}
QPushButton#btn_primary:hover {
    background-color: #8c66ff;
    border: 1px solid #7C4DFF;
}
QPushButton#btn_primary:pressed { background-color: #5e35b1; }

/* Nút bấm Cảnh báo/Nguy hiểm */
QPushButton#btn_danger {
    background-color: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.5);
    color: #ef4444;
}
QPushButton#btn_danger:hover {
    background-color: #ef4444;
    color: #ffffff;
}

/* Labels */
QLabel#title_label { font-size: 24px; font-weight: bold; color: #ffffff; }

/* Thanh tiến trình */
QProgressBar {
    background-color: #27272a;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: #ffffff;
    height: 12px;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7C4DFF, stop:1 #4facfe);
    border-radius: 4px;
}

/* Checkbox */
QCheckBox { color: #e0e0e0; spacing: 10px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #555; background-color: #121212; }
QCheckBox::indicator:checked { background-color: #7C4DFF; border: 1px solid #7C4DFF; }

/* Thẻ Lịch sử */
QFrame#history_card {
    background-color: #1e1e24;
    border: 1px solid #2d2d3a;
    border-radius: 10px;
}
QFrame#history_card:hover { border-color: #7C4DFF; background-color: #25252d; }
"""

LIGHT_STYLE = """
QMainWindow {
    background-color: #f8fafc; /* Nền xám rất nhạt */
}

QWidget {
    font-family: "Segoe UI", "Segoe UI Variable", sans-serif;
    font-size: 14px;
    color: #0f172a;
}

QScrollArea, QScrollArea > QWidget > QWidget {
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #94a3b8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

/* Sidebar Light Mode */
QListWidget#sidebar {
    background-color: #ffffff;
    border: none;
    border-right: 1px solid #e2e8f0;
    outline: 0;
    padding: 15px 10px;
}
QListWidget#sidebar::item {
    padding: 12px 16px;
    margin: 4px 0px;
    border-radius: 8px;
    color: #64748b;
    font-size: 15px;
    font-weight: 500;
}
QListWidget#sidebar::item:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}
QListWidget#sidebar::item:selected {
    background-color: rgba(124, 77, 255, 0.1);
    border-left: 4px solid #7C4DFF;
    color: #7C4DFF;
    font-weight: bold;
}

/* Nội dung chính */
QStackedWidget { background-color: #f8fafc; }

/* Khối GroupBox - Đã chỉnh nổi bật trên nền Light */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    margin-top: 24px;
    padding: 20px 15px 15px 15px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 2px 10px;
    color: #6d28d9; /* Tím đậm */
    font-size: 13px;
    font-weight: bold;
    text-transform: uppercase;
}

/* Thẻ nhập liệu (Input) */
QLineEdit, QSpinBox {
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 10px 12px;
    color: #0f172a;
}
QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #7C4DFF;
    background-color: #ffffff;
}
QLineEdit:disabled { background-color: #f1f5f9; color: #94a3b8; }

/* Custom QSpinBox Buttons to prevent overlapping and match theme */
QSpinBox {
    padding-right: 36px;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #ffffff;
    subcontrol-origin: border;
    width: 22px;
    border: none;
    border-left: 1px solid #cbd5e1;
}
QSpinBox::up-button {
    subcontrol-position: top right;
    border-top-right-radius: 6px;
    margin-top: 1px;
    margin-right: 1px;
}
QSpinBox::down-button {
    subcontrol-position: bottom right;
    border-bottom-right-radius: 6px;
    margin-bottom: 1px;
    margin-right: 1px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #f1f5f9;
}
QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
    background-color: #cbd5e1;
}
QSpinBox::up-arrow {
    image: none;
    width: 0px;
    height: 0px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-bottom: 5px solid #64748b;
}
QSpinBox::down-arrow {
    image: none;
    width: 0px;
    height: 0px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #64748b;
}

/* ComboBox */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 10px 12px;
    color: #0f172a;
}
QComboBox:hover { border: 1px solid #94a3b8; }
QComboBox::drop-down { border: none; width: 30px; }
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #64748b;
    margin-top: 4px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    color: #0f172a;
    selection-background-color: rgba(124, 77, 255, 0.1);
    selection-color: #7C4DFF;
}

/* Nút bấm thường (Fix triệt để lỗi mất chữ) */
QPushButton {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 10px 18px;
    color: #0f172a; /* Ép chữ đen/xanh đen */
    font-weight: 600;
}
QPushButton:hover {
    background-color: #f1f5f9;
    border-color: #94a3b8;
}
QPushButton:pressed { background-color: #e2e8f0; }

/* Nút bấm Chính (Màu tím AZHome) */
QPushButton#btn_primary {
    background-color: #7C4DFF;
    border: 1px solid #651fff;
    color: #ffffff;
}
QPushButton#btn_primary:hover {
    background-color: #651fff; /* Đậm hơn khi hover */
}
QPushButton#btn_primary:pressed { background-color: #5e35b1; }

/* Nút bấm Cảnh báo */
QPushButton#btn_danger {
    background-color: #ffffff;
    border: 1px solid #fca5a5;
    color: #ef4444;
}
QPushButton#btn_danger:hover {
    background-color: #fef2f2;
    border-color: #ef4444;
}

/* Labels */
QLabel#title_label { font-size: 24px; font-weight: bold; color: #0f172a; }

/* Thanh tiến trình */
QProgressBar {
    background-color: #e2e8f0;
    border: none;
    border-radius: 4px;
    text-align: center;
    color: transparent; /* Giấu text % ở giữa cho đẹp */
    height: 12px;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7C4DFF, stop:1 #4facfe);
    border-radius: 4px;
}

/* Checkbox */
QCheckBox { color: #0f172a; spacing: 10px; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #cbd5e1; background-color: #ffffff; }
QCheckBox::indicator:checked { background-color: #7C4DFF; border: 1px solid #7C4DFF; }

/* Thẻ Lịch sử */
QFrame#history_card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
}
QFrame#history_card:hover { border-color: #7C4DFF; background-color: #f1f5f9; }
"""
