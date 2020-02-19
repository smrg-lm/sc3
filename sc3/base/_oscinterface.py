
from abc import ABC, abstractmethod
import threading
import atexit
import errno
import struct
import socket
import logging

from ..seq import clock as clk
from ..seq import stream as stm
from . import main as _libsc3
from . import netaddr as nad
from . import _osclib as oli
from . import functions as fn


__all__ = ['OscUdpInterface', 'OscTcpInteface']


_logger = logging.getLogger(__name__)


class OscInterface(ABC):
    def __init__(self, port, port_range):
        self._port = port
        self._port_range = port_range
        self._socket = None
        self._recv_functions = set()

    @property
    def port(self):
        return self._port

    @property
    def port_range(self):
        return self._port_range

    @property
    def socket(self):
        return self._socket

    @property
    def recv_functions(self):
        return self._recv_functions

    def add_recv_func(self, func):
        '''
        Register a callable to be evaluated each time an OSC message arrives.
        Signature of func is:
            msg: OSC message as list.
            time: Time of arrival meassured from main.elapsed_time().
            addr: A NetAddr object with sender's address.
            port: Local port as int.
        '''
        self._recv_functions.add(func)

    def remove_recv_func(self, func):
        '''Unregister func callback.'''
        self._recv_functions.discard(func)

    def recv(self, addr, time, *msg):
        '''
        This method is the handler of all incoming OSC messages or bundles
        to be registered once for each OSC server interface in subclasses.

        Args:
            addr: A tuple (sender_ip:str, sender_port:int).
            time: OSC timetag as 64bits unsigned integer.
            *msg: OSC message as address followed by values.
        '''
        # _libsc3.main.update_logical_time()  # *** BUG: Clock.sched actualiza abajo, VER TIEMPO LÓGICO.
        addr = nad.NetAddr(addr[0], addr[1])

        if time is None:
            time = _libsc3.main.elapsed_time()  # *** BUG: VER TIEMPO LÓGICO, probar en sclang recibiendo desde una rutina con tempoclock.
        else:
            time = clk.SystemClock.osc_to_elapsed_time(time)

        def sched_func():
            for func in self.recv_functions:
                func(list(msg), time, addr, self.port)

        clk.AppClock.sched(0, sched_func)  # *** BUG: SystemClock?

    def send_msg(self, target, *args):
        '''
        args are values to create one message.
        target is a tuple (hostname, port).
        sclang converts True to 1, False to 0, None and empty lists to 0.
        Non empty lists are converted to blobs containing osc messages or
        bundles. Empty strings are sent unchanged.
        '''
        msg = self._build_msg(list(args))
        self.send(msg, target)

    def send_bundle(self, target, time, *args):
        '''
        args are lists of values to creae a message or bundle each.
        target is a tuple (hostname, port).
        If time is None the OSC library must send 1 (immediate) as timetag.
        If time is negative it will be substracted from elapsed time and be
        an already late timetag (no check for sign).
        '''
        bndl = self._build_bundle([time, *args])
        self.send(bndl, target)

    @abstractmethod
    def send(self, msg, target):
        pass

    def _build_msg(self, arg_list):  # ['/path', arg1, arg2, ..., argN]
        msg_builder = oli.OscMessageBuilder(arg_list.pop(0))
        for arg in arg_list:
            if arg is None:
                msg_builder.add_arg(0)
            elif isinstance(arg, bool):
                msg_builder.add_arg(int(arg))
            elif isinstance(arg, list):
                if len(arg) == 0:
                    msg_builder.add_arg(0)
                elif isinstance(arg[0], str):
                    msg_builder.add_arg(self._build_msg(arg).dgram)
                elif isinstance(arg[0], (int, float, type(None))):
                    msg_builder.add_arg(self._build_bundle(arg).dgram)
                else:
                    raise oli.OscMessageBuildError(
                        'lists within messages must be a valid '
                        f'OSC message or bundle: {arg}')
            elif arg == '[':
                msg_builder.args.append(
                    (msg_builder.ARG_TYPE_ARRAY_START, None))
            elif arg == ']':
                msg_builder.args.append(
                    (msg_builder.ARG_TYPE_ARRAY_STOP, None))
            else:
                msg_builder.add_arg(arg)  # Infiere correctamente el resto de los tipos.
        return msg_builder.build()

    def _build_bundle(self, arg_list):  # [time, ['/path', arg1, arg2, ..., argN], ['/path', arg1, arg2, ..., argN], ...]
        bndl_builder = oli.OscBundleBuilder(arg_list.pop(0) or oli.IMMEDIATELY)  # Only None is IMMEDIATELY, zero can't reach this stage through addr.send_bundle.
        for arg in arg_list:
            if isinstance(arg[0], str):
                bndl_builder.add_content(self._build_msg(arg))
            elif isinstance(arg[0], (int, float, type(None))):
                bndl_builder.add_content(self._build_bundle(arg))
            else:
                raise oli.OscMessageBuildError(
                    'lists within messages must be a valid '
                    f'OSC message or bundle: {arg}')
        return bndl_builder.build()

    # *** *** BUG: volver estos métodos a NetAddr de alguna manera.
    def msg_size(self, arg_list): # ['/path', arg1, arg2, ..., argN]
        msg = _build_msg(arg_list)  # *** BUG: el problema es no estar construyendo el mensaje dos veces igual.
        return msg.size  # *** BUG: este método está demás, hay que hacer todo en quién llama y guardar el msg.

    # *** BUG: ver _NetAddr_BundleSize
    def bundle_size(self, arg_list): # [time, ['/path', arg1, arg2, ..., argN], ['/path', arg1, arg2, ..., argN], ...]
        bndl = _build_bundle(arg_list)  # *** BUG: el problema es no estar construyendo el atado dos veces igual.
        return bndl.size  # *** BUG: este método está demás, hay que hacer todo en quién llama y guardar el bndl.


    ### UDP Interface ###

    def start(self):
        pass

    def stop(self):
        pass

    def running(self):
        pass


    ### TCP Interface ###

    def bind(self):
        pass

    def connect(self, target):
        pass

    def try_connect(self, target, on_complete=None, on_failure=None, timeout=3):
        pass

    def disconnect(self):
        pass

    @property
    def is_connected(self):
        pass


class OscUdpInterface(OscInterface):
    '''OSC over UDP server.'''

    def __init__(self, port=57120, port_range=10):
        super().__init__(port, port_range)
        self._server = None
        self._server_thread = None
        self._running = False

    @property
    def socket(self):
        return self._server.socket if self._server else None

    def start(self):
        if self._running:
            return
        for i in range(self.port_range):
            try:
                self._server = oli.OSCUDPServer(
                    ('127.0.0.1', self._port), oli.UDPHandler)
                break
            except OSError as e:
                if e.errno == errno.EADDRINUSE and i < self.port_range - 1:
                    self._port += 1
                elif e.errno == errno.EADDRINUSE and i == self.port_range - 1:
                    err = OSError(
                        f'[Errno {errno.EADDRINUSE}] Port range already '
                        f'in use: {self.port}-{self.port_range - 1}')
                    err.errno = errno.EADDRINUSE
                    raise err
                else:
                    raise e
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            name=f'{type(self).__name__} port {self._port}')
        self._server_thread.daemon = True
        self._server_thread.start()
        self._running = True
        atexit.register(self.stop)

    def stop(self):
        if not self._running:
            return
        self._server.shutdown()
        self._server = None
        self._running = False
        self._server_thread = None
        atexit.unregister(self.stop)

    def running(self):
        return self._running

    def send(self, msg, target):
        self._server.socket.sendto(msg.dgram, target)


class OscTcpInteface(OscInterface):
    '''
    OSC client over TCP. OscTcpInteface instances aren't reusable.
    '''

    def __init__(self, port=57120, port_range=10):
        super().__init__(port, port_range)
        self._tcp_thread = None
        self._run_thread = False
        self._is_connected = False

    def bind(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        for i in range(self.port_range):
            try:
                self._socket.bind(('127.0.0.1', self._port))
                break
            except OSError as e:
                if e.errno == errno.EADDRINUSE and i < self.port_range - 1:
                    self._port += 1
                elif e.errno == errno.EADDRINUSE and i == self.port_range - 1:
                    err = OSError(
                        f'[Errno {errno.EADDRINUSE}] Port range already '
                        f'in use: {self.port}-{self.port_range - 1}')
                    err.errno = errno.EADDRINUSE
                    raise err
                else:
                    raise e

    def connect(self, target):
        self._socket.connect(target)  # Exception on failure.
        self._is_connected = True  # Not thread safe.
        self._tcp_thread = threading.Thread(
            target=self._tcp_run, name=str(self))
        self._tcp_thread.daemon = True
        self._tcp_thread.start()
        atexit.register(self.disconnect)

    def _tcp_run(self):
        self._run_thread = True
        while self._run_thread:
            try:
                data = self._socket.recv(4)
                if len(data) == 0:
                    self._is_connected = False
                    break
                size = struct.unpack('>i', data)[0]
                data = self._socket.recv(size)
                if len(data) == 0:
                    self._is_connected = False
                    break
            except OSError as e:
                _logger.error(f'{str(self)}: {str(e)}')
                break
            packet = oli.OscPacket(data)
            for timed_msg in packet.messages:
                msg = [timed_msg.message.address, *timed_msg.message.params]
                _libsc3.main._osc_interface.recv(
                    self._socket.getpeername(), timed_msg.time, *msg)

    def try_connect(self, target, on_complete=None, on_failure=None, timeout=3):
        def tcp_connect_func():
            dt = 0.2
            attempts = int(timeout / dt)
            for i in range(attempts):
                try:
                    self.connect(target)
                    fn.value(on_complete, self)
                    return
                except ConnectionRefusedError:
                    yield dt
            _logger.warning(f"{str(self)} couldn't establish connection")
            fn.value(on_failure, self)

        stm.Routine.run(tcp_connect_func, clk.AppClock)

    def disconnect(self):
        self._socket.shutdown(socket.SHUT_RDWR)
        self._is_connected = False  # Is sync.
        self._socket.close()  # OSError if underlying error.
        self._run_thread = False
        self._tcp_thread = None
        atexit.unregister(self.disconnect)

    def send(self, msg, _=None):
        self._socket.send(msg.size.to_bytes(4, 'big'))
        self._socket.send(msg.dgram)

    @property
    def is_connected(self):
        return self._is_connected

    def __str__(self):
        return f'{type(self).__name__} port {self._port}'
