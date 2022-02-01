
from abc import ABC, abstractmethod
import logging
import threading
import errno
import struct
import socket
import time
import subprocess
import sys
import pprint

from ..synth import server as srv
from . import clock as clk
from . import stream as stm
from . import _taskq as tsq
from . import main as _libsc3
from . import netaddr as nad
from . import _osclib as oli
from . import functions as fn
from . import platform as plf


__all__ = ['OscUdpInterface', 'OscTcpInterface', 'OscNrtInterface']


_logger = logging.getLogger(__name__)


class OscInterface(ABC):
    _recv_functions = set()
    _local_endpoints = dict()

    def __init__(self, port=None, port_range=1):
        self._port = port
        self._port_range = port_range if port_range > 0 else 1
        self._socket = None
        self._proto = None

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
    def proto(self):
        return self._proto

    @classmethod
    def add_recv_func(cls, func):
        '''
        Register a callable to be evaluated each time an OSC message arrives.
        Signature of func is:
            msg: OSC message as list.
            time: Time of arrival measured from `main.elapsed_time()`.
            addr: A NetAddr object with sender's address.
            port: Local port as int.
        '''
        cls._recv_functions.add(func)

    @classmethod
    def remove_recv_func(cls, func):
        '''Unregister func callback.'''
        cls._recv_functions.discard(func)

    def _msg_dispatch(self, addr, time, *msg):
        '''
        This method routes all incoming OSC messages to responders.

        Args:
            addr: A tuple (sender_ip:str, sender_port:int).
            time: OSC timetag as 64bits unsigned integer.
            *msg: OSC message as address followed by values.
        '''
        addr = nad.NetAddr(addr[0], addr[1])
        addr._osc_interface = self

        def sched_func():
            for func in type(self)._recv_functions.copy():
                func(list(msg), time, addr, self.port)

        clk.SystemClock.sched(0, sched_func)  # Updates logical time.

    def _handle_request(self, data, address):
        try:
            elapsed_time = _libsc3.main.elapsed_time()
            packet = oli.OscPacket(data)
            for timed_msg in packet.messages:
                if timed_msg.time is None or timed_msg.time == oli.IMMEDIATELY:
                    time = elapsed_time
                else:
                    time = clk.SystemClock.osc_to_elapsed_time(timed_msg.time)
                self._msg_dispatch(
                    address, time,
                    *[timed_msg.message.address,
                    *timed_msg.message.params])
        except:
            _logger.error(
                'Exception happened during processing '
                f'request from {address}',
                exc_info=sys.exc_info())

    def send_msg(self, target, *args):
        '''
        args are values to create one message.
        target is a tuple (hostname, port).
        sclang converts True to 1, False to 0, None and empty lists to 0.
        Non empty lists are converted to blobs containing osc messages or
        bundles. Empty strings are sent unchanged.
        '''
        # Time has to be set here for nested bundles (completion msg case).
        send_time = _libsc3.main.current_tt._seconds
        self._send(self._build_msg(send_time, list(args)), target)

    def send_bundle(self, target, time, *elements):
        '''
        args are lists of values to creae a message or bundle each.
        target is a tuple (hostname, port).
        If time is None the OSC library must send 1 (immediate) as timetag.
        If time is negative it will be substracted from elapsed time and be
        an already late timetag (no check for sign).
        '''
        # Time has to be set here for nested bundles consistency.
        send_time = _libsc3.main.current_tt._seconds
        self._send(self._build_bundle(send_time, [time, *elements]), target)

    @abstractmethod
    def _send(self, msg, target):
        pass

    def _build_msg(self, send_time, arg_list):
        # ['/path', arg1, arg2, ..., argN]
        msg_builder = oli.OscMessageBuilder(arg_list[0])
        for arg in arg_list[1:]:
            if arg is None:
                msg_builder.add_arg(0)
            elif isinstance(arg, bool):
                msg_builder.add_arg(int(arg))
            elif isinstance(arg, list):
                if not arg:
                    msg_builder.add_arg(0)
                elif isinstance(arg[0], str):
                    msg_builder.add_arg(
                        self._build_msg(send_time, arg).dgram)
                elif isinstance(arg[0], (int, float, type(None)))\
                and len(arg) > 1 and isinstance(arg[1], list):
                    msg_builder.add_arg(
                        self._build_bundle(send_time, arg).dgram)
                else:
                    raise ValueError(
                        'lists within messages must be valid '
                        f'OSC messages or bundles: {arg}')
            elif arg == '[':
                msg_builder.args.append(
                    (msg_builder.ARG_TYPE_ARRAY_START, None))
            elif arg == ']':
                msg_builder.args.append(
                    (msg_builder.ARG_TYPE_ARRAY_STOP, None))
            else:
                msg_builder.add_arg(arg)  # Infiere correctamente el resto de los tipos.
        return msg_builder.build()

    def _build_bundle(self, send_time, arg_list):
        # [time, ['/path', arg1, arg2, ..., argN], [...], ...]
        timetag = self._get_timetag(send_time, arg_list[0])
        bndl_builder = oli.OscBundleBuilder(timetag)
        for arg in arg_list[1:]:
            if isinstance(arg[0], str):
                bndl_builder.add_content(self._build_msg(send_time, arg))
            elif isinstance(arg[0], (int, float, type(None))):
                self._check_subtime(arg_list[0], arg[0])
                bndl_builder.add_content(self._build_bundle(send_time, arg))
            else:
                raise ValueError(
                    'elements within bundles must be valid '
                    f'OSC messages or bundles: {arg}')
        return bndl_builder.build()

    @staticmethod
    def _get_timetag(send_time, time):
        if time is None or time < 0.0:
            return oli.IMMEDIATELY
        else:
            time += send_time
            return clk.SystemClock.elapsed_time_to_osc(time)

    @staticmethod
    def _check_subtime(time, subtime):
        # OSC spec. 1.0. This check should be done by _osclib.
        if time is None:
            return
        if subtime is None or time > subtime:
            raise ValueError(
                'nested bundle time must be >= enclosing bundle time')

    def bind(self):
        localhost = socket.gethostbyname('localhost')
        for i in range(self._port_range):
            try:
                bind_addr = (localhost, self._port)
                self._socket.bind(bind_addr)
                type(self)._local_endpoints[bind_addr] = self
                break
            except OSError as e:
                if e.errno == errno.EADDRINUSE and i < self._port_range - 1:
                    self._port += 1
                elif e.errno == errno.EADDRINUSE and i == self._port_range - 1:
                    last = self._port
                    first = last - (self._port_range - 1)
                    if first == last:
                        errstr = (
                            f'[Errno {errno.EADDRINUSE}] port '
                            f'{first} already in use')
                    else:
                        errstr = (
                            f'[Errno {errno.EADDRINUSE}] port range '
                            f'{first}-{last} already in use')
                    err = OSError(errstr)
                    err.errno = errno.EADDRINUSE
                    raise err from e
                else:
                    raise

    def unbind(self):
        bind_addr = self._socket.getsockname()
        if self._socket.type == socket.SOCK_STREAM:
            self._socket.shutdown(socket.SHUT_RDWR)
        else:
            # SOCK_DGRAM recvfrom unblock for Linux.
            self._socket.sendto(b'', bind_addr)
        self._socket.close()
        del type(self)._local_endpoints[bind_addr]


    ### UDP Interface ###

    def start(self):
        pass

    def stop(self):
        pass

    def running(self):
        pass


    ### TCP Interface ###

    def connect(self, target):
        pass

    def try_connect(self, target, timeout=3, on_complete=None, on_failure=None):
        pass

    def disconnect(self):
        pass

    @property
    def is_connected(self):
        return False


    ### NRT Interface ###

    def init(self):
        pass

    def finish(self):
        pass


    def __str__(self):
        return f'{type(self).__name__} port {self._port}'


class OscUdpInterface(OscInterface):
    '''OSC over UDP server.'''

    def __init__(self, port, port_range=1):
        super().__init__(port, port_range)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp_thread = None
        self._running = False
        self._proto = 'udp'

    def start(self):
        if self._running:
            return
        self.bind()
        self._udp_thread = threading.Thread(
            target=self._udp_run, name=str(self))
        self._udp_thread.daemon = True
        self._udp_thread.start()
        _libsc3.main._atexitq.add(
            _libsc3.main._atexitprio.NETWORKING + 1, self.stop)

    def _udp_run(self):
        bind_addr = self._socket.getsockname()
        self._running = True
        while self._running:
            try:
                data, address = self._socket.recvfrom(65536)
                if not data and address == bind_addr:
                    break
                self._handle_request(data, address)
            except OSError as e:
                if self._running:
                    _logger.error(f'{str(self)}: {str(e)}')
                break

    def stop(self):
        if not self._running:
            return
        self._running = False
        self.unbind()
        _libsc3.main._atexitq.remove(self.stop)

    def running(self):
        return self._running

    def _send(self, msg, target):  # override
        self._socket.sendto(msg.dgram, target)


class OscTcpInterface(OscInterface):
    '''
    OSC client over TCP. OscTcpInterface instances aren't reusable.
    '''

    def __init__(self, port, port_range=1):
        super().__init__(port, port_range)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._tcp_thread = None
        self._run_thread = False
        self._is_connected = False
        self._proto = 'tcp'

    def connect(self, target):
        self._socket.connect(target)  # Exception on failure.
        self._is_connected = True  # Not thread safe.
        self._tcp_thread = threading.Thread(
            target=self._tcp_run, name=str(self))
        self._tcp_thread.daemon = True
        self._tcp_thread.start()
        _libsc3.main._atexitq.add(
            _libsc3.main._atexitprio.NETWORKING, self.disconnect)

    def _tcp_run(self):
        self._run_thread = True
        while self._run_thread:
            try:
                data = self._socket.recv(4)
                if not data:
                    self._is_connected = False
                    break
                size = struct.unpack('>i', data)[0]
                data = self._socket.recv(size)
                if not data:
                    self._is_connected = False
                    break
                self._handle_request(data, self._socket.getpeername())
            except OSError as e:
                if self._run_thread:  # Log for not intentional disconnects.
                    _logger.error(f'{str(self)}: {str(e)}')
                self._is_connected = False
                break

    def try_connect(self, target, timeout=3, on_complete=None, on_failure=None):
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
                except OSError as e:
                    if e.errno == errno.EADDRNOTAVAIL:  # Happens when trying to register to the existing server after a boot() fail.
                        yield dt
                    else:
                        raise
            _logger.warning(f"{str(self)} couldn't establish connection")
            fn.value(on_failure, self)

        stm.Routine.run(tcp_connect_func, clk.AppClock)

    def disconnect(self):
        self._run_thread = False
        self._tcp_thread = None
        self._is_connected = False  # Is sync.
        self.unbind()
        _libsc3.main._atexitq.remove(self.disconnect)

    @property
    def is_connected(self):
        return self._is_connected

    def _send(self, msg, _=None):  # override
        self._socket.send(msg.size.to_bytes(4, 'big'))
        self._socket.send(msg.dgram)


class OscNrtInterface(OscInterface):
    def init(self):
        self._osc_score = OscScore()

    def finish(self):  # close?
        self._osc_score.finish()

    @classmethod
    def add_recv_func(cls, func):  # override
        pass  # Exception?

    @classmethod
    def remove_recv_func(cls, func):  # override
        pass  # Exception?

    def _msg_dispatch(self, addr, time, *msg):  # override
        pass  # Exception?

    def send_msg(self, target, *args):  # override
        # In NRT all messages are bundles at current time.
        self.send_bundle(target, 0.0, list(args))

    def send_bundle(self, target, time, *elements):  # override
        # Time is calculated in _build_bundle to support
        # sub-bundles relative time by calling _get_timetag().
        self._osc_score.add([time, *elements])

    @staticmethod
    def _get_timetag(send_time, time):  # override
        # Changes in this method must be synced with OscScore._get_logical_time.
        if time is None or time < 0.0:
            time = 0.0  # IMMEDIATELY is not needed in nrt.
        # In NRT bundle's time generated outside a routine is
        # always absolute time (from zero as reference time).
        if _libsc3.main.current_tt is not _libsc3.main.main_tt:
            time += send_time
        return int(time * clk.SystemClock._SECONDS_TO_OSC)

    def _send(self, msg, target):
        pass


class OscScore():
    class _Entry():
        def __init__(self, bndl, msg):
            self.bndl = bndl
            self.msg = msg
            # *** NOTE: May need to define __eq__ and __hash__ for TaskQueue.

    def __init__(self):
        self._scoreq = tsq.TaskQueue()
        self._lst_score = []
        self._raw_score = bytearray()
        self._finished = False
        self.add([0.0, ["/g_new", 1, 0, 0]])  # Root node.

    @property
    def list(self):
        return self._lst_score[:]

    @property
    def raw(self):
        return self._raw_score[:]

    @property
    def duration(self):
        return self._scoreq.peek(False)[0] * clk.SystemClock._OSC_TO_SECONDS

    def add(self, bndl):
        if self._finished:
            raise Exception('already finished OSC score')
        send_time = _libsc3.main.current_tt._seconds
        msg = _libsc3.main._osc_interface._build_bundle(send_time, bndl)  # Raises Exception.
        msg = msg.size.to_bytes(4, 'big') + msg.dgram
        bndl = self._process_bndl_time(send_time, bndl)
        self._scoreq.add(bndl[0], type(self)._Entry(bndl, msg))

    def _process_bndl_time(self, send_time, bndl):
        # Process time in seconds to store in the score and
        # support sub-bundles relative time like _build_bundle.
        # _check_subtime is done by _build_bundle before calling this method.
        for i, element in enumerate(bndl[1:], 1):
            if isinstance(element[0], (int, float, type(None))):
                bndl[i] = self._process_bndl_time(send_time, element)
            elif not isinstance(element[0], str):
                raise ValueError(
                    'elements within bundles must be valid '
                    f'OSC messages or bundles: {element}')
        bndl = bndl[:]
        bndl[0] = self._get_logical_time(send_time, bndl[0])
        return bndl

    def _get_logical_time(self, send_time, time):
        # Same as OscNrtInterface._get_timetag but in logical time.
        # Changes in this method must be synced with it, or refactored.
        if time is None or time < 0.0:
            time = 0.0
        if _libsc3.main.current_tt is not _libsc3.main.main_tt:
            time += send_time
        return time

    def finish(self, tailtime=0.0):
        if self._finished:
            return
        # This method uses the logical time of its call as the others
        # when called from a routine but when called from ouside it
        # needs to undo the check of _get_timetag and _get_logical_time.
        # Those methods and this one would need refactoring all at once.
        if _libsc3.main.current_tt is _libsc3.main.main_tt:
            tailtime += _libsc3.main.current_tt._seconds
        self.add([tailtime, ['/c_set', 0, 0]])  # Dummy cmd.
        for _, entry in self._scoreq:
            self._lst_score.append(entry.bndl)
            self._raw_score.extend(entry.msg)
        self._finished = True

    def write(self, path):
        if not self._finished:
            self.finish(self.duration)
        with open(path, 'wb') as file:
            file.write(self._raw_score)

    def render(self, path=None, input_file=None, server=None):
        # This method blocks until cmd finish and returns its exit code.
        osc_file = plf.Platform.tmp_dir
        osc_file /= 'SC_' + time.strftime('%Y%m%d_%H%M%S') + '.osc'
        self.write(osc_file)

        server = srv.Server.default if server is None else server
        cmd = [server.options.program]
        cmd.extend(
            server.options.options_list(None, osc_file, input_file, path))

        self._render_proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=sys.stdout,
            stderr=sys.stderr,
            bufsize=1,
            universal_newlines=True)

        try:
            self._render_proc.wait()
            return self._render_proc.poll()
        finally:
            osc_file.unlink()

    def __str__(self):
        return pprint.pformat(self._lst_score)
