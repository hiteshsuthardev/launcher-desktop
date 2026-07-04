import asyncio
import json
import websockets

async def listen_loop():
    uri = "ws://127.0.0.1:8765"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")
            
            # Send pairing payload (using current active code)
            pair_payload = {
                "type": "join_session",
                "code": "510210",  # We'll need to read the latest code from pairing_code.txt
                "deviceId": "test-device-id-5678",
                "deviceName": "Push Tester"
            }
            # Read latest code from pairing_code.txt
            try:
                with open("data/pairing_code.txt", "r") as f:
                    pair_payload["code"] = f.read().strip()
            except:
                pass
                
            print(f"Sending pair payload with code: {pair_payload['code']}")
            await websocket.send(json.dumps(pair_payload))
            
            async for message in websocket:
                data = json.loads(message)
                print(f"\n[CLIENT RECEIVED] Msg type: {data.get('type')}")
                if data.get("type") == "apps":
                    print(f"Received apps update! Count: {len(data.get('apps', []))}")
                else:
                    print(f"Message: {message[:200]}")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(listen_loop())
