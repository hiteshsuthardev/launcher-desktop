import os
import asyncio
import json
import socket
import datetime
import websockets
from PySide6.QtCore import QThread, Signal

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable, just triggers OS routing to find local IP
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

class LocalServerThread(QThread):
    # Signals to communicate events back to the PySide6 UI thread
    launch_requested = Signal(str)      # Emits app ID to trigger launch in GUI
    client_connected = Signal(str)      # Emits client device name to update status dot
    client_disconnected = Signal(str)   # Emits client name on disconnect
    server_started = Signal(str, int)   # Emits (ip, port) when server starts

    def __init__(self, pairing_code: str, app_manager, trusted_manager, parent=None):
        super().__init__(parent)
        self.pairing_code = pairing_code
        self.app_manager = app_manager
        self.trusted_manager = trusted_manager
        self.loop = None
        self.server = None
        self.running = True
        self.port = 8765
        self.local_ip = get_local_ip()
        self.authenticated_client = None  # Holds the currently paired active websocket connection

    def update_pairing_code(self, new_code: str):
        """Updates the active pairing code used for client verification."""
        self.pairing_code = new_code
        print(f"[LOCAL SERVER] Pairing code updated to: '{new_code}'")

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        async def handler(websocket):
            peer_address = websocket.remote_address[0]
            print(f"[LOCAL SERVER] Connection attempt from {peer_address}")
            is_authenticated = False
            client_name = "Mobile Client"
            
            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        continue
                        
                    msg_type = data.get("type")
                    
                    if not is_authenticated:
                        # First message must be join_session to authenticate/pair
                        if msg_type == "join_session":
                            code = data.get("code")
                            token = data.get("token")
                            device_id = data.get("deviceId", peer_address)
                            client_name = data.get("deviceName", "Mobile Companion")
                            
                            # Reconnection logic using token:
                            if token and device_id:
                                if self.trusted_manager.is_device_trusted(device_id, token):
                                    is_authenticated = True
                                    self.authenticated_client = websocket
                                    self.client_connected.emit(client_name)
                                    
                                    import time
                                    expiry_timestamp = int((time.time() + self.trusted_manager.trust_duration_hours * 3600) * 1000)
                                    await websocket.send(json.dumps({
                                        "type": "pair_success",
                                        "token": token,
                                        "expiry": expiry_timestamp
                                    }))
                                    print(f"[LOCAL SERVER] Companion reconnected using session token: {client_name}")
                                    continue
                            
                            # Normal pairing using access code:
                            code_str = str(code).strip() if code is not None else ""
                            pairing_code_str = str(self.pairing_code).strip()
                            
                            if code_str == pairing_code_str:
                                is_authenticated = True
                                self.authenticated_client = websocket
                                self.client_connected.emit(client_name)
                                
                                # Register as trusted device and get a new token
                                new_token = self.trusted_manager.trust_device(device_id, client_name)
                                
                                import time
                                expiry_timestamp = int((time.time() + self.trusted_manager.trust_duration_hours * 3600) * 1000)
                                await websocket.send(json.dumps({
                                    "type": "pair_success",
                                    "token": new_token,
                                    "expiry": expiry_timestamp
                                }))
                                print(f"[LOCAL SERVER] Companion paired successfully: {client_name}")
                            else:
                                print(f"[LOCAL SERVER] Companion pairing failed: invalid code '{code}' or token expired")
                                await websocket.send(json.dumps({
                                    "type": "pair_failed",
                                    "message": "Invalid pairing code or token expired"
                                }))
                                await websocket.close()
                                break
                        else:
                            print(f"[LOCAL SERVER] Rejected message of type '{msg_type}' - connection not authenticated")
                            await websocket.send(json.dumps({
                                "type": "pair_failed",
                                "message": "Authentication required"
                            }))
                            await websocket.close()
                            break
                    else:
                        # Connection is authenticated, forward and process commands
                        # Note: The mobile companion wraps commands directly or forwards them.
                        # For direct connection, we can support client's command format directly.
                        # The mobile app might send {"type": "get_apps"}, {"type": "launch"}, etc.
                        # Or it might wrap them in a payload. We handle both for robustness.
                        payload = data.get("payload") if msg_type == "forward" else data
                        cmd_type = payload.get("type") if payload else msg_type
                        
                        print(f"[LOCAL SERVER] Received command: '{cmd_type}'")
                        response_payload = await self.process_client_message(payload or data)
                        
                        if response_payload:
                            # Forward the requestId from the original request
                            req_id = data.get("requestId")
                            if req_id:
                                response_payload["requestId"] = req_id
                            
                            # Send response back to the client.
                            await websocket.send(json.dumps(response_payload))
                            
            except websockets.exceptions.ConnectionClosed:
                pass
            except Exception as e:
                print(f"[LOCAL SERVER ERROR] Error in connection handler: {e}")
            finally:
                if is_authenticated:
                    print(f"[LOCAL SERVER] Paired client '{client_name}' disconnected.")
                    self.authenticated_client = None
                    self.client_disconnected.emit(client_name)

        async def start_server():
            # Try to bind on ports from 8765 to 8775
            for p in range(8765, 8776):
                try:
                    self.server = await websockets.serve(handler, "0.0.0.0", p)
                    self.port = p
                    print(f"[LOCAL SERVER] Server started successfully on ws://{self.local_ip}:{self.port}")
                    self.server_started.emit(self.local_ip, self.port)
                    return True
                except OSError:
                    print(f"[LOCAL SERVER WARNING] Port {p} is in use, retrying next port...")
            return False

        async def main_loop():
            success = await start_server()
            if not success:
                print("[LOCAL SERVER ERROR] Could not bind to any port in the range 8765-8775.")
                # Fallback to local loopback if all else fails
                try:
                    self.server = await websockets.serve(handler, "127.0.0.1", 8765)
                    self.port = 8765
                    print(f"[LOCAL SERVER] Server fallback started on ws://127.0.0.1:8765")
                    self.server_started.emit("127.0.0.1", 8765)
                except Exception as e:
                    print(f"[LOCAL SERVER CRITICAL ERROR] Server failed to start on fallback: {e}")
                    return
            
            while self.running:
                await asyncio.sleep(0.1)
                
            if self.server:
                self.server.close()
                await self.server.wait_closed()
                print("[LOCAL SERVER] Server shutdown complete.")
            self.loop.stop()

        try:
            self.loop.run_until_complete(main_loop())
        except asyncio.CancelledError:
            pass
        except RuntimeError as re:
            if "Event loop stopped before Future completed" not in str(re) and "Event loop is closed" not in str(re):
                print(f"[LOCAL SERVER ERROR] Server event loop error: {re}")
        except Exception as e:
            print(f"[LOCAL SERVER ERROR] Server event loop error: {e}")

    def get_apps_payload(self) -> dict:
        """Helper to get list of apps formatted with base64 encoded icons."""
        raw_apps = self.app_manager.get_apps()
        apps_with_icons = []
        import base64
        for app in raw_apps:
            icon_b64 = ""
            icon_path = app.get("icon_path", "")
            if icon_path:
                full_icon_path = os.path.join(self.app_manager.data_dir, icon_path)
                if os.path.exists(full_icon_path):
                    try:
                        with open(full_icon_path, "rb") as img_f:
                            icon_b64 = base64.b64encode(img_f.read()).decode("utf-8")
                    except Exception as e:
                        print(f"[LOCAL SERVER] Failed to read/encode icon: {e}")
            
            apps_with_icons.append({
                "id": app.get("id"),
                "name": app.get("name"),
                "icon": icon_b64
            })
        
        return {
            "type": "apps",
            "apps": apps_with_icons
        }

    def push_apps_to_companion(self):
        """Pushes the current list of apps (with base64 icons) to the connected companion client."""
        if self.authenticated_client and self.loop:
            payload = self.get_apps_payload()
            # Run the coroutine thread-safely in the event loop thread
            future = asyncio.run_coroutine_threadsafe(
                self.authenticated_client.send(json.dumps(payload)),
                self.loop
            )
            def callback(f):
                try:
                    f.result()
                except Exception as ex:
                    print(f"[LOCAL SERVER ERROR] Failed to push apps update: {ex}")
            future.add_done_callback(callback)
            print("[LOCAL SERVER] Pushed updated app list to companion.")

    async def process_client_message(self, data: dict) -> dict:
        """Processes client commands and executes local actions."""
        msg_type = data.get("type") or data.get("action")
        
        if msg_type in ("get_apps", "getAppList"):
            return self.get_apps_payload()
        elif msg_type == "launch":
            app_id = data.get("appId")
            app = self.app_manager.get_app(app_id)
            if app:
                self.launch_requested.emit(app_id)
                return {
                    "type": "launch_result",
                    "appId": app_id,
                    "success": True
                }
            else:
                return {
                    "type": "launch_result",
                    "appId": app_id,
                    "success": False,
                    "error": "App not found"
                }
        elif msg_type == "system_action":
            action_name = data.get("action")
            value = data.get("value")
            from core.system_controls import execute_system_action
            success, result_msg = execute_system_action(action_name, value)
            return {
                "type": "system_action_result",
                "action": action_name,
                "success": success,
                "error": result_msg if not success else ""
            }
        return None

    def stop(self):
        """Stops the WebSocket server and event loop."""
        self.running = False
        self.wait()
