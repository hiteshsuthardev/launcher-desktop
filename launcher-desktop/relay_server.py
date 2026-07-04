import asyncio
import json
import random
import string
import websockets

PORT = 8888

# Active sessions: { connectAddress: { "host": websocket, "code": "...", "client": websocket } }
sessions = {}

async def handler(websocket):
    client_type = None
    session_id = None
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue
                
            msg_type = data.get("type")
            
            # 1. Desktop Host Registration
            if msg_type == "register_host":
                code = data.get("code")
                # Generate unique 6-character alphanumeric session ID
                session_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                while session_id in sessions:
                    session_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    
                sessions[session_id] = {
                    "host": websocket,
                    "code": code,
                    "client": None
                }
                client_type = "host"
                print(f"[RELAY SERVER] Registered Host. Session ID: {session_id} | Pairing Code: {code}")
                
                await websocket.send(json.dumps({
                    "type": "session_created",
                    "connectAddress": session_id
                }))
            
            # 2. Mobile Companion Join Session
            elif msg_type == "join_session":
                addr = data.get("connectAddress")
                code = data.get("code")
                device_id = data.get("deviceId", "")
                device_name = data.get("deviceName", "Mobile Client")
                
                print(f"[RELAY SERVER] Client join attempt. Session: '{addr}' | Code: '{code}'")
                
                if addr in sessions and sessions[addr]["code"] == code:
                    session = sessions[addr]
                    session["client"] = websocket
                    session_id = addr
                    client_type = "client"
                    
                    # Notify host desktop that mobile client paired successfully
                    host_conn = session["host"]
                    await host_conn.send(json.dumps({
                        "type": "client_connected",
                        "deviceId": device_id,
                        "deviceName": device_name
                    }))
                    
                    # Send pair confirmation to client
                    await websocket.send(json.dumps({
                        "type": "pair_success",
                        "token": f"relay_session_token_{addr}"
                    }))
                    print(f"[RELAY SERVER] Session '{addr}' successfully paired with client '{device_name}'")
                else:
                    print(f"[RELAY SERVER] Client join failed. Invalid session ID or code: '{addr}' / '{code}'")
                    await websocket.send(json.dumps({
                        "type": "pair_failed"
                    }))
                    break  # Close connection on failure
            
            # 3. Message forwarding
            elif client_type == "host":
                # Forward host response payload directly to paired client
                if session_id in sessions:
                    client_conn = sessions[session_id]["client"]
                    if client_conn:
                        payload = data.get("payload")
                        await client_conn.send(json.dumps(payload))
                        
            elif client_type == "client":
                # Wrap client command and forward to host
                if session_id in sessions:
                    host_conn = sessions[session_id]["host"]
                    if host_conn:
                        await host_conn.send(json.dumps({
                            "type": "forward",
                            "payload": data
                        }))
                        
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"[RELAY SERVER ERROR] Exception: {e}")
    finally:
        # Session cleanup on disconnection
        if client_type == "host" and session_id in sessions:
            print(f"[RELAY SERVER] Host disconnected. Closing session '{session_id}'...")
            client_conn = sessions[session_id]["client"]
            if client_conn:
                try:
                    await client_conn.send(json.dumps({"type": "host_disconnected"}))
                    await client_conn.close()
                except Exception:
                    pass
            del sessions[session_id]
        elif client_type == "client" and session_id in sessions:
            print(f"[RELAY SERVER] Client disconnected from session '{session_id}'.")
            sessions[session_id]["client"] = None
            host_conn = sessions[session_id]["host"]
            if host_conn:
                try:
                    await host_conn.send(json.dumps({"type": "client_disconnected"}))
                except Exception:
                    pass

async def main():
    print("====================================================")
    print("           STANDALONE WEBSOCKET RELAY SERVER        ")
    print("====================================================")
    print(f"Listening on ws://0.0.0.0:{PORT} ...")
    async with websockets.serve(handler, "0.0.0.0", PORT):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
