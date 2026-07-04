# AppLauncher (launcher-desktop)

A modern, high-performance **PySide6-based Windows Desktop Launcher** designed for a Console-like/Big Picture experience. This application integrates local and WAN-capable **WebSockets** to pair with a mobile companion device, enabling you to launch desktop applications, retrieve lists of apps, and control Windows system settings (volume, brightness, keyboard simulation, etc.) remotely.

---

## Key Features

- 🎮 **Console-like UI**: Implements a sleek, fullscreen-maximized console interface built using PySide6.
- ⚙️ **Windows System Control**: Integrates directly with Windows APIs to control:
  - System Volume (via `pycaw`)
  - Screen Brightness (via `screen-brightness-control`)
  - Keyboard Inputs / Remote navigation (via `keyboard`)
- 📦 **Dynamic Application Management**:
  - Add executables dynamically with auto icon extraction (extracts `.ico` / `.png` from `.exe`).
  - Store apps and preferences locally in portable JSON files (`apps.json`, `settings.json`).
- 🔗 **Dual-Mode Companion Connectivity**:
  - **Local WebSocket Server**: Hosts an authenticated local server directly from the desktop (defaulting to ports `8765-8775`).
  - **Relay Server Support**: Includes a standalone relay server (`relay_server.py`) for pairing over the WAN/internet without complex port forwarding.
- 🔒 **Device Trust Manager**: Securely pairs mobile companion devices using a 6-digit PIN and persistent pairing tokens saved in `trusted_devices.json`.
- ⚡ **Real-Time Pushes**: Broadcasts active updates (such as additions or removals from the app library) directly to connected companion clients.

---

## Repository Structure

```text
launcher-desktop/
├── main.py                  # Desktop application entry point
├── relay_server.py          # Standalone WebSocket relay server
├── requirements.txt         # Project package requirements
├── test_client_req.py       # Client request / connection simulator script
├── test_push.py             # Client push listener simulator script
├── core/                    # Core business logic layer
│   ├── app_manager.py       # Manages application additions, library, and icons
│   ├── system_controls.py   # Handles volume, brightness, and key inputs
│   ├── icon_extractor.py    # Extracts high-res icons from Windows executables
│   ├── trusted_manager.py   # Manages pairing security tokens and expiry settings
│   └── launcher.py          # Executes system programs
├── ui/                      # PySide6 Graphical Interface
│   ├── main_window.py       # Fullscreen launcher dashboard
│   ├── style.qss            # Custom CSS/QSS styling sheet
│   ├── theme.py             # UI design theme configurations
│   └── qrcode_widget.py     # Renders pairing QR code dynamically
├── network/                 # Networking/WebSocket clients & server
│   ├── local_server.py      # Direct local WebSocket server (thread-safe)
│   └── relay_client.py      # Reconnection-ready client for remote relay
└── data/                    # Generated application database & pairing caches
```

---

## Installation & Setup

### Prerequisites
- **Operating System**: Windows (required for PySide6 UI and native system integrations like `pywin32` and `pycaw`).
- **Python**: Python 3.8 or higher.

### 1. Download/Clone the Project
```bash
git clone https://github.com/hiteshsuthardev/launcher-desktop.git
cd launcher-desktop
```

### 2. Set Up a Virtual Environment (Recommended)
Creating a virtual environment ensures that the required packages do not conflict with your global Python installation.

**On Command Prompt (cmd):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**On PowerShell:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Package Dependencies
With your virtual environment activated, install the required packages:
```bash
pip install -r requirements.txt
```

---

## Running the Application

### 1. Start the Desktop Launcher
Run the main PySide6 desktop application:
```bash
python main.py
```
This opens the fullscreen dashboard containing your applications, pairing information, system options, and QR codes.

### 2. Start the Standalone Relay Server (Optional)
If you want to allow remote pairing over external networks (WAN) without directly exposing ports:
```bash
python relay_server.py
```
By default, the relay server listens on port `8888` (`ws://0.0.0.0:8888`). You can host this relay server on a cloud instance/VPS to connect your phone (cellular) to your desktop (home network).

### 3. Testing with Simulator Scripts
To test connection capabilities and command routing without developing a mobile companion application:

- **Listen for real-time app list updates:**
  ```bash
  python test_push.py
  ```
- **Simulate pairing, requesting app lists, and launching apps:**
  ```bash
  python test_client_req.py
  ```

---

## How Companion Pairing Works

1. **Authentication Flow**: When you run the launcher, a random 6-digit numeric pairing code is generated.
2. **Access Token**: On a successful match, the client receives a secure `UUID` token from the trust manager.
3. **Session Reconnect**: The companion client stores this token locally. For subsequent connections within 24 hours (configurable in settings), authentication is granted automatically without requesting the pairing code again.
4. **Command Routing**: Once authenticated, the companion client can send JSON messages to:
   - Request the list of apps (`get_apps`).
   - Launch a specific program (`launch` with `appId`).
   - Control system volume or screen brightness (`system_action`).