#!/usr/bin/env python

import os
import json
import ctypes

LIBNETHOGS_VERSION = "0.8.5-54-gac5af1d"

NETHOGS_APP_ACTION_SET = 1
NETHOGS_APP_ACTION_REMOVE = 2

CMPFUNC_t = None

class NethogsMonitorRecord(ctypes.Structure):
    _fields_ = [
        ('record_id', ctypes.c_int), 
        ('name', ctypes.c_char_p), 
        ('pid', ctypes.c_int), 
        ('uid', ctypes.c_uint), 
        ('device_name', ctypes.c_char_p),
        ('sent_bytes', ctypes.c_ulonglong),
        ('recv_bytes', ctypes.c_ulonglong),
        ('sent_kbs', ctypes.c_float),
        ('recv_kbs', ctypes.c_float)]

    def __repr__(self):
        return json.dumps({'record_id': self.record_id, 'name': self.name.decode('utf-8'), 'pid': self.pid, 'uid': self.uid, 'device_name': self.device_name.decode('utf-8'), 'sent_bytes': self.sent_bytes, 'recv_bytes': self.recv_bytes, 'sent_kbs': self.sent_kbs, 'recv_kbs': self.recv_kbs})


def main(queue):
    global CMPFUNC_t

    libnethogs =  ctypes.CDLL("lib/libnethogs.so.%s" % LIBNETHOGS_VERSION)

    NethogsMonitorRecord_ptr = ctypes.POINTER(NethogsMonitorRecord)

    CMPFUNC_t = ctypes.CFUNCTYPE(None, ctypes.c_int, NethogsMonitorRecord_ptr)

    def callback(action, update):
        u = str(update.contents)
        a = json.loads(u)
        a['action'] = action
        queue.put(json.dumps(a))

    dist_callback = CMPFUNC_t(callback)

    libnethogs.nethogsmonitor_loop.argtypes = [CMPFUNC_t, ctypes.c_bool]
    libnethogs.nethogsmonitor_loop.restype = ctypes.c_int
    libnethogs.nethogsmonitor_loop(dist_callback, None)