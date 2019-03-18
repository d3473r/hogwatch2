#!/usr/bin/env python

import os
import sys
import json
import janus
import signal
import logging
import asyncio
import hashlib
import websockets
import pynethogs

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

USERS = set()
loop = asyncio.get_event_loop()
queue = janus.Queue(loop=loop)

def get_hash(websocket):
    return hashlib.sha256(str(hash(websocket)).encode()).hexdigest()

async def consumer(websocket, message):
    data = json.loads(message.replace('\'', '\"'))
    if 'action' in data and 'interface' in data:
        action = data['action']
        interface = data['interface']
        if action == 'add':
            if not interface in websocket.interfaces:
                websocket.interfaces.append(interface)
                logging.info('%s adding interface: %s' % (websocket.id, interface))
                logging.info('%s current interfaces: %s' % (websocket.id, websocket.interfaces))
        elif action == 'remove':
            if interface in websocket.interfaces:
                websocket.interfaces.remove(interface)
                logging.info('%s removing interface: %s' % (websocket.id, interface))
                logging.info('%s current interfaces: %s' % (websocket.id, websocket.interfaces))
        else:
            logging.error('%s unsupported event: %s' % (websocket.id, action))
    else:
        logging.error('%s parameter missing: %s' % (websocket.id, data))

async def consumer_handler(websocket, path):
    try:
        while True:
            message = await websocket.recv()
            await consumer(websocket, message)
    except websockets.exceptions.ConnectionClosed as e:
        pass

async def producer_handler():
    while True:
        message = await queue.async_q.get()
        message_dict = json.loads(message)
        for websocket in USERS:
            if len(websocket.interfaces) > 0:
                if message_dict['device_name'] in websocket.interfaces:
                    await websocket.send(message)
            else:
                await websocket.send(message)

async def register(websocket):
    USERS.add(websocket)

async def unregister(websocket):
    USERS.remove(websocket)

async def handler(websocket, path):
    websocket.interfaces = list()
    websocket.id = get_hash(websocket)
    await register(websocket)
    logging.info('%s connected' % websocket.id)
    try:
        consumer_task = asyncio.ensure_future(consumer_handler(websocket, path))
        producer_task = asyncio.ensure_future(producer_handler())
        done, pending = await asyncio.wait(
            [consumer_task, producer_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    finally:
        logging.info('%s disconnected' % websocket.id)
        await unregister(websocket)

def signal_handler(signal, frame):
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    future = loop.run_in_executor(None, pynethogs.main, queue.sync_q)

    loop.run_until_complete(websockets.serve(handler, '0.0.0.0', 8765))
    loop.run_forever()

if __name__ == '__main__':
    if os.getuid() != 0:
        print('This has to be run as root sorry :/')
    else:
        main()