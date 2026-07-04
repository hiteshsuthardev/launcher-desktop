import os
import json
import uuid
import shutil
from typing import List, Dict, Optional

class AppManager:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # Locate relative to this file: launcher-desktop/data
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.data_dir = os.path.join(base_dir, "data")
        else:
            self.data_dir = data_dir

        self.apps_json_path = os.path.join(self.data_dir, "apps.json")
        self.icons_dir = os.path.join(self.data_dir, "icons")
        
        # Ensure directories exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.icons_dir, exist_ok=True)
        
        self.apps = []
        self.load_apps()

    def load_apps(self) -> List[Dict]:
        """Loads apps from the apps.json file."""
        if not os.path.exists(self.apps_json_path):
            self.apps = []
            self.save_apps()
            return self.apps
            
        try:
            with open(self.apps_json_path, "r", encoding="utf-8") as f:
                self.apps = json.load(f)
        except Exception as e:
            print(f"Error loading apps.json: {e}")
            self.apps = []
        return self.apps

    def save_apps(self):
        """Saves current apps list to apps.json."""
        try:
            with open(self.apps_json_path, "w", encoding="utf-8") as f:
                json.dump(self.apps, f, indent=4)
        except Exception as e:
            print(f"Error saving apps.json: {e}")

    def get_apps(self) -> List[Dict]:
        """Returns the list of apps."""
        return self.apps

    def get_app(self, app_id: str) -> Optional[Dict]:
        """Returns a single app by ID."""
        for app in self.apps:
            if app["id"] == app_id:
                return app
        return None

    def add_app(self, exe_path: str, custom_name: Optional[str] = None) -> Optional[Dict]:
        """Adds a new application, extracts its icon, and saves the list."""
        if not os.path.exists(exe_path):
            print(f"Executable path does not exist: {exe_path}")
            return None

        # Determine display name
        base_name = os.path.basename(exe_path)
        name, _ = os.path.splitext(base_name)
        display_name = custom_name if custom_name else name

        app_id = str(uuid.uuid4())
        
        # Generate icon path
        icon_filename = f"{app_id}.png"
        icon_path = os.path.join(self.icons_dir, icon_filename)
        
        # Extract icon using our extractor (implemented next)
        from core.icon_extractor import extract_icon
        icon_extracted = extract_icon(exe_path, icon_path)
        
        # Relative icon path for portability (stored relative to data_dir)
        rel_icon_path = os.path.join("icons", icon_filename).replace("\\", "/")

        if not icon_extracted:
            # If extraction failed, we can use a default icon or placeholder
            rel_icon_path = "icons/default.png"
            # Create a fallback placeholder if needed
            self._create_default_icon_if_missing()

        new_app = {
            "id": app_id,
            "name": display_name,
            "exe_path": exe_path,
            "icon_path": rel_icon_path
        }
        
        self.apps.append(new_app)
        self.save_apps()
        return new_app

    def remove_app(self, app_id: str) -> bool:
        """Removes an application and its icon, then saves."""
        app = self.get_app(app_id)
        if not app:
            return False

        # Remove icon file if it exists and is not the default icon
        icon_path = os.path.join(self.data_dir, app["icon_path"])
        if os.path.exists(icon_path) and "default.png" not in app["icon_path"]:
            try:
                os.remove(icon_path)
            except Exception as e:
                print(f"Could not remove icon file: {e}")

        self.apps = [a for a in self.apps if a["id"] != app_id]
        self.save_apps()
        return True

    def rename_app(self, app_id: str, new_name: str) -> bool:
        """Renames an application display name and saves."""
        app = self.get_app(app_id)
        if not app:
            return False
            
        app["name"] = new_name
        self.save_apps()
        return True

    def _create_default_icon_if_missing(self):
        """Creates a default fallback icon in data/icons/default.png if not present."""
        default_path = os.path.join(self.icons_dir, "default.png")
        if not os.path.exists(default_path):
            # Create a simple default visual indicator (blank or solid color QPixmap later)
            # For now we'll write a simple 1x1 transparent/colored PNG or let PySide create it
            # We'll write a solid color 64x64 PNG using a placeholder or let UI load a built-in resources icon
            pass
