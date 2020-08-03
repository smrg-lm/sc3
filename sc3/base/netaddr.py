"""NetAddr.sc"""

import ipaddress
import socket

from ..seq import stream as stm
from . import main as _libsc3
from . import utils as utl
from . import responsedefs as rdf
from . import _oscinterface as osci


__all__ = ['NetAddr']  #, 'BundleNetAddr']


class NetAddr():
    # use_doubles = False
    # broadcast_flag = False

    # From Wikipedia: "The field size sets a theoretical limit of 65,535 bytes
    # (8 byte header + 65,527 bytes of data) for a UDP datagram. However the
    # actual limit for the data length, which is imposed by the underlying
    # IPv4 protocol, is 65,507 bytes (65,535 − 8 byte UDP header − 20 byte
    # IP header)".
    _MAX_UDP_DGRAM_SIZE = 65507
    _SYNC_BNDL_DGRAM_SIZE = 36  # Size of bundle(latency, ['/sync', id]) dgram.

    def __init__(self, hostname, port):
        if hostname is None:
            self._addr = 0  # Server:in_process
        else:
            self._addr = int(ipaddress.IPv4Address(hostname))  # Exception if invalid.
        self._hostname = hostname
        self._port = port
        self._target = (hostname, port)
        self._tcp_interface = None

    @property
    def hostname(self):
        return self._hostname

    @property
    def addr(self):
        return self._addr

    @property
    def port(self):
        return self._port

    @property
    def proto(self):
        return self._osc_interface.proto

    @property
    def is_local(self):
        return self.match_lang_ip(self._hostname)

    @property
    def local_end_point(self):  # bind_addr
        if self._osc_interface.socket:
            return type(self)(*self._osc_interface.socket.getsockname())

    @property
    def _osc_interface(self):
        return self._tcp_interface or _libsc3.main._osc_interface

    @staticmethod
    def lang_port():
        return _libsc3.main._osc_interface.port

    @staticmethod
    def match_lang_ip(ipstring):
        # if ipaddress.IPv4Address(self._addr).is_loopback:
        if ipstring == '127.0.0.1':
            return True
        addr_info = socket.getaddrinfo(socket.gethostname(), None)
        for item in addr_info:
            if item[4][0] == ipstring:
                return True
        return False


    ### TCP Connections ###

    def connect(self, on_complete=None, on_failure=None,
                local_port=None, port_range=10, timeout=3):
        # Async.
        if self.is_connected:
            self.disconnect()
        self._tcp_interface = osci.OscTcpInterface(
            local_port or self.lang_port() + 1, port_range)
        self._tcp_interface.bind()
        self._tcp_interface.try_connect(
            self._target, timeout, on_complete, on_failure)

    def disconnect(self):
        # Sync.
        self._tcp_interface.disconnect()
        self._tcp_interface = None

    @property
    def is_connected(self):
        return self._tcp_interface and self._tcp_interface.is_connected


    def has_bundle(self):
        return False

    # def send_raw(self, raw_bytes):
    #     # send a raw message without timestamp to the addr.
    #     self._osc_interface.send_raw(self._target, raw_bytes)

    def send_msg(self, *args):
        self._osc_interface.send_msg(self._target, *args)

    def send_bundle(self, time, *args):
        self._osc_interface.send_bundle(self._target, time, *args)

    def send_clumped_bundles(self, time, *args):
        if self._calc_bndl_dgram_size(args) > self._MAX_UDP_DGRAM_SIZE:
            for item in self._clump_bundle(args):
                if time is not None:
                    time += 1e-9  # One nanosecond later each.
                self.send_bundle(time, *item)
        else:
            self.send_bundle(time, *args)

    def send_status_msg(self):
        self._osc_interface.send_msg(self._target, '/status')

    def recover(self):
        return self

    def sync(self, condition=None, bundle=None, latency=None):
        condition = condition or stm.Condition()
        if bundle is None:
            id = self._make_sync_responder(condition)
            self.send_bundle(latency, ['/sync', id])
            yield from condition.wait()
        else:
            sync_size = self._SYNC_BNDL_DGRAM_SIZE
            max_size = self._MAX_UDP_DGRAM_SIZE - sync_size
            if self._calc_bndl_dgram_size(bundle) > max_size:
                for item in self._clump_bundle(bundle, max_size):
                    id = self._make_sync_responder(condition)
                    item.append(['/sync', id])
                    self.send_bundle(latency, *item)
                    if latency is not None:
                        latency += 1e-9  # One nanosecond later each.
                    yield from condition.wait()
            else:
                id = self._make_sync_responder(condition)
                bundle = bundle[:]
                bundle.append(['/sync', id])
                self.send_bundle(latency, *bundle)
                yield from condition.wait()

    def _make_sync_responder(self, condition):
        id = utl.UniqueID.next()

        def resp_func(msg, *_):
            if msg[1] == id:
                resp.free()
                condition.test = True
                condition.signal()

        resp = rdf.OSCFunc(resp_func, '/synced', self)
        return id

    def _clump_bundle(self, elements, size=8192):
        elist = []
        for e in elements:
            if isinstance(e[0], str):
                elist.append((self._calc_msg_dgram_size(e), e))
            else:
                elist.append((self._calc_bndl_dgram_size(e), e))
        res = []
        clump = []
        acc_size = 16  # Bundle prefix + Timetag bytes.
        for s, e in elist:
            if acc_size + s >= size:
                res.append(clump)
                clump = []
                acc_size = 16  # Bundle prefix + Timetag bytes.
            acc_size += s
            clump.append(e)
        if clump:
            res.append(clump)
        return res

    def _calc_bndl_dgram_size(self, bndl):
        # Argument bndl is the content without Timetag: [[], [], ...].
        res = 16  # Bundle prefix + Timetag bytes.
        for element in bndl:
            res += 4  # Element size bytes.
            if isinstance(element[0], str):  # message
                res += self._calc_msg_dgram_size(element)
            else:  # bundle
                res += self._calc_bndl_dgram_size(bndl)
        return res

    def _calc_msg_dgram_size(self, msg):
        res = self._strpad4(len(bytes(msg[0], 'ascii')))  # Address.
        res += self._strpad4(len(msg[1:]) + 1)  # Type tag string.
        for val in msg[1:]:
            if isinstance(val, str):
                res += self._strpad4(len(val))
            elif isinstance(val, list):
                # sc3 don't send osc arrays, they are msgs converted to blobs.
                res += self._calc_msg_dgram_size(val) + 4  # Blob size bytes.
            else:
                res += 4  # Everything else (sent by sc3, no doubles).
        return res

    @staticmethod
    def _strpad4(n):
        # Pad to 4 or add null if mod is zero.
        return n + 4 - (n & 3)

    def __eq__(self, other):
        if type(self) == type(other):
            return self._target == other._target
        else:
            return False

    def __hash__(self):
        return hash((type(self), hash(self._target)))

    def __repr__(self):
        return f"{type(self).__name__}('{self.hostname}', {self.port})"


# BUG: hay que implementar para server
# class BundleNetAddr(NetAddr):
#     ...
