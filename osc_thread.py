'''
INTENTO OBSOLETO, LIBLO ES MUCHO MÁS FÁCIL
Se encarga de:
    * loop osc para cliente y servidor
'''

import threading
from osc4py3.as_eventloop import * # is safe they say

class OSCThread(threading.Thread):

    def __init__(self):
        super(OSCThread, self).__init__()
        self.name = "supercollie client"
        self.msgEvent = threading.Event()
        self._stopEvent = threading.Event()
        self._sleepTime = 0.001

    def run(self):
        osc_startup()
        while not self._stopEvent.is_set():
            self.msgEvent.wait(self._sleepTime)
            osc_process()
            self.msgEvent.clear()
        osc_terminate()

    def stop(self):
        self._stopEvent.set()

    def add_sc_client(self, clientport):
        # atrapar: OSError: [Errno 98] Address already in use. y unregister
        # porque: ValueError: OSC channel/peer name 'supercollie' already used.
        osc_udp_server("127.0.0.1", clientport, "supercollie") # receiver

    def add_handler(self):
        pass

    def remove_handler(self):
        pass

    def add_sc_erver(self, server):
        osc_udp_client(server.hostaddr, server.port, server.name)

    def remove_sc_server(self, server):
        pass
