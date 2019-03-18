#!/usr/bin/env python

import json
import asyncio
import websockets

async def client(uri):
    async with websockets.connect(uri) as websocket:
        # await websocket.send(json.dumps({'action': 'add', 'interface': 'eth0'}))
        # await websocket.send(json.dumps({'action': 'add', 'interface': 'wlan0'}))
        while True:
            print(await websocket.recv())

try:
    asyncio.get_event_loop().run_until_complete(client('ws://localhost:8765'))
except KeyboardInterrupt as e:
        pass