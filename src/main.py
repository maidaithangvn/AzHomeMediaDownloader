import sys
import os

# Add project root directory to path to prevent import errors when running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

def main():
    # Support High DPI scaling on modern 4K/2K screens
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    app.setApplicationName("FB Media Downloader")
    app.setApplicationDisplayName("FB Media Downloader")
    # Matches the .desktop file name so Linux (Wayland/X11) shows the right icon
    app.setDesktopFileName("azhome-media-downloader")

    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
