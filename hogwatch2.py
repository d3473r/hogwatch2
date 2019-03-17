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

class WebSocketServerProtocolWrapper:
    interfaces = []

    def __init__(self, webSocketServerProtocol):
        self.webSocketServerProtocol = webSocketServerProtocol

def get_wrapper_hash(wrapper):
    return hashlib.sha256(str(hash(wrapper.webSocketServerProtocol)).encode()).hexdigest()

async def consumer(wrapper, message):
    data = json.loads(message)
    sha = get_wrapper_hash(wrapper)
    if 'action' in data and 'interface' in data:
        action = data['action']
        interface = data['interface']
        if action == 'add':
            if not interface in wrapper.interfaces:
                wrapper.interfaces.append(interface)
                logging.info('%s adding interface: %s' % (sha, interface))
                logging.info('%s current interfaces: %s' % (sha, wrapper.interfaces))
        elif action == 'remove':
            if interface in wrapper.interfaces:
                wrapper.interfaces.remove(interface)
                logging.info('%s removing interface: %s' % (sha, interface))
                logging.info('%s current interfaces: %s' % (sha, wrapper.interfaces))
        else:
            logging.error('%s unsupported event: %s' % (sha, action))
    else:
        logging.error('%s parameter missing: %s' % (sha, data))

async def consumer_handler(wrapper, path):
    try:
        while True:
            message = await wrapper.webSocketServerProtocol.recv()
            await consumer(wrapper, message)
    except websockets.exceptions.ConnectionClosed as e:
        pass

async def producer_handler(wrapper, path):
    while True:
        message = await queue.async_q.get()
        message_dict = json.loads(message)
        if len(wrapper.interfaces) > 0:
            if message_dict['device_name'] in wrapper.interfaces:
                await wrapper.webSocketServerProtocol.send(message)
        else:
            await wrapper.webSocketServerProtocol.send(message)

async def register(wrapper):
    USERS.add(wrapper)

async def unregister(wrapper):
    USERS.remove(wrapper)

async def handler(websocket, path):
    wrapper = WebSocketServerProtocolWrapper(websocket)
    await register(wrapper)
    logging.info('%s connected' % get_wrapper_hash(wrapper))
    try:
        consumer_task = asyncio.ensure_future(consumer_handler(wrapper, path))
        producer_task = asyncio.ensure_future(producer_handler(wrapper, path))
        done, pending = await asyncio.wait(
            [consumer_task, producer_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    finally:
        logging.info('%s disconnected' % get_wrapper_hash(wrapper))
        await unregister(wrapper)

def signal_handler(signal, frame):
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    future = loop.run_in_executor(None, pynethogs.main, queue.sync_q)

    loop.run_until_complete(websockets.serve(handler, 'localhost', 8765))
    loop.run_forever()

if __name__ == '__main__':
    if os.getuid() != 0:
        print('This has to be run as root sorry :/')
    else:
        main()