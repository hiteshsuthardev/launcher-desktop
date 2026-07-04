import sys
import os
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    # Allow local imports from the project root
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    app = QApplication(sys.argv)
    app.setApplicationName("AppLauncher")
    app.setQuitOnLastWindowClosed(False)
    
    window = MainWindow()
    # Let's open it maximized to give it that console-like Big Picture feel
    window.showMaximized()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
