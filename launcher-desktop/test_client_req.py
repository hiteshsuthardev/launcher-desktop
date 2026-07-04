import asyncio
import json
import websockets

async def test_flow():
    uri = "ws://127.0.0.1:8765"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")
            
            # 1. Pairing
            pair_payload = {
                "type": "join_session",
                "code": "161738",
                "deviceId": "test-device-id-1234",
                "deviceName": "Python Tester"
            }
            print(f"Sending pair payload: {json.dumps(pair_payload)}")
            await websocket.send(json.dumps(pair_payload))
            
            response = await websocket.recv()
            print(f"Received pair response: {response}")
            
            # 2. Get Apps List with Request ID
            req_id_1 = "test-req-1111"
            get_apps_payload = {
                "action": "getAppList",
                "type": "get_apps",
                "requestId": req_id_1
            }
            print(f"Sending get_apps payload with requestId: {req_id_1}")
            await websocket.send(json.dumps(get_apps_payload))
            
            apps_response = await websocket.recv()
            print(f"Received apps response: {apps_response}")
            
            # 3. Launch App with Request ID
            # Let's get the first app's ID from response
            apps_data = json.loads(apps_response)
            apps_list = apps_data.get("apps", [])
            if apps_list:
                app_id = apps_list[0].get("id")
                req_id_2 = "test-req-2222"
                launch_payload = {
                    "type": "launch",
                    "appId": app_id,
                    "requestId": req_id_2
                }
                print(f"Sending launch payload for app {app_id} with requestId: {req_id_2}")
                await websocket.send(json.dumps(launch_payload))
                
                launch_response = await websocket.recv()
                print(f"Received launch response: {launch_response}")
            else:
                print("No apps to launch.")
                
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_flow())
