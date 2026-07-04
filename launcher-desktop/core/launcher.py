import os
import subprocess


def launch_app(exe_path: str) -> bool:
    """Launches an application executable in the background."""
    if not exe_path or not os.path.exists(exe_path):
        print(f"Error: Executable not found at '{exe_path}'")
        return False
        
    try:
        cwd = os.path.dirname(exe_path)
        # Use subprocess.Popen to launch asynchronously without blocking
        subprocess.Popen([exe_path], cwd=cwd if cwd else None)
        return True
    except Exception as e:
        print(f"Error executing {exe_path}: {e}")
        return False
