import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame)
from PySide6.QtCore import Qt, QTimer
from ui.qrcode_widget import QRCodeWidget
import ui.theme as theme

class ConnectDeviceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect Companion Device")
        self.setMinimumWidth(560)
        self.setModal(True)
        self.main_window = parent
        
        self.last_code = ""
        self.last_address = ""
        self.setup_ui()
        self.apply_styles()
        
        # Start a timer to update values reactively
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.sync_details)
        self.sync_timer.start(500)
        
        self.sync_details()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(24)
        
        # Title & Subtitle
        title_layout = QVBoxLayout()
        title_layout.setSpacing(6)
        
        title_label = QLabel("Connect Mobile Companion")
        title_label.setObjectName("dialogTitle")
        
        desc_label = QLabel("Scan the QR code with your mobile app or type the details manually to link via your local Wi-Fi network.")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #9ca3af; font-size: 13px;")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(desc_label)
        main_layout.addLayout(title_layout)
        
        # Main Info Layout (Columns: Left = QR Code, Right = Code & Address)
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(24)
        
        # Left side: QR Code
        qr_container = QFrame()
        qr_container.setStyleSheet("background-color: transparent;")
        qr_layout = QVBoxLayout(qr_container)
        qr_layout.setContentsMargins(0, 0, 0, 0)
        
        self.qr_widget = QRCodeWidget(parent=self)
        qr_layout.addWidget(self.qr_widget)
        columns_layout.addWidget(qr_container)
        
        # Right side: Details & Manual entry
        details_layout = QVBoxLayout()
        details_layout.setSpacing(14)
        details_layout.setAlignment(Qt.AlignTop)
        
        # 1. Connect Address Box (Session ID)
        addr_box = QFrame()
        addr_box.setObjectName("dialogCardFrame")
        addr_layout = QVBoxLayout(addr_box)
        addr_layout.setContentsMargins(15, 12, 15, 12)
        addr_layout.setSpacing(6)
        
        addr_header = QLabel("CONNECT ADDRESS (LOCAL IP & PORT):")
        addr_header.setStyleSheet("color: #6b7280; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        
        self.addr_label = QLabel("STARTING SERVER...")
        self.addr_label.setObjectName("dialogAddrText")
        self.addr_label.setAlignment(Qt.AlignCenter)
        
        addr_layout.addWidget(addr_header)
        addr_layout.addWidget(self.addr_label)
        details_layout.addWidget(addr_box)
        
        # 2. Access Code Box
        code_box = QFrame()
        code_box.setObjectName("dialogCardFrame")
        code_layout = QVBoxLayout(code_box)
        code_layout.setContentsMargins(15, 12, 15, 12)
        code_layout.setSpacing(6)
        
        code_header = QLabel("ACCESS CODE:")
        code_header.setStyleSheet("color: #6b7280; font-size: 11px; font-weight: 800; letter-spacing: 1px;")
        
        self.code_label = QLabel("0 0 0 0 0 0")
        self.code_label.setObjectName("dialogCodeText")
        self.code_label.setAlignment(Qt.AlignCenter)
        
        code_layout.addWidget(code_header)
        code_layout.addWidget(self.code_label)
        details_layout.addWidget(code_box)
        
        # Expiration countdown
        self.timer_label = QLabel("Code expires in: 05:00")
        self.timer_label.setStyleSheet("color: #4da6ff; font-weight: bold; font-size: 12px;")
        details_layout.addWidget(self.timer_label)
        
        columns_layout.addLayout(details_layout)
        main_layout.addLayout(columns_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        self.regen_button = QPushButton("🔄  Regenerate Session")
        self.regen_button.setProperty("class", "SecondaryBtn")
        self.regen_button.clicked.connect(self.regenerate_session)
        
        self.close_button = QPushButton("Close")
        self.close_button.setProperty("class", "PrimaryBtn")
        self.close_button.setDefault(True)
        self.close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.regen_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        main_layout.addLayout(button_layout)

    def regenerate_session(self):
        """Requests the main window to regenerate the pairing session code."""
        if hasattr(self.main_window, "regenerate_pairing_code"):
            self.main_window.regenerate_pairing_code()
            self.sync_details()

    def sync_details(self):
        """Polls main window state to update QR codes and timer text."""
        code = self.main_window.pairing_code
        spaced_code = "  ".join(list(code))
        self.code_label.setText(spaced_code)
        
        addr = self.main_window.connect_address
        if addr:
            self.addr_label.setText(addr)
        else:
            self.addr_label.setText("STARTING SERVER...")
            
        # Update QR code when code or address changes
        if code != self.last_code or addr != self.last_address:
            self.last_code = code
            self.last_address = addr
            qr_data = self.main_window.get_pairing_json()
            self.qr_widget.update_data(qr_data)
            
        # Update timer
        time_left = self.main_window.pairing_time_left
        minutes, seconds = divmod(time_left, 60)
        self.timer_label.setText(f"Code expires in:  {minutes:02d}:{seconds:02d}")

    def apply_styles(self):
        self.setStyleSheet(f"""
            #dialogTitle {{
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
                font-family: {theme.FONT_FAMILY};
            }}
            #dialogCardFrame {{
                background-color: #11141c;
                border: 1.5px solid #232a3b;
                border-radius: 12px;
            }}
            #dialogCodeText {{
                font-family: 'Courier New', Courier, monospace;
                font-size: 30px;
                font-weight: bold;
                color: #4da6ff;
                letter-spacing: 6px;
            }}
            #dialogAddrText {{
                font-family: 'Courier New', Courier, monospace;
                font-size: 16px;
                font-weight: bold;
                color: #14e8b0;
                letter-spacing: 1px;
            }}
        """)
