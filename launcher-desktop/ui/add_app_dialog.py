import os
import win32com.client
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QFormLayout, QComboBox)
from PySide6.QtCore import Qt, QThread, Signal

class AppScannerThread(QThread):
    apps_found = Signal(list)

    def run(self):
        import pythoncom
        pythoncom.CoInitialize()

        paths = []
        try:
            from win32com.shell import shell, shellcon
            # Common Start Menu
            paths.append(shell.SHGetFolderPath(0, shellcon.CSIDL_COMMON_PROGRAMS, None, 0))
            # User Start Menu
            paths.append(shell.SHGetFolderPath(0, shellcon.CSIDL_PROGRAMS, None, 0))
            # Common Desktop
            paths.append(shell.SHGetFolderPath(0, shellcon.CSIDL_COMMON_DESKTOPDIRECTORY, None, 0))
            # User Desktop
            paths.append(shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOPDIRECTORY, None, 0))
        except Exception:
            user_profile = os.environ.get("USERPROFILE", "")
            program_data = os.environ.get("ProgramData", "C:\\ProgramData")
            paths = [
                os.path.join(program_data, "Microsoft\\Windows\\Start Menu\\Programs"),
                os.path.join(user_profile, "AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs"),
                os.path.join(user_profile, "Desktop"),
                "C:\\Users\\Public\\Desktop"
            ]

        apps = []
        seen_paths = set()
        
        wsh = None
        try:
            wsh = win32com.client.Dispatch("WScript.Shell")
        except Exception:
            pass

        for base_path in paths:
            if not base_path or not os.path.exists(base_path):
                continue
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    filepath = os.path.join(root, file)
                    name, ext = os.path.splitext(file)
                    ext = ext.lower()

                    target_path = None
                    if ext == ".lnk" and wsh:
                        try:
                            shortcut = wsh.CreateShortCut(filepath)
                            target = shortcut.TargetPath
                            if target and os.path.exists(target) and target.lower().endswith(".exe"):
                                target_path = os.path.normpath(target).replace("\\", "/")
                        except Exception:
                            pass
                    elif ext == ".exe":
                        target_path = os.path.normpath(filepath).replace("\\", "/")

                    if target_path and target_path not in seen_paths:
                        seen_paths.add(target_path)
                        apps.append({"name": name, "path": target_path})

        apps.sort(key=lambda x: x["name"].lower())
        
        pythoncom.CoUninitialize()
        self.apps_found.emit(apps)


class AddAppDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Application")
        self.setMinimumWidth(520)
        self.setModal(True)
        
        self.setup_ui()
        
        # Start background scanner thread for installed applications
        self.scanner_thread = AppScannerThread(self)
        self.scanner_thread.apps_found.connect(self.on_apps_found)
        self.scanner_thread.start()
        
    def setup_ui(self):
        # Overall container layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(24)

        # Title
        title_label = QLabel("Add New Application")
        title_label.setObjectName("dialogTitle")
        layout.addWidget(title_label)

        # Form Layout
        form_layout = QFormLayout()
        form_layout.setSpacing(14)
        form_layout.setContentsMargins(0, 5, 0, 5)

        # Detected Apps dropdown
        self.app_selector = QComboBox()
        self.app_selector.addItem("Scanning for installed applications...")
        self.app_selector.setEnabled(False)

        # Exe Path
        self.exe_path_input = QLineEdit()
        self.exe_path_input.setPlaceholderText("Select or enter the path to the executable...")
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.setProperty("class", "SecondaryBtn")
        self.browse_button.clicked.connect(self.browse_file)
        
        exe_layout = QHBoxLayout()
        exe_layout.setSpacing(10)
        exe_layout.addWidget(self.exe_path_input)
        exe_layout.addWidget(self.browse_button)
        
        # Display Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter the name to show in the launcher...")

        form_layout.addRow("Select App:", self.app_selector)
        form_layout.addRow("Executable Path:", exe_layout)
        form_layout.addRow("Display Name:", self.name_input)
        
        layout.addLayout(form_layout)

        # Action Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setProperty("class", "SecondaryBtn")
        self.cancel_button.clicked.connect(self.reject)
        
        self.add_button = QPushButton("Add Application")
        self.add_button.setProperty("class", "PrimaryBtn")
        self.add_button.setDefault(True)
        self.add_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.add_button)
        
        layout.addLayout(button_layout)

    def on_apps_found(self, apps):
        self.app_selector.blockSignals(True)
        self.app_selector.clear()
        self.app_selector.addItem("-- Select from discovered apps --", None)
        
        for app in apps:
            self.app_selector.addItem(app["name"], app)
            
        self.app_selector.setEnabled(True)
        self.app_selector.blockSignals(False)
        self.app_selector.currentIndexChanged.connect(self.on_app_selected)

    def on_app_selected(self, index):
        if index <= 0:
            return
            
        app_data = self.app_selector.itemData(index)
        if app_data and "path" in app_data:
            self.exe_path_input.setText(app_data["path"])
            self.name_input.setText(app_data["name"])

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Executable File",
            "",
            "Executable Files (*.exe);;All Files (*)"
        )
        if file_path:
            file_path = os.path.normpath(file_path).replace("\\", "/")
            self.exe_path_input.setText(file_path)
            
            # Autofill name if empty
            if not self.name_input.text().strip():
                base_name = os.path.basename(file_path)
                name, _ = os.path.splitext(base_name)
                self.name_input.setText(name)

    def get_data(self):
        """Returns (exe_path, display_name)."""
        return (self.exe_path_input.text().strip(), self.name_input.text().strip())

    def reject(self):
        self.cleanup_thread()
        super().reject()
        
    def accept(self):
        self.cleanup_thread()
        super().accept()
        
    def closeEvent(self, event):
        self.cleanup_thread()
        super().closeEvent(event)
        
    def cleanup_thread(self):
        if hasattr(self, 'scanner_thread') and self.scanner_thread.isRunning():
            self.scanner_thread.terminate()
            self.scanner_thread.wait()
