import ctypes
import os
import subprocess
import keyboard
import screen_brightness_control as sbc
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL

# Media key virtual key codes
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_PREV_TRACK = 0xB1

def lock_screen() -> str:
    """Locks the Windows user session."""
    ctypes.windll.user32.LockWorkStation()
    return "Windows session locked"

def volume_up() -> str:
    """Increases system volume by 5%."""
    devices = AudioUtilities.GetSpeakers()
    volume = devices.EndpointVolume
    current = volume.GetMasterVolumeLevelScalar()
    new_vol = min(1.0, current + 0.05)
    volume.SetMasterVolumeLevelScalar(new_vol, None)
    return f"Volume set to {int(new_vol * 100)}%"

def volume_down() -> str:
    """Decreases system volume by 5%."""
    devices = AudioUtilities.GetSpeakers()
    volume = devices.EndpointVolume
    current = volume.GetMasterVolumeLevelScalar()
    new_vol = max(0.0, current - 0.05)
    volume.SetMasterVolumeLevelScalar(new_vol, None)
    return f"Volume set to {int(new_vol * 100)}%"

def volume_mute() -> str:
    """Toggles system mute."""
    devices = AudioUtilities.GetSpeakers()
    volume = devices.EndpointVolume
    muted = volume.GetMute()
    volume.SetMute(not muted, None)
    return "Audio muted" if not muted else "Audio unmuted"

def shutdown_pc() -> str:
    """Initiates PC shutdown with a 5-second delay."""
    # Run shutdown command in background
    res = subprocess.run(["shutdown", "/s", "/t", "5"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if res.returncode != 0:
        if "privilege" in res.stderr.lower() or "access" in res.stderr.lower():
            raise PermissionError("Administrator privileges required to initiate shutdown.")
        raise Exception(res.stderr.strip())
    return "Shutdown scheduled in 5 seconds"

def restart_pc() -> str:
    """Initiates PC restart with a 5-second delay."""
    res = subprocess.run(["shutdown", "/r", "/t", "5"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if res.returncode != 0:
        if "privilege" in res.stderr.lower() or "access" in res.stderr.lower():
            raise PermissionError("Administrator privileges required to initiate restart.")
        raise Exception(res.stderr.strip())
    return "Restart scheduled in 5 seconds"

def sleep_pc() -> str:
    """Suspends the PC (Sleep mode)."""
    # Note: rundll32.exe powrprof.dll,SetSuspendState 0,1,0 puts Windows to sleep
    res = subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if res.returncode != 0:
        raise Exception("Failed to suspend PC.")
    return "PC suspended"

def media_play_pause() -> str:
    """Sends the virtual key code for media Play/Pause."""
    ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 2, 0)  # KEYEVENTF_KEYUP
    return "Media Play/Pause key sent"

def media_next() -> str:
    """Sends the virtual key code for media Next Track."""
    ctypes.windll.user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_MEDIA_NEXT_TRACK, 0, 2, 0)
    return "Media Next Track key sent"

def media_previous() -> str:
    """Sends the virtual key code for media Previous Track."""
    ctypes.windll.user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 0, 0)
    ctypes.windll.user32.keybd_event(VK_MEDIA_PREV_TRACK, 0, 2, 0)
    return "Media Previous Track key sent"

def brightness_up() -> str:
    """Increases screen brightness by 10%."""
    try:
        current = sbc.get_brightness()
        if isinstance(current, list):
            current = current[0]
        new_bright = min(100, current + 10)
        sbc.set_brightness(new_bright)
        return f"Brightness set to {new_bright}%"
    except Exception as e:
        raise Exception(f"Brightness control not supported on this monitor: {e}")

def brightness_down() -> str:
    """Decreases screen brightness by 10%."""
    try:
        current = sbc.get_brightness()
        if isinstance(current, list):
            current = current[0]
        new_bright = max(0, current - 10)
        sbc.set_brightness(new_bright)
        return f"Brightness set to {new_bright}%"
    except Exception as e:
        raise Exception(f"Brightness control not supported on this monitor: {e}")

def get_wifi_state() -> str:
    """Uses netsh to parse current state of the Wi-Fi adapter."""
    try:
        # Check specific adapter by name Wi-Fi first
        res = subprocess.run(["netsh", "interface", "show", "interface", "name=Wi-Fi"], 
                             capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if "Enabled" in res.stdout:
            return "on"
        elif "Disabled" in res.stdout:
            return "off"
            
        # Fallback: scan interface list for generic wireless names
        res = subprocess.run(["netsh", "interface", "show", "interface"], 
                             capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        for line in res.stdout.splitlines():
            if "wi-fi" in line.lower() or "wireless" in line.lower():
                if "Enabled" in line:
                    return "on"
                elif "Disabled" in line:
                    return "off"
    except Exception:
        pass
    return "unknown"

def toggle_wifi() -> str:
    """Toggles the Wi-Fi interface between Enabled and Disabled (needs admin privileges)."""
    current = get_wifi_state()
    adapter_name = "Wi-Fi"
    
    # Try to find specific adapter name
    try:
        res = subprocess.run(["netsh", "interface", "show", "interface"], 
                             capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        for line in res.stdout.splitlines():
            if "wi-fi" in line.lower() or "wireless" in line.lower():
                parts = [p.strip() for p in line.split() if p.strip()]
                if parts:
                    adapter_name = parts[-1]
                    break
    except Exception:
        pass
        
    new_state = "enabled" if current == "off" else "disabled"
    
    # Run toggle command
    res = subprocess.run(
        ["netsh", "interface", "set", "interface", adapter_name, f"admin={new_state}"],
        capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
    )
    
    # Check for administrator privilege error
    if "administrator" in res.stderr.lower() or "privilege" in res.stderr.lower() or res.returncode != 0:
        raise PermissionError("Administrator privileges required to toggle Wi-Fi adapter.")
        
    final_state = get_wifi_state()
    return f"Wi-Fi is now {final_state}"


def set_volume_scalar(val: float) -> str:
    """Sets master volume to a scalar value between 0.0 and 1.0."""
    devices = AudioUtilities.GetSpeakers()
    volume = devices.EndpointVolume
    val = max(0.0, min(1.0, val))
    volume.SetMasterVolumeLevelScalar(val, None)
    return f"Volume set to {int(val * 100)}%"

def get_volume_scalar() -> float:
    """Returns the current master volume level scalar (0.0 to 1.0)."""
    try:
        devices = AudioUtilities.GetSpeakers()
        volume = devices.EndpointVolume
        return volume.GetMasterVolumeLevelScalar()
    except Exception:
        return 0.5

def set_brightness_value(val: int) -> str:
    """Sets screen brightness directly to a percentage (0 to 100)."""
    try:
        sbc.set_brightness(val)
        return f"Brightness set to {val}%"
    except Exception as e:
        raise Exception(f"Brightness control failed: {e}")

def get_brightness_value() -> int:
    """Returns current monitor brightness (0 to 100)."""
    try:
        current = sbc.get_brightness()
        if isinstance(current, list):
            current = current[0]
        return int(current)
    except Exception:
        return 50

def execute_system_action(action: str, value=None) -> tuple:
    """
    Executes a system control command.
    Returns a tuple of (success_bool, message_str).
    """
    import pythoncom
    try:
        pythoncom.CoInitialize()
        try:
            if action == "lock_screen":
                msg = lock_screen()
            elif action == "volume_up":
                msg = volume_up()
            elif action == "volume_down":
                msg = volume_down()
            elif action == "volume_mute":
                msg = volume_mute()
            elif action == "set_volume" and value is not None:
                msg = set_volume_scalar(float(value))
            elif action == "shutdown":
                msg = shutdown_pc()
            elif action == "restart":
                msg = restart_pc()
            elif action == "sleep":
                msg = sleep_pc()
            elif action == "media_play_pause":
                msg = media_play_pause()
            elif action == "media_next":
                msg = media_next()
            elif action == "media_previous":
                msg = media_previous()
            elif action == "brightness_up":
                msg = brightness_up()
            elif action == "brightness_down":
                msg = brightness_down()
            elif action == "set_brightness" and value is not None:
                msg = set_brightness_value(int(value))
            elif action == "wifi_toggle":
                msg = toggle_wifi()
            else:
                return False, f"Unknown system action: '{action}'"
            return True, msg
        finally:
            pythoncom.CoUninitialize()
    except PermissionError as pe:
        return False, str(pe)
    except Exception as e:
        return False, f"Error: {str(e)}"
