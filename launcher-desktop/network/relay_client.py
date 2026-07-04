import asyncio
import json
import datetime
import websockets
from PySide6.QtCore import QThread, Signal

def log_msg(tag: str, msg: str):
    """Utility to print log messages with formatted timestamps."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{tag}] {msg}")


class RelayClientThread(QThread):
    # Signals to communicate events back to the PySide6 UI thread
    launch_requested = Signal(str)      # Emits app ID to trigger launch in GUI
    client_connected = Signal(str)      # Emits client device name to update status dot
    client_disconnected = Signal(str)   # Emits client/relay name on disconnect
    session_created = Signal(str)       # Emits connectAddress (alphanumeric session ID)

    def __init__(self, relay_url: str, pairing_code: str, app_manager, trusted_manager, parent=None):
        super().__init__(parent)
        self.relay_url = relay_url
        self.pairing_code = pairing_code
        self.app_manager = app_manager
        self.trusted_manager = trusted_manager
        self.loop = None
        self.websocket = None
        self.running = True
        self.connect_address = ""

    def update_pairing_code(self, new_code: str):
        """Updates the active pairing code and re-registers with the relay server."""
        self.pairing_code = new_code
        log_msg("RELAY CLIENT", f"Pairing code updated to: '{new_code}'")
        if self.websocket and self.loop:
            asyncio.run_coroutine_threadsafe(self.send_registration(), self.loop)

    async def send_registration(self):
        """Sends the host registration payload to the relay server."""
        if self.websocket:
            log_msg("RELAY CLIENT", f"Registering host session with code: '{self.pairing_code}'...")
            try:
                await self.websocket.send(json.dumps({
                    "type": "register_host",
                    "code": self.pairing_code
                }))
            except Exception as e:
                log_msg("RELAY CLIENT WARNING", f"Failed to send host registration: {e}")

    def run(self):
        # Create a new event loop for the thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        async def connection_loop():
            while self.running:
                log_msg("RELAY CLIENT", f"Connecting to relay server at: {self.relay_url}...")
                try:
                    async with websockets.connect(self.relay_url) as ws:
                        self.websocket = ws
                        log_msg("RELAY CLIENT", "Connected successfully to relay server.")
                        
                        # Register as the host on connect
                        await self.send_registration()
                        
                        async for message in ws:
                            try:
                                data = json.loads(message)
                            except json.JSONDecodeError:
                                continue
                                
                            msg_type = data.get("type")
                            
                            if msg_type == "session_created":
                                self.connect_address = data.get("connectAddress")
                                log_msg("RELAY CLIENT", f"Session established. Connect Address: '{self.connect_address}'")
                                self.session_created.emit(self.connect_address)
                                
                            elif msg_type == "client_connected":
                                dev_name = data.get("deviceName", "Mobile Companion")
                                dev_id = data.get("deviceId", "")
                                log_msg("RELAY CLIENT", f"Mobile companion connected: '{dev_name}' ({dev_id})")
                                self.client_connected.emit(dev_name)
                                
                            elif msg_type == "client_disconnected":
                                log_msg("RELAY CLIENT", "Mobile companion disconnected.")
                                self.client_disconnected.emit("Client")
                                
                            elif msg_type == "forward":
                                # Extract payload sent from the client
                                payload = data.get("payload", {})
                                client_msg_type = payload.get("type")
                                log_msg("RELAY CLIENT ACTION", f"Received client command: '{client_msg_type}'")
                                
                                # Process and compute response
                                response_payload = await self.process_client_message(payload)
                                if response_payload:
                                    # Send response payload back through the relay
                                    await ws.send(json.dumps({
                                        "type": "send_to_client",  # Handled transparently by the server
                                        "payload": response_payload
                                    }))
                                    
                except Exception as e:
                    if self.running:
                        log_msg("RELAY CLIENT WARNING", f"Relay disconnect or connection error: {e}")
                        self.websocket = None
                        self.connect_address = ""
                        self.session_created.emit("")
                        self.client_disconnected.emit("Relay Server")
                    
                if not self.running:
                    break
                    
                # Reconnect attempt back-off interval of 5 seconds
                for _ in range(50):
                    if not self.running:
                        break
                    await asyncio.sleep(0.1)

        try:
            self.loop.run_until_complete(connection_loop())
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log_msg("RELAY CLIENT ERROR", f"Relay client loop exception: {e}")

    async def process_client_message(self, data: dict) -> dict:
        """Processes the client commands and returns the matching response payloads."""
        msg_type = data.get("type")
        
        if msg_type == "get_apps":
            apps = self.app_manager.get_apps()
            return {
                "type": "apps_list",
                "apps": apps
            }
        elif msg_type == "launch":
            app_id = data.get("appId")
            app = self.app_manager.get_app(app_id)
            if app:
                self.launch_requested.emit(app_id)
                return {
                    "type": "launch_result",
                    "status": "success"
                }
            else:
                return {
                    "type": "launch_result",
                    "status": "error"
                }
        elif msg_type == "system_action":
            action_name = data.get("action")
            value = data.get("value")
            from core.system_controls import execute_system_action
            success, result_msg = execute_system_action(action_name, value)
            return {
                "type": "system_action_result",
                "action": action_name,
                "status": "success" if success else "error",
                "message": result_msg
            }
        return None

    def stop(self):
        self.running = False
        log_msg("RELAY CLIENT SHUTDOWN", "Requesting relay client shutdown...")
        if self.websocket and self.loop:
            future = asyncio.run_coroutine_threadsafe(self.websocket.close(), self.loop)
            try:
                future.result(timeout=2.0)
            except Exception:
                pass
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.wait()
