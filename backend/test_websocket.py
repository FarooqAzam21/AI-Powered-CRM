#!/usr/bin/env python3
"""Test WebSocket connection to Phase 8 dashboard"""

import asyncio
import websockets
import json


async def test_websocket():
    """Test WebSocket connection"""
    try:
        uri = "ws://localhost:8000/api/v1/ws/1"
        print(f"Connecting to {uri}...")
        
        async with websockets.connect(uri) as ws:
            print("✅ WebSocket connected!")
            
            # Wait for initial connection message
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2)
                print(f"✅ Received: {msg}")
                
                # Try to parse as JSON
                try:
                    data = json.loads(msg)
                    print(f"✅ Parsed JSON: {json.dumps(data, indent=2, default=str)}")
                except:
                    print(f"⚠️  Message is not JSON: {msg[:100]}")
            except asyncio.TimeoutError:
                print("❌ Timeout waiting for connection confirmation")
                return
            
            # Send subscription
            sub_msg = json.dumps({
                "action": "subscribe",
                "channel": "deals"
            })
            await ws.send(sub_msg)
            print(f"📤 Sent subscription: {sub_msg}")
            
            # Receive confirmation
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=2)
                print(f"✅ Response: {response}")
                data = json.loads(response)
                print(f"✅ Parsed response: {json.dumps(data, indent=2, default=str)}")
            except asyncio.TimeoutError:
                print("❌ Timeout waiting for subscription confirmation")
            
    except ConnectionRefusedError:
        print("❌ Connection refused - is server running?")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket())

