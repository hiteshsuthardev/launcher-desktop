import os
import sys
import random
import json
import datetime
from PySide6.QtWidgets import (QMainWindow, QWidget, QScrollArea, QGridLayout, 
                             QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
                             QMenu, QInputDialog, QMessageBox, QSlider, QSystemTrayIcon)
from PySide6.QtCore import Qt, QTimer, Signal, QEvent, QPropertyAnimation, QEasingCurve, QRectF, Property
from PySide6.QtGui import QPixmap, QColor, QKeyEvent, QPainter, QPen, QRadialGradient, QIcon, QAction


from core.app_manager import AppManager
from core.trusted_manager import TrustedManager
from core.launcher import launch_app
from network.local_server import LocalServerThread
from ui.add_app_dialog import AddAppDialog
from ui.settings_dialog import SettingsDialog
import ui.theme as theme

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("titleBar")
        self.setFixedHeight(40)
        self.parent_window = parent
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 0, 0)
        layout.setSpacing(0)
        
        logo = QLabel("🎮  AppLauncher")
        logo.setObjectName("titleBarText")
        layout.addWidget(logo)
        
        layout.addStretch()
        
        self.btn_min = QPushButton("─")
        self.btn_min.setProperty("class", "TitleBarBtn")
        self.btn_min.clicked.connect(self.parent_window.showMinimized)
        
        self.btn_max = QPushButton("▢")
        self.btn_max.setProperty("class", "TitleBarBtn")
        self.btn_max.clicked.connect(self.toggle_maximize)
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("btnClose")
        self.btn_close.setProperty("class", "TitleBarBtn")
        self.btn_close.clicked.connect(self.parent_window.close)
        
        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(self.btn_close)
        
        self.drag_position = None

    def toggle_maximize(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self.btn_max.setText("▢")
        else:
            self.parent_window.showMaximized()
            self.btn_max.setText("❐")

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()
            event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_position is not None and event.buttons() == Qt.LeftButton:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
                self.btn_max.setText("▢")
            self.parent_window.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        event.accept()


class PulsingDot(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self.alpha = 255
        self.fading_down = True
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.pulse)
        self.timer.start(50)
        self.set_color(theme.ACCENT)

    def set_color(self, hex_color):
        self.base_color = hex_color
        self.update_style()

    def pulse(self):
        if self.base_color == theme.STATUS_CONNECTED:
            self.alpha = 255
            self.update_style()
            return

        if self.fading_down:
            self.alpha -= 12
            if self.alpha <= 70:
                self.alpha = 70
                self.fading_down = False
        else:
            self.alpha += 12
            if self.alpha >= 255:
                self.alpha = 255
                self.fading_down = True
        self.update_style()

    def update_style(self):
        if self.base_color == theme.STATUS_CONNECTED:
            self.setStyleSheet(f"background-color: {self.base_color}; border-radius: 5px;")
        else:
            self.setStyleSheet(f"background-color: rgba({theme.ACCENT_RGB}, {self.alpha/255.0:.2f}); border-radius: 5px;")


class AppTile(QFrame):
    clicked = Signal(str)
    action_requested = Signal(str, str)

    def __init__(self, app_id: str, name: str, icon_path: str, is_add_button: bool = False, parent=None):
        super().__init__(parent)
        self.app_id = app_id
        self.name = name
        self.icon_path = icon_path
        self.is_add_button = is_add_button
        
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedSize(180, 220)
        self.setObjectName("AddTile" if is_add_button else "AppTile")
        
        self._scale_progress = 0.0
        self._anim = QPropertyAnimation(self, b"scale_progress")
        self._anim.setDuration(theme.ANIM_DURATION)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        
        self.launching = False
        self.spinner_angle = 0
        self.spinner_timer = QTimer(self)
        self.spinner_timer.timeout.connect(self.update_spinner)
        
        self.setup_ui()

    @Property(float)
    def scale_progress(self):
        return self._scale_progress

    @scale_progress.setter
    def scale_progress(self, val):
        self._scale_progress = val
        m = int(18 - 8 * val)
        self.layout().setContentsMargins(m, m, m, m)
        self.update()

    def update_spinner(self):
        self.spinner_angle = (self.spinner_angle + 12) % 360
        self.update()

    def start_loading(self):
        self.launching = True
        self.spinner_timer.start(30)
        self.update()

    def stop_loading(self):
        self.launching = False
        self.spinner_timer.stop()
        self.update()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignCenter)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(80, 80)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setObjectName("tileIcon")
        
        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setObjectName("tileName")
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.name_label)

        if self.is_add_button:
            self.name_label.setText("Add App")
            self.icon_label.setText("+")
            self.icon_label.setStyleSheet("font-size: 56px; color: #4da6ff; font-weight: bold; margin-bottom: 5px;")
        else:
            self.name_label.setText(self.name)
            self.load_icon()

    def load_icon(self):
        if self.icon_path and os.path.exists(self.icon_path):
            pixmap = QPixmap(self.icon_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.icon_label.setPixmap(pixmap)
                return
        self.icon_label.setText("🎮")
        self.icon_label.setStyleSheet("font-size: 44px;")

    def enterEvent(self, event):
        self.animate_scale(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.hasFocus():
            self.animate_scale(0.0)
        super().leaveEvent(event)

    def focusInEvent(self, event):
        self.animate_scale(1.0)
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        if not self.underMouse():
            self.animate_scale(0.0)
        super().focusOutEvent(event)

    def animate_scale(self, target):
        self._anim.stop()
        self._anim.setStartValue(self._scale_progress)
        self._anim.setEndValue(target)
        self._anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setFocus()
            self.clicked.emit(self.app_id)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        if self.is_add_button:
            return
            
        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        remove_action = menu.addAction("Remove")
        
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {theme.BG_CARD};
                color: #ffffff;
                border: 1px solid {theme.BORDER_COLOR};
                border-radius: 8px;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 24px;
                border-radius: 4px;
                font-size: 13px;
                font-family: {theme.FONT_FAMILY};
            }}
            QMenu::item:selected {{
                background-color: {theme.ACCENT};
                color: {theme.BG_DARK};
                font-weight: bold;
            }}
        """)
        
        action = menu.exec(event.globalPos())
        if action == rename_action:
            self.action_requested.emit(self.app_id, "rename")
        elif action == remove_action:
            self.action_requested.emit(self.app_id, "remove")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        inset = 8 - 6 * self._scale_progress
        rect = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        
        is_active = self.hasFocus() or self.underMouse()
        
        bg_color = QColor(theme.BG_CARD_HOVER if is_active else theme.BG_CARD)
        border_color = QColor(theme.ACCENT if is_active else theme.BORDER_COLOR)
        border_width = 2.0 if is_active else 1.5
        
        if is_active and self._scale_progress > 0:
            for i in range(1, 6):
                glow_rect = rect.adjusted(-i, -i, i, i)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(77, 166, 255, int((16 - i * 2.5) * self._scale_progress)))
                painter.drawRoundedRect(glow_rect, 16, 16)
                
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(rect, 14, 14)
        
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect, 14, 14)
        
        if self.launching:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(10, 11, 13, 200))
            painter.drawRoundedRect(rect, 14, 14)
            
            spinner_rect = QRectF(rect.center().x() - 20, rect.center().y() - 20, 40, 40)
            pen = QPen(QColor(theme.ACCENT), 3)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawArc(spinner_rect, self.spinner_angle * 16, 270 * 16)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AppLauncher")
        self.setMinimumSize(1020, 680)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint)
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(base_dir, "data")
        
        self.app_manager = AppManager(self.data_dir)
        self.trusted_manager = TrustedManager(self.data_dir)
        self.tiles = []
        
        self.connect_address = ""
        self.pairing_code = ""
        self.pairing_time_left = 600
        self.regenerate_pairing_code()
        
        self.setup_ui()
        self.load_stylesheet()
        self.load_grid()
        self.start_networking()
        
        # Timer for code expiration
        self.timer_ticker = QTimer(self)
        self.timer_ticker.timeout.connect(self.decrement_pairing_timer)
        self.timer_ticker.start(1000)
        
        # Timer to keep sliders in sync with physical device hardware state (volume & brightness)
        self.slider_sync_timer = QTimer(self)
        self.slider_sync_timer.timeout.connect(self.sync_system_sliders)
        self.slider_sync_timer.start(500)
        
        # System Tray configuration
        self.really_quit = False
        self.tray_message_shown = False
        self.setup_tray_icon()


    def load_stylesheet(self):
        qss_path = os.path.join(os.path.dirname(__file__), "style.qss")
        if os.path.exists(qss_path):
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        window_layout = QVBoxLayout(self.central_widget)
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(self)
        window_layout.addWidget(self.title_bar)
        
        self.content_panel = QWidget()
        self.content_panel.setObjectName("contentPanel")
        window_layout.addWidget(self.content_panel)
        
        content_layout = QVBoxLayout(self.content_panel)
        content_layout.setContentsMargins(40, 25, 40, 30)
        content_layout.setSpacing(25)
        
        # Header (Logo + Connect Button + Status Card)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)
        
        title_label = QLabel("APPLAUNCHER")
        title_label.setObjectName("appTitle")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Connect Modal Trigger
        self.btn_connect = QPushButton("📱  Connect Device")
        self.btn_connect.setProperty("class", "PrimaryBtn")
        self.btn_connect.setFocusPolicy(Qt.StrongFocus)
        self.btn_connect.clicked.connect(self.open_connect_device_dialog)
        header_layout.addWidget(self.btn_connect)
        
        # Settings Trigger
        self.btn_settings = QPushButton("⚙️  Settings")
        self.btn_settings.setProperty("class", "SecondaryBtn")
        self.btn_settings.setFocusPolicy(Qt.StrongFocus)
        self.btn_settings.clicked.connect(self.open_settings_dialog)
        header_layout.addWidget(self.btn_settings)
        
        # Pairing code card
        self.pairing_container = QFrame()
        self.pairing_container.setObjectName("pairingContainer")
        pairing_layout = QHBoxLayout(self.pairing_container)
        pairing_layout.setContentsMargins(18, 8, 18, 8)
        pairing_layout.setSpacing(12)
        
        self.status_dot = PulsingDot(self)
        self.pairing_label = QLabel(self.get_status_label_text())
        self.pairing_label.setObjectName("pairingLabel")
        
        pairing_layout.addWidget(self.status_dot)
        pairing_layout.addWidget(self.pairing_label)
        header_layout.addWidget(self.pairing_container)
        content_layout.addLayout(header_layout)
        
        # --- Split Dashboard Layout (Unified Page) ---
        dashboard_layout = QHBoxLayout()
        dashboard_layout.setSpacing(30)
        content_layout.addLayout(dashboard_layout)
        
        # Left Panel (Applications Grid)
        self.left_panel = QWidget()
        self.left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        library_title = QLabel("MY LIBRARY")
        library_title.setObjectName("sectionTitle")
        left_layout.addWidget(library_title)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("gridScrollArea")
        
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scrollContent")
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        
        self.scroll_area.setWidget(self.scroll_content)
        left_layout.addWidget(self.scroll_area)
        
        dashboard_layout.addWidget(self.left_panel, stretch=7)
        
        # Right Panel (Sidebar Quick Settings Panel)
        self.right_panel = QFrame()
        self.right_panel.setObjectName("sidebarPanel")
        self.right_panel.setFixedWidth(320)
        self.setup_sidebar_controls()
        
        dashboard_layout.addWidget(self.right_panel, stretch=3)

    def setup_sidebar_controls(self):
        sidebar_layout = QVBoxLayout(self.right_panel)
        sidebar_layout.setContentsMargins(20, 20, 20, 20)
        sidebar_layout.setSpacing(22)
        sidebar_layout.setAlignment(Qt.AlignTop)
        
        # Title of Sidebar
        sidebar_header = QLabel("QUICK SYSTEM SETTINGS")
        sidebar_header.setObjectName("sectionTitle")
        sidebar_header.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 800; border-bottom: 1.5px solid #232a3b; padding-bottom: 8px;")
        sidebar_layout.addWidget(sidebar_header)
        
        # Section 1: AUDIO & PLAYBACK
        audio_sec = QWidget()
        audio_sec.setProperty("class", "sidebarSection")
        audio_layout = QVBoxLayout(audio_sec)
        audio_layout.setContentsMargins(0, 0, 0, 0)
        audio_layout.setSpacing(10)
        
        audio_title = QLabel("AUDIO & PLAYBACK")
        audio_title.setProperty("class", "sidebarSectionTitle")
        audio_layout.addWidget(audio_title)
        
        # Volume slider row
        vol_row = QHBoxLayout()
        vol_row.setSpacing(12)
        
        self.vol_value_label = QLabel("50%")
        self.vol_value_label.setProperty("class", "sliderLabel")
        self.vol_value_label.setFixedWidth(35)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        
        from core.system_controls import get_volume_scalar
        vol_scalar = get_volume_scalar()
        self.volume_slider.setValue(int(vol_scalar * 100))
        self.vol_value_label.setText(f"{self.volume_slider.value()}%")
        
        self.volume_slider.valueChanged.connect(self.handle_volume_change)
        
        vol_row.addWidget(QLabel("🔊"))
        vol_row.addWidget(self.volume_slider)
        vol_row.addWidget(self.vol_value_label)
        audio_layout.addLayout(vol_row)
        
        # Media controls row
        media_row = QHBoxLayout()
        media_row.setSpacing(10)
        media_row.setAlignment(Qt.AlignCenter)
        
        self.btn_prev = QPushButton("⏮️")
        self.btn_prev.setProperty("class", "MediaBtn")
        self.btn_prev.clicked.connect(lambda: self.trigger_local_system_action("media_previous"))
        
        self.btn_play = QPushButton("▶️")
        self.btn_play.setProperty("class", "MediaBtn")
        self.btn_play.clicked.connect(lambda: self.trigger_local_system_action("media_play_pause"))
        
        self.btn_next = QPushButton("⏭️")
        self.btn_next.setProperty("class", "MediaBtn")
        self.btn_next.clicked.connect(lambda: self.trigger_local_system_action("media_next"))
        
        self.btn_mute = QPushButton("🔇")
        self.btn_mute.setProperty("class", "MediaBtn")
        self.btn_mute.clicked.connect(lambda: self.trigger_local_system_action("volume_mute"))
        
        media_row.addWidget(self.btn_prev)
        media_row.addWidget(self.btn_play)
        media_row.addWidget(self.btn_next)
        media_row.addWidget(self.btn_mute)
        audio_layout.addLayout(media_row)
        
        sidebar_layout.addWidget(audio_sec)
        
        # Section 2: DISPLAY & UTILITY
        disp_sec = QWidget()
        disp_sec.setProperty("class", "sidebarSection")
        disp_layout = QVBoxLayout(disp_sec)
        disp_layout.setContentsMargins(0, 0, 0, 0)
        disp_layout.setSpacing(10)
        
        disp_title = QLabel("DISPLAY & UTILITY")
        disp_title.setProperty("class", "sidebarSectionTitle")
        disp_layout.addWidget(disp_title)
        
        # Brightness slider row
        bright_row = QHBoxLayout()
        bright_row.setSpacing(12)
        
        self.bright_value_label = QLabel("50%")
        self.bright_value_label.setProperty("class", "sliderLabel")
        self.bright_value_label.setFixedWidth(35)
        
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 100)
        
        from core.system_controls import get_brightness_value
        bright_val = get_brightness_value()
        self.brightness_slider.setValue(bright_val)
        self.bright_value_label.setText(f"{bright_val}%")
        
        self.brightness_slider.valueChanged.connect(self.update_brightness_label)
        self.brightness_slider.sliderReleased.connect(self.apply_brightness_change)
        
        bright_row.addWidget(QLabel("☀️"))
        bright_row.addWidget(self.brightness_slider)
        bright_row.addWidget(self.bright_value_label)
        disp_layout.addLayout(bright_row)
        
        # Wi-Fi toggle button
        self.btn_wifi = QPushButton("📶  Toggle Wi-Fi Connection")
        self.btn_wifi.setProperty("class", "PowerGridBtn")
        self.btn_wifi.setProperty("action", "wifi_toggle")
        self.btn_wifi.clicked.connect(lambda: self.trigger_local_system_action("wifi_toggle"))
        disp_layout.addWidget(self.btn_wifi)
        
        sidebar_layout.addWidget(disp_sec)
        
        # Section 3: POWER OPERATIONS
        power_sec = QWidget()
        power_sec.setProperty("class", "sidebarSection")
        power_layout = QVBoxLayout(power_sec)
        power_layout.setContentsMargins(0, 0, 0, 0)
        power_layout.setSpacing(10)
        
        power_title = QLabel("POWER & SESSION")
        power_title.setProperty("class", "sidebarSectionTitle")
        power_layout.addWidget(power_title)
        
        power_grid = QGridLayout()
        power_grid.setSpacing(10)
        power_grid.setContentsMargins(0, 0, 0, 0)
        
        self.btn_lock = QPushButton("🔒  Lock PC")
        self.btn_lock.setProperty("class", "PowerGridBtn")
        self.btn_lock.setProperty("action", "lock_screen")
        self.btn_lock.clicked.connect(lambda: self.trigger_local_system_action("lock_screen"))
        
        self.btn_sleep = QPushButton("💤  Sleep PC")
        self.btn_sleep.setProperty("class", "PowerGridBtn")
        self.btn_sleep.clicked.connect(lambda: self.trigger_local_system_action("sleep"))
        
        self.btn_restart = QPushButton("🔄  Restart")
        self.btn_restart.setProperty("class", "PowerGridBtn")
        self.btn_restart.clicked.connect(lambda: self.trigger_local_system_action("restart"))
        
        self.btn_shutdown = QPushButton("🛑  Shutdown")
        self.btn_shutdown.setProperty("class", "PowerGridBtn")
        self.btn_shutdown.clicked.connect(lambda: self.trigger_local_system_action("shutdown"))
        
        power_grid.addWidget(self.btn_lock, 0, 0)
        power_grid.addWidget(self.btn_sleep, 0, 1)
        power_grid.addWidget(self.btn_restart, 1, 0)
        power_grid.addWidget(self.btn_shutdown, 1, 1)
        power_layout.addLayout(power_grid)
        
        sidebar_layout.addWidget(power_sec)
        sidebar_layout.addStretch()

    def handle_volume_change(self, val):
        self.vol_value_label.setText(f"{val}%")
        try:
            from core.system_controls import set_volume_scalar
            set_volume_scalar(val / 100.0)
        except Exception as e:
            print(f"Error setting volume: {e}")

    def update_brightness_label(self, val):
        self.bright_value_label.setText(f"{val}%")

    def apply_brightness_change(self):
        val = self.brightness_slider.value()
        try:
            from core.system_controls import set_brightness_value
            set_brightness_value(val)
        except Exception as e:
            print(f"Error setting brightness: {e}")

    def sync_system_sliders(self):
        """Polls hardware volume levels and syncs the UI sliders to match."""
        try:
            from core.system_controls import get_volume_scalar
            # Sync volume slider
            current_vol = int(get_volume_scalar() * 100)
            if abs(self.volume_slider.value() - current_vol) > 1:
                self.volume_slider.blockSignals(True)
                self.volume_slider.setValue(current_vol)
                self.vol_value_label.setText(f"{current_vol}%")
                self.volume_slider.blockSignals(False)
        except Exception:
            pass

    def trigger_local_system_action(self, action: str):
        from core.system_controls import execute_system_action
        success, msg = execute_system_action(action)
        if not success:
            QMessageBox.warning(self, "System Action Error", msg)
        else:
            # Sync slider state instantly if mute changed volume internally
            self.sync_system_sliders()

    def decrement_pairing_timer(self):
        # Reset pairing timer if a client is actively paired/connected
        if hasattr(self, "server_thread") and self.server_thread and self.server_thread.authenticated_client is not None:
            self.pairing_time_left = 600
            return
            
        self.pairing_time_left -= 1
        if self.pairing_time_left <= 0:
            print("[PAIRING TIMER] Session expired. Regenerating...")
            self.regenerate_pairing_code()

    def regenerate_pairing_code(self):
        """Generates a new random 6-digit numeric access code."""
        self.pairing_code = "".join(random.choices("0123456789", k=6))
        self.pairing_time_left = 600
        
        try:
            code_file_path = os.path.join(self.data_dir, "pairing_code.txt")
            with open(code_file_path, "w") as f:
                f.write(self.pairing_code)
            print(f"[DEBUG CODE] Wrote active pairing code to file: {self.pairing_code}")
        except Exception as e:
            print(f"[DEBUG CODE ERROR] Failed to write pairing code to file: {e}")
        
        if hasattr(self, "server_thread") and self.server_thread:
            self.server_thread.update_pairing_code(self.pairing_code)
            
        if hasattr(self, "pairing_label") and self.pairing_label:
            self.pairing_label.setText(self.get_status_label_text())

    def get_pairing_json(self) -> str:
        """Assembles JSON payload encoding the relay session ID and active pairing code."""
        data = {
            "address": self.connect_address,
            "code": self.pairing_code
        }
        return json.dumps(data)

    def get_status_label_text(self) -> str:
        """Helper to format the status card label text."""
        code_str = "  ".join(list(self.pairing_code))
        if self.connect_address:
            return f"Server: {self.connect_address}  |  Code: {code_str}"
        return f"Starting Server...  |  Code: {code_str}"

    def open_connect_device_dialog(self):
        from ui.connect_device_dialog import ConnectDeviceDialog
        dialog = ConnectDeviceDialog(self)
        dialog.exec()

    def open_settings_dialog(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        gradient = QRadialGradient(self.width() / 2, self.height() / 2, max(self.width(), self.height()))
        gradient.setColorAt(0.0, QColor(21, 26, 38))
        gradient.setColorAt(0.65, QColor(10, 11, 13))
        gradient.setColorAt(1.0, QColor(6, 7, 8))
        
        painter.fillRect(self.rect(), gradient)

    def load_grid(self):
        for tile in self.tiles:
            self.grid_layout.removeWidget(tile)
            tile.deleteLater()
        self.tiles.clear()

        apps = self.app_manager.get_apps()
        for app in apps:
            icon_abs_path = os.path.join(self.data_dir, app["icon_path"]) if app["icon_path"] else ""
            tile = AppTile(app["id"], app["name"], icon_abs_path, is_add_button=False)
            tile.clicked.connect(self.handle_tile_click)
            tile.action_requested.connect(self.handle_tile_action)
            self.tiles.append(tile)
            
        add_tile = AppTile("add_app", "Add App", "", is_add_button=True)
        add_tile.clicked.connect(self.handle_tile_click)
        self.tiles.append(add_tile)
        
        self.update_grid_layout()
        
        if self.tiles:
            self.tiles[0].setFocus()
            
        self.notify_companion_apps_changed()

    def notify_companion_apps_changed(self):
        """Notifies the companion app that the application library has changed."""
        if hasattr(self, "server_thread") and self.server_thread:
            self.server_thread.push_apps_to_companion()

    def update_grid_layout(self):
        for tile in self.tiles:
            self.grid_layout.removeWidget(tile)
            
        cols = self.calculate_columns()
        for idx, tile in enumerate(self.tiles):
            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(tile, row, col)

    def calculate_columns(self):
        width = self.scroll_area.viewport().width()
        if width <= 0:
            width = self.width() - 360 # Adjust for sidebar width + margins
        tile_width = 180
        spacing = 24
        margins = 20
        cols = (width - margins) // (tile_width + spacing)
        return max(1, cols)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_grid_layout()

    def handle_tile_click(self, app_id: str):
        if app_id == "add_app":
            self.open_add_app_dialog()
        else:
            self.launch_app_by_id(app_id)

    def handle_tile_action(self, app_id: str, action: str):
        if action == "rename":
            app = self.app_manager.get_app(app_id)
            if not app:
                return
            new_name, ok = QInputDialog.getText(
                self, "Rename Application", 
                "Enter new name:", text=app["name"]
            )
            if ok and new_name.strip():
                if self.app_manager.rename_app(app_id, new_name.strip()):
                    self.load_grid()
        elif action == "remove":
            app = self.app_manager.get_app(app_id)
            if not app:
                return
            reply = QMessageBox.question(
                self, "Remove Application",
                f"Are you sure you want to remove '{app['name']}'?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                if self.app_manager.remove_app(app_id):
                    self.load_grid()

    def open_add_app_dialog(self):
        dialog = AddAppDialog(self)
        if dialog.exec() == AddAppDialog.Accepted:
            exe_path, display_name = dialog.get_data()
            if exe_path:
                app = self.app_manager.add_app(exe_path, display_name)
                if app:
                    self.load_grid()
                else:
                    QMessageBox.warning(self, "Error", "Failed to add application. Ensure the path is correct.")

    def launch_app_by_id(self, app_id: str):
        tile = None
        for t in self.tiles:
            if t.app_id == app_id:
                tile = t
                break
                
        if tile:
            tile.start_loading()
            QTimer.singleShot(2000, tile.stop_loading)

        app = self.app_manager.get_app(app_id)
        if app:
            success = launch_app(app["exe_path"])
            if not success:
                if tile:
                    tile.stop_loading()
                QMessageBox.critical(self, "Launch Error", f"Could not launch executable:\n{app['exe_path']}")

    def start_networking(self):
        """Starts the Local WebSocket Server."""
        self.server_thread = LocalServerThread(
            pairing_code=self.pairing_code,
            app_manager=self.app_manager,
            trusted_manager=self.trusted_manager
        )
        self.server_thread.launch_requested.connect(self.launch_app_by_id)
        self.server_thread.client_connected.connect(self.handle_client_connected)
        self.server_thread.client_disconnected.connect(self.handle_client_disconnected)
        self.server_thread.server_started.connect(self.handle_server_started)
        self.server_thread.start()

    def handle_server_started(self, ip: str, port: int):
        self.connect_address = f"ws://{ip}:{port}"
        if hasattr(self, "pairing_label") and self.pairing_label:
            self.pairing_label.setText(self.get_status_label_text())

    def handle_client_connected(self, name_or_addr: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_dot.set_color(theme.STATUS_CONNECTED)
        
        addr_part = f"Relay Session: {self.connect_address}" if self.connect_address else "Relay"
        self.pairing_label.setText(f"Connected:  {name_or_addr} ({timestamp})  |  {addr_part}")
        
        self.regenerate_pairing_code()

    def handle_client_disconnected(self, name_or_addr: str):
        self.status_dot.set_color(theme.ACCENT)
        self.pairing_label.setText(self.get_status_label_text())

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            self.navigate_grid(key)
            event.accept()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            focused = self.focusWidget()
            if isinstance(focused, AppTile):
                self.handle_tile_click(focused.app_id)
                event.accept()
        else:
            super().keyPressEvent(event)

    def navigate_grid(self, key):
        focused_widget = self.focusWidget()
        if not isinstance(focused_widget, AppTile):
            if self.tiles:
                self.tiles[0].setFocus()
            return

        try:
            idx = self.tiles.index(focused_widget)
        except ValueError:
            if self.tiles:
                self.tiles[0].setFocus()
            return

        cols = self.calculate_columns()
        num_tiles = len(self.tiles)

        if key == Qt.Key_Left:
            new_idx = idx - 1
            if new_idx < 0:
                new_idx = num_tiles - 1
        elif key == Qt.Key_Right:
            new_idx = idx + 1
            if new_idx >= num_tiles:
                new_idx = 0
        elif key == Qt.Key_Up:
            new_idx = idx - cols
            if new_idx < 0:
                new_idx = (idx % cols) + ((num_tiles - 1) // cols) * cols
                if new_idx >= num_tiles:
                    new_idx -= cols
        elif key == Qt.Key_Down:
            new_idx = idx + cols
            if new_idx >= num_tiles:
                new_idx = idx % cols

        new_idx = max(0, min(new_idx, num_tiles - 1))
        self.tiles[new_idx].setFocus()

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        icon = self.create_tray_icon()
        self.tray_icon.setIcon(icon)
        self.setWindowIcon(icon)
        
        self.tray_menu = QMenu(self)
        self.tray_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {theme.BG_CARD};
                color: #ffffff;
                border: 1px solid {theme.BORDER_COLOR};
                border-radius: 8px;
                padding: 5px;
            }}
            QMenu::item {{
                padding: 8px 24px;
                border-radius: 4px;
                font-size: 13px;
                font-family: {theme.FONT_FAMILY};
            }}
            QMenu::item:selected {{
                background-color: {theme.ACCENT};
                color: {theme.BG_DARK};
                font-weight: bold;
            }}
        """)
        
        show_action = QAction("Open AppLauncher", self)
        show_action.triggered.connect(self.show_and_activate)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        
        self.tray_menu.addAction(show_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.handle_tray_activation)
        self.tray_icon.show()

    def create_tray_icon(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw a beautiful dark background circle with neon blue glow border
        painter.setBrush(QColor("#151821"))
        pen = QPen(QColor("#4da6ff"), 4)
        painter.setPen(pen)
        painter.drawEllipse(4, 4, 56, 56)
        
        # Draw a clean game play/controller triangle shape
        painter.setBrush(QColor("#4da6ff"))
        painter.setPen(Qt.NoPen)
        
        from PySide6.QtGui import QPolygonF
        from PySide6.QtCore import QPointF
        points = [QPointF(26, 20), QPointF(26, 44), QPointF(46, 32)]
        painter.drawPolygon(QPolygonF(points))
        
        painter.end()
        return QIcon(pixmap)

    def show_and_activate(self):
        self.show()
        if self.isMaximized():
            self.showMaximized()
        else:
            self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_application(self):
        self.really_quit = True
        self.close()
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    def handle_tray_activation(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.isVisible():
                self.hide()
            else:
                self.show_and_activate()

    def closeEvent(self, event):
        if not self.really_quit:
            event.ignore()
            self.hide()
            if not self.tray_message_shown:
                self.tray_icon.showMessage(
                    "AppLauncher",
                    "AppLauncher will continue running in the background.",
                    QSystemTrayIcon.Information,
                    3000
                )
                self.tray_message_shown = True
        else:
            self.server_thread.stop()
            super().closeEvent(event)
