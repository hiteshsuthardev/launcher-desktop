import os
import json
import time
import uuid
from typing import Dict

class TrustedManager:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.data_dir = os.path.join(base_dir, "data")
        else:
            self.data_dir = data_dir

        self.filepath = os.path.join(self.data_dir, "trusted_devices.json")
        self.settings_filepath = os.path.join(self.data_dir, "settings.json")
        
        os.makedirs(self.data_dir, exist_ok=True)
        self.trusted_devices = {}
        self.trust_duration_hours = 24
        
        self.load_settings()
        self.load_devices()

    def load_settings(self):
        """Loads settings from settings.json."""
        if os.path.exists(self.settings_filepath):
            try:
                with open(self.settings_filepath, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    self.trust_duration_hours = settings.get("trust_duration_hours", 24)
            except Exception as e:
                print(f"Error loading settings.json: {e}")
        else:
            self.save_settings(24)

    def save_settings(self, duration_hours: int):
        """Saves settings to settings.json."""
        self.trust_duration_hours = duration_hours
        try:
            with open(self.settings_filepath, "w", encoding="utf-8") as f:
                json.dump({"trust_duration_hours": duration_hours}, f, indent=4)
        except Exception as e:
            print(f"Error saving settings.json: {e}")

    def load_devices(self) -> Dict:
        """Loads trusted devices from the JSON file."""
        if not os.path.exists(self.filepath):
            self.trusted_devices = {}
            self.save_devices()
            return self.trusted_devices
            
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                self.trusted_devices = json.load(f)
        except Exception as e:
            print(f"Error loading trusted_devices.json: {e}")
            self.trusted_devices = {}
        return self.trusted_devices

    def save_devices(self):
        """Saves current trusted devices list to the JSON file."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.trusted_devices, f, indent=4)
        except Exception as e:
            print(f"Error saving trusted_devices.json: {e}")

    def is_device_trusted(self, device_id: str, token: str) -> bool:
        """Verifies if a device ID matches the stored session token and is not expired."""
        if not device_id or not token:
            return False
            
        if device_id in self.trusted_devices:
            dev = self.trusted_devices[device_id]
            # Check token match
            if dev.get("token") != token:
                return False
                
            # Check expiration
            paired_time = dev.get("paired_time", 0.0)
            elapsed_seconds = time.time() - paired_time
            max_seconds = self.trust_duration_hours * 3600
            
            if elapsed_seconds <= max_seconds:
                # Valid connection! Update last-connected timestamp
                dev["last_connected"] = time.time()
                self.save_devices()
                return True
            else:
                # Expired! Revoke automatically
                print(f"[TRUST MANAGER] Device '{dev.get('name')}' connection expired.")
                self.untrust_device(device_id)
        return False

    def trust_device(self, device_id: str, device_name: str) -> str:
        """Adds/registers a device to the trusted list, generates a token, and persists it."""
        if not device_id:
            return ""
            
        token = str(uuid.uuid4())
        now = time.time()
        self.trusted_devices[device_id] = {
            "name": device_name,
            "token": token,
            "paired_time": now,
            "last_connected": now
        }
        self.save_devices()
        print(f"[TRUST MANAGER] Registered trusted device '{device_name}' ({device_id}) with new token.")
        return token

    def untrust_device(self, device_id: str):
        """Removes a device from the trusted list."""
        if device_id in self.trusted_devices:
            del self.trusted_devices[device_id]
            self.save_devices()
