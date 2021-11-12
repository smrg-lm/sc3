"""NetAddr.sc"""

import ipaddress
import socket

from . import stream as stm
from . import main as _libsc3
from . import builtins as bi
from . import responders as rpd
from . import _oscinterface as osci


__all__ = ['NetAddr', 'BundleNetAddr']


class NetAddr():
    '''
    NetAddr's objects represent *target* addresses to send messages to, or
    establish connections with, using UDP or TCP transport protocols.

    When initialized in real time, the library sets up a default UDP port
    with the default interface to send and receive OSC data. The default port
    is 57120 but it can change if it is being used by another application.
    The actual port can be queried through the 'lang_port()' static method.

    More UDP ports can be open as local endpoints with 'main.open_udp_port'
    and closed with 'main.close_udp_port'. To change the output UDP port
    of a NetAddr object use 'change_output_port'. TCP connections can be
    stablished with 'connect' and closed with 'disconnect' from an existing
    NetAddr object. Note that differently from UDP protocol, which is
    connectionless, TCP connections are client connections that can't be used
    for serving purposes as independent ports.
    '''

    # use_doubles = False
    # broadcast_flag = False

    # From Wikipedia: "The field size sets a theoretical limit of 65,535 bytes
    # (8 byte header + 65,527 bytes of data) for a UDP datagram. However the
    # actual limit for the data length, which is imposed by the underlying
    # IPv4 protocol, is 65,507 bytes (65,535 − 8 byte UDP header − 20 byte
    # IP header)".
    _MAX_UDP_DGRAM_SIZE = 65504  # It is 4 instead of 7 (pad4).
    _SYNC_BNDL_DGRAM_SIZE = 36  # Size of bundle(latency, ['/sync', id]) dgram.

    def __init__(self, hostname, port):
        if hostname is None:
            self._addr = 0  # Server:in_process
        else:
            self._addr = int(ipaddress.IPv4Address(hostname))  # Exception if invalid.
        self._hostname = hostname
        self._port = port
        self._target = (hostname, port)
        self._osc_interface = _libsc3.main._osc_interface

    @property
    def hostname(self):
        '''Address name.'''
        return self._hostname

    @property
    def addr(self):
        '''Address name as int.'''
        return self._addr

    @property
    def port(self):
        '''Address port.'''
        return self._port

    @property
    def proto(self):
        '''Return the transport protocol.'''
        return self._osc_interface.proto

    @property
    def is_local(self):
        '''Return true if the address is in localhost.'''
        return ipaddress.IPv4Address(self._hostname).is_loopback

    @property
    def local_endpoint(self):
        '''Return the bind address as a tuple (hostname, port).'''
        if self._osc_interface.socket:
            return self._osc_interface.socket.getsockname()

    def change_output_port(self, port):
        '''Change UDP local endpoint.'''
        with _libsc3.main._main_lock:
            local_addr = (socket.gethostbyname('localhost'), port)
            new_interface = type(
                _libsc3.main._osc_interface)._local_endpoints.get(local_addr)
        if new_interface is None:
            raise Exception(f'port {port} is not open')
        if self._osc_interface.proto == 'tcp' or new_interface == 'tcp':
            raise Exception("can't change output port from/to TCP")
        self._osc_interface = new_interface
        self._port = port

    @staticmethod
    def lang_port():
        '''Return the default UPD port of the language.'''
        return _libsc3.main._osc_interface.port

    @staticmethod
    def lang_endpoints():
        '''Return a list of all active local endpoints as (hostname, port, proto).'''
        with _libsc3.main._main_lock:
            return [
                (*k, v.proto) for k, v in
                type(_libsc3.main._osc_interface)._local_endpoints.items()]


    ### TCP Connections ###

    def connect(self, on_complete=None, on_failure=None,
                local_port=None, timeout=3):
        '''Stablish a TCP connection to this address.'''
        # Async.
        with _libsc3.main._main_lock:
            if self._osc_interface.proto == 'tcp'\
            and self._osc_interface.is_connected:
                self.disconnect()
            self._osc_interface = osci.OscTcpInterface(
                local_port or self.lang_port() + 1, 100)
            self._osc_interface.bind()
            self._osc_interface.try_connect(
                self._target, timeout, on_complete, on_failure)

    def disconnect(self):
        '''Close TCP connection to this address.'''
        if self._osc_interface is _libsc3.main._osc_interface:
            return
        # Sync.
        with _libsc3.main._main_lock:
            self._osc_interface.disconnect()
            self._osc_interface = _libsc3.main._osc_interface

    @property
    def is_connected(self):
        '''Return True if a TCP connection is stablished.'''
        return self._osc_interface.is_connected


    def has_bundle(self):
        '''
        Polymorphic method used to differentiate NetAddr from BundleNetAddr
        by avoiding type checking.
        '''
        return False

    def send_msg(self, *args):
        '''Send an OSC message to the server.

        Parameters
        ----------
        *args: items
            OSC address followed by zero or more values that compose the
            message.

        Notes
        -----
        Invoked as::

          addr.send_msg('/osc_addr', p1, p2, ...)
        '''

        self._osc_interface.send_msg(self._target, *args)

    def send_bundle(self, time, *elements):
        '''Send an OSC bundle to the server.

        Parameters
        ----------
        time: int | float | None
            Latency time from now. If `time` is None or negative the timetag
            is set to immediately. Nested bundles can have their own latency
            but must be >= to the enclosing bundle latency.
        *elements: lists
            Each element is a list in the form of an OSC message or bundle.

        .. note: Nested bundles only work with supernova, for scsynth the
        generated bundle can be only composed of messages.

        Notes
        -----
        Elements lists representing messages or bundles. Invoked as::

          addr.send_bundle(1, ['/msg', ...], [1.2, ['/bndl', ...], ...], ...)
        '''

        self._osc_interface.send_bundle(self._target, time, *elements)

    def send_clumped_bundles(self, time, *elements):
        '''
        This method is used to send bundles larger than UDP datagram size
        as successive sub-clumped packages.
        '''
        if self._calc_bndl_dgram_size(elements) > self._MAX_UDP_DGRAM_SIZE:
            for item in self._clump_bundle(elements):
                if time is not None:
                    time += 1e-9  # One nanosecond later each.
                self.send_bundle(time, *item)
        else:
            self.send_bundle(time, *elements)

    def send_status_msg(self):
        '''Send '/status' message to the server.

        The server will respond with '/status.reply'.
        '''

        self._osc_interface.send_msg(self._target, '/status')

    def sync(self, condition=None, latency=None, elements=None):
        '''
        Generator method that internally manages server's '/sync'
        message. Because it's used to synchronize bundles sent
        to the server it is primarly used through Server's ``sync``
        wrapper method.

        Parameters
        ----------
        condition: Condition
            An optional instance of Condition that will be used to
            wait for the reply.
        latancy: int | float
            Bundle's latency as in ``send_bundle``.
        elements: list
            A list of lists as OSC messages which will be sent
            before the '/sync' message.
        '''

        condition = condition or stm.Condition()
        if elements is None:
            id = self._make_sync_responder(condition)
            self.send_bundle(latency, ['/sync', id])
            yield from condition.wait()
        else:
            sync_size = self._SYNC_BNDL_DGRAM_SIZE
            max_size = self._MAX_UDP_DGRAM_SIZE - sync_size
            if self._calc_bndl_dgram_size(elements) > max_size:
                for item in self._clump_bundle(elements, max_size):
                    id = self._make_sync_responder(condition)
                    item.append(['/sync', id])
                    self.send_bundle(latency, *item)
                    if latency is not None:
                        latency += 1e-9  # One nanosecond later each.
                    yield from condition.wait()
            else:
                id = self._make_sync_responder(condition)
                elements = list(elements)
                elements.append(['/sync', id])
                self.send_bundle(latency, *elements)
                yield from condition.wait()

    def _make_sync_responder(self, condition):
        id = bi.uid()

        def resp_func(msg, *_):
            if msg[1] == id:
                resp.free()
                condition.test = True
                condition.signal()

        resp = rpd.OscFunc(resp_func, '/synced', self)
        return id

    def _clump_bundle(self, elements, size=8192):
        elist = []
        for e in elements:
            if isinstance(e[0], str):
                elist.append((self._calc_msg_dgram_size(e), e))
            elif isinstance(e[0], (int, float)):  # bundle
                elist.append((self._calc_bndl_dgram_size(e[1:]), e))
            else:
                raise ValueError(
                    'elements within bundles must be valid OSC '
                    f'messages or bundles, received: {e}')
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

    def _calc_bndl_dgram_size(self, elements):
        # Argument elements is the content without Timetag: [[], [], ...].
        res = 16  # Bundle prefix + Timetag bytes.
        for e in elements:
            res += 4  # Element size bytes.
            if isinstance(e[0], str):  # message
                res += self._calc_msg_dgram_size(e)
            elif isinstance(e[0], (int, float)):  # bundle
                res += self._calc_bndl_dgram_size(e[1:])
            else:
                raise ValueError(
                    'elements within bundles must be valid OSC '
                    f'messages or bundles, received: {e}')
        return res

    def _calc_msg_dgram_size(self, msg):
        res = self._strpad4(len(bytes(msg[0], 'ascii')))  # Address.
        res += self._strpad4(len(msg[1:]) + 1)  # Type tag string.
        for val in msg[1:]:
            if isinstance(val, str):
                res += self._strpad4(len(val))
            elif isinstance(val, (bytes, bytearray, memoryview)):
                res += len(val) + 4  # Blob size bytes.
            elif isinstance(val, list):
                # Arrays are messages converted to blobs.
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


class BundleNetAddr(NetAddr):
    # Important difference: This class is a context manager. forkIfNeeded
    # can't be implemented, addr.sync() uses it in sclang. Here sync calls are
    # handled different doing yield from directly within the with statement.
    '''
    This class is a context manager that acts as a proxy of the current
    NetAddr and collects single messages to be sent as a bundle. It's main
    use is through 'bind' method of the server objects.
    '''

    class _SYNC_FLAG(): pass

    def __init__(self, target, arg_list=None, send=True):
        if isinstance(target, NetAddr):
            self._save_addr = target
            self._server = None
        else:  # Assumes it's a Server to avoid the import.
            self._save_addr = target.addr
            self._server = target
        super().__init__(self._save_addr._hostname, self._save_addr._port)
        self._bundle = arg_list or []
        self._send = send
        self._last_sync = -1

    def has_bundle(self):
        return True

    # def send_raw(self, rawlst):

    def send_msg(self, *args):
        self._bundle.append(list(args))

    def send_bundle(self, time, *elements):
        self._bundle.extend(list(elements))  # Discard time.

    def send_clumped_bundles(self, time, *elements):
        self._bundle.extend(list(elements))  # Discard time.

    def send_status_msg(self):
        pass  # // Ignore status message.

    def sync(self, condition=None, latency=None, elements=None):
        if self._send:
            self._send_last_bundle()
            yield from self._save_addr.sync(None, latency, elements)
        self._last_sync = len(self._bundle)
        self._bundle.append([self._SYNC_FLAG, latency, elements])

    def _send_last_bundle(self):
        time = self._server.latency if self._server else None
        bundle = self._bundle[self._last_sync+1:]
        if bundle:
            self._save_addr.send_clumped_bundles(time, *bundle)

    def _split_bundles(self, time):
        res = []
        curr = [time]
        for item in self._bundle:
            if item[0] is self._SYNC_FLAG:
                if item[2] is not None:
                    curr.extend(item[2])
                res.append(curr)
                curr = [item[1]]
            else:
                curr.append(item)
        res.append(curr)
        return res

    def get_bundle(self, time=None):
        '''Return all bundled messages so far.'''
        if self._last_sync == -1:
            return [time, *self._bundle]
        else:
            return self._split_bundles(time)

    def __enter__(self):
        if self._server:
            self._server._addr = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._server:
            self._server._addr = self._save_addr
        if exc_type is None and self._send:
            self._send_last_bundle()
