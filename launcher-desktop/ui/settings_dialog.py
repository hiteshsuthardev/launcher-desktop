import datetime
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QComboBox, QScrollArea, QWidget)
from PySide6.QtCore import Qt
import ui.theme as theme

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings & Trusted Devices")
        self.setMinimumSize(580, 500)
        self.setModal(True)
        self.main_window = parent
        self.trusted_manager = self.main_window.trusted_manager

        self.setup_ui()
        self.apply_styles()
        self.load_settings()
        self.load_devices()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(24)

        # Title
        title_label = QLabel("Settings & Devices")
        title_label.setObjectName("dialogTitle")
        main_layout.addWidget(title_label)

        # 1. Validity Duration Section
        duration_section = QFrame()
        duration_section.setObjectName("settingsCardFrame")
        duration_layout = QHBoxLayout(duration_section)
        duration_layout.setContentsMargins(20, 15, 20, 15)
        duration_layout.setSpacing(15)

        duration_lbl = QLabel("Connection Validity Duration:")
        duration_lbl.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 600;")
        
        self.duration_combo = QComboBox()
        self.duration_combo.addItems([
            "1 Hour",
            "6 Hours",
            "12 Hours",
            "1 Day (24 Hours)",
            "3 Days",
            "7 Days",
            "30 Days"
        ])
        # Mapping from combo index to duration in hours
        self.duration_map = {
            0: 1,
            1: 6,
            2: 12,
            3: 24,
            4: 72,
            5: 168,
            6: 720
        }
        self.duration_combo.currentIndexChanged.connect(self.save_duration_setting)

        duration_layout.addWidget(duration_lbl)
        duration_layout.addStretch()
        duration_layout.addWidget(self.duration_combo)
        main_layout.addWidget(duration_section)

        # 2. Trusted Devices List Section
        devices_header_lbl = QLabel("TRUSTED COMPANION DEVICES")
        devices_header_lbl.setStyleSheet("color: #6b7280; font-size: 11px; font-weight: 800; letter-spacing: 1px; margin-top: 10px;")
        main_layout.addWidget(devices_header_lbl)

        # Scroll Area for devices
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("devicesScrollArea")
        
        self.scroll_widget = QWidget()
        self.scroll_widget.setObjectName("scrollWidget")
        self.devices_layout = QVBoxLayout(self.scroll_widget)
        self.devices_layout.setContentsMargins(5, 5, 5, 5)
        self.devices_layout.setSpacing(12)
        self.devices_layout.setAlignment(Qt.AlignTop)
        
        self.scroll_area.setWidget(self.scroll_widget)
        main_layout.addWidget(self.scroll_area)

        # Bottom Close Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.close_button = QPushButton("Close")
        self.close_button.setProperty("class", "PrimaryBtn")
        self.close_button.clicked.connect(self.accept)
        btn_layout.addWidget(self.close_button)
        
        main_layout.addLayout(btn_layout)

    def load_settings(self):
        """Loads and maps configured duration to the combo box."""
        current_hours = self.trusted_manager.trust_duration_hours
        # Find closest match or default to 24 hours (index 3)
        combo_index = 3
        for idx, hours in self.duration_map.items():
            if hours == current_hours:
                combo_index = idx
                break
        self.duration_combo.setCurrentIndex(combo_index)

    def save_duration_setting(self):
        """Saves selected duration to trusted_manager."""
        idx = self.duration_combo.currentIndex()
        hours = self.duration_map.get(idx, 24)
        self.trusted_manager.save_settings(hours)

    def load_devices(self):
        """Populates the trusted devices scroll area list."""
        # Clear existing entries in layout
        while self.devices_layout.count():
            item = self.devices_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        devices = self.trusted_manager.trusted_devices
        if not devices:
            no_devices_lbl = QLabel("No trusted companion devices paired yet.")
            no_devices_lbl.setStyleSheet("color: #6b7280; font-size: 13px; font-style: italic; padding: 20px;")
            no_devices_lbl.setAlignment(Qt.AlignCenter)
            self.devices_layout.addWidget(no_devices_lbl)
            return

        for dev_id, info in list(devices.items()):
            dev_frame = QFrame()
            dev_frame.setObjectName("deviceCardFrame")
            
            dev_layout = QHBoxLayout(dev_frame)
            dev_layout.setContentsMargins(15, 12, 15, 12)
            dev_layout.setSpacing(15)

            # Details
            info_layout = QVBoxLayout()
            info_layout.setSpacing(4)
            
            name_lbl = QLabel(info.get("name", "Unknown Device"))
            name_lbl.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold;")
            
            last_conn_ts = info.get("last_connected", 0.0)
            last_conn_str = datetime.datetime.fromtimestamp(last_conn_ts).strftime("%Y-%m-%d %H:%M:%S")
            conn_lbl = QLabel(f"Last Connection: {last_conn_str}")
            conn_lbl.setStyleSheet("color: #9ca3af; font-size: 11px;")
            
            paired_ts = info.get("paired_time", 0.0)
            paired_str = datetime.datetime.fromtimestamp(paired_ts).strftime("%Y-%m-%d %H:%M:%S")
            paired_lbl = QLabel(f"Paired: {paired_str}")
            paired_lbl.setStyleSheet("color: #6b7280; font-size: 11px;")

            info_layout.addWidget(name_lbl)
            info_layout.addWidget(conn_lbl)
            info_layout.addWidget(paired_lbl)
            dev_layout.addLayout(info_layout)
            dev_layout.addStretch()

            # Forget Device Button
            forget_btn = QPushButton("Forget")
            forget_btn.setObjectName("forgetButton")
            forget_btn.clicked.connect(lambda checked=False, d_id=dev_id: self.forget_device(d_id))
            dev_layout.addWidget(forget_btn)

            self.devices_layout.addWidget(dev_frame)

    def forget_device(self, device_id: str):
        """Revokes token and removes device from trusted list."""
        self.trusted_manager.untrust_device(device_id)
        self.load_devices()

    def apply_styles(self):
        self.setStyleSheet(f"""
            #dialogTitle {{
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
                font-family: {theme.FONT_FAMILY};
            }}
            #settingsCardFrame {{
                background-color: {theme.BG_CARD};
                border: 1.5px solid {theme.BORDER_COLOR};
                border-radius: 12px;
            }}
            #deviceCardFrame {{
                background-color: {theme.BG_CARD};
                border: 1.5px solid {theme.BORDER_COLOR};
                border-radius: 10px;
            }}
            #devicesScrollArea {{
                border: none;
                background-color: transparent;
            }}
            #scrollWidget {{
                background-color: transparent;
            }}
            QComboBox {{
                background-color: #11141c;
                border: 1.5px solid {theme.BORDER_COLOR};
                border-radius: 6px;
                padding: 6px 12px;
                color: #ffffff;
                min-width: 150px;
                font-family: {theme.FONT_FAMILY};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: #11141c;
                border: 1.5px solid {theme.BORDER_COLOR};
                color: #ffffff;
                selection-background-color: {theme.ACCENT};
                selection-color: {theme.BG_DARK};
            }}
            #forgetButton {{
                background-color: rgba(239, 68, 68, 0.1);
                border: 1.5px solid #ef4444;
                border-radius: 6px;
                color: #ef4444;
                padding: 6px 15px;
                font-weight: bold;
                font-family: {theme.FONT_FAMILY};
            }}
            #forgetButton:hover {{
                background-color: #ef4444;
                color: #ffffff;
            }}
        """)
