"""Server.sc"""

import enum
import subprocess
import threading
import logging
import os
import time
import errno

from ..base import main as _libsc3
from ..base import utils as utl
from ..base import classlibrary as clb
from ..base import netaddr as nad
from ..base import model as mdl
from ..base import systemactions as sac
from ..base import functions as fn
from ..base import platform as plf
from ..base import stream as stm
from ..base import clock as clk
from . import _engine as eng
from . import _serverstatus as sst
from . import _nodewatcher as ndw
from . import _volume as vlm
from . import recorder as rcd
from . import node as nod
from . import _graphparam as gpp


__all__ = ['s', 'Server', 'ServerOptions']


_logger = logging.getLogger(__name__)


s = None
'''Default server global variable.'''


class Defaults(enum.Enum):
    '''Default command values for server options.

    '''

    UDP_PORT = ('-u', None)  # mutex -t, opt int
    TCP_PORT = ('-t', None)  # mutex -u, opt int

    BIND_ADDRESS = ('-B', '127.0.0.1')  # opt str
    MAX_LOGINS = ('-l', 64)  # opt int
    PASSWORD = ('-p', None)  # opt str
    ZEROCONF = ('-R', 1)  # RENDEZVOUS, boolean

    RESTRICTED_PATH = ('-P', None)  # opt str
    UGEN_PLUGINS_PATH = ('-U', None)  # opt str

    CONTROL_BUSES = ('-c', 16384)  # # opt int, num_control_bus_channels
    AUDIO_BUSES = ('-a', 1024)  # # opt int, num_audio_bus_channels
    INPUT_CHANNELS = ('-i', 8)  # opt int, num_input_bus_channels
    OUTPUT_CHANNELS = ('-o', 8)  # opt int, num_output_bus_channels
    BLOCK_SIZE = ('-z', 64)  # opt int
    BUFFERS = ('-b', 1024)  # opt int, num_buffers
    MAX_NODES = ('-n', 1024)  # opt int
    MAX_SYNTHDEFS = ('-d', 1024)  # opt int, max_synth_defs
    RT_MEMORY = ('-m', 8192)  # opt int, mem_size
    WIRES = ('-w', 64)  # opt int, num_wire_bufs
    RGENS = ('-r', 64)  # opt int, num_rgens
    LOAD_SYNTHDEFS = ('-D', 1)  # opt bool, load_defs

    HW_DEVICE_NAME = ('-H', None)  # opt str
    HW_BUFFER_SIZE = ('-Z', 0)  # opt int, hardware_buffer_size
    SAMPLE_RATE = ('-S', 0)  # opt int, supernova differs: 44100
    NRT = ('-N', None)  # mode flag
    VERBOSE = ('-V', 0)  # opt int

    # Supernova only.
    MEMORY_LOCKING = ('-L', None)  # mode flag
    THREADS = ('-T', 4)  # opt int
    USE_SYSTEM_CLOCK = ('-C', 1)  # opt bool

    # Darwin only.
    INPUT_STREAMS = ('-I', None)  # opt str, input_streams_enabled
    OUTPUT_STREAMS = ('-O', None)  # opt str, output_streams_enabled

    def __init__(self, flag, default):
        self.flag = flag
        self.default = default


class ServerOptions():
    '''Encapsulates commandline and other server options.

    Attributes
    ----------
    program : str
        Command name of the server.
    protocol : str
        Transport protocol of the server, either 'udp' or 'tcp'.
    bind_address : str
        The IP address that the server's TCP or UDP socket is listening
        on. The default value is '127.0.0.1', meaning only listen to
        OSC messages on localhost.
    max_logins : int
        Indicate the maximum number of clients which can simultaneously
        receive notifications from the server. When using TCP this is
        also the maximum number of simultaneous connections. This is
        also used by the language to split ranges of nodes, buffers, or
        busses. In multi-client situations you will need to set this to
        at least the number of clients you wish to allow. This must be
        the same in the Server instances on every client.
        The default is 1.
    password : str
        Set servers' session password for TCP connections. When using
        TCP, the session password must be the first command sent. UDP
        ports never require passwords, so for security use TCP.
        The default is `None` (no password).
    zeroconf : bool
        Indicate whether or not the server should publish its port
        using zero configuration networking, to facilitate network
        interaction. This is `True` by default. If you find
        unacceptable delays (beachballing) upon server boot, you can
        try setting this to false.
    restricted_path : str
        Restrict the system paths in which the server is allowed to
        read/write files when running. If `None` (default) no
        restrictions are applied. Otherwise, set it as a string
        representing a single path.
    ugen_plugins_path : str
        A path or a list of paths. If not `None`, the standard paths
        are **not** searched for plugins. Default is `None`.

    control_buses : int
        The number of internal control rate busses.
        The default is 16384.
    audio_buses : int
        The number of internal audio rate busses.
        The default is 1024.
    input_channels : int
        The number of audio input bus channels. This need not
        correspond to the number of hardware inputs.
        The default is 2.
    output_channels : int
        The number of audio output bus channels. This need not
        correspond to the number of hardware outputs (this can be
        useful for instance in the case of recording).
        The default is 2.
    block_size : int
        The number of samples in one control period.
        The default is 64.
    buffers : int
        The number of global sample buffers available.
        The default is 1024.
    max_nodes : int
        The maximum number of nodes. The default is 1024.
    max_synthdefs : int
        The maximum number of synthdefs. The default is 1024.
    rt_memory : int
        The number of kilobytes of real time memory allocated to the
        server. This memory is used to allocate synths and any memory
        that unit generators themselves allocate (for instance in the
        case of delay ugens which do not use buffers, such as CombN),
        and is separate from the memory used for buffers. Setting this
        too low is a common cause of 'exception in real time: alloc
        failed' errors. The default is 8192.
    wires : int
        The maximum number of buffers that are allocated to
        interconnect unit generators. (Not to be confused with the
        global sample buffers represented by Buffer.) This sets the
        limit of complexity of SynthDefs that can be loaded at runtime.
        This value will be automatically increased if a more complex
        synthdef is loaded at startup, but it cannot be increased
        thereafter without rebooting. The default is 64.
    rgens : int
        The number of seedable random number generators.
        The default is 64.
    load_synthdefs : bool
        Indicate whether or not to load the synth definitions in the
        default synthdefs folder (or anywhere set in the environment
        variable SC_SYNTHDEF_PATH) at startup. The default is `True`.
    hw_device_name : str | tuple(str, str)
        A string to choose I/O device by name or a tuple of two strings
        for a different input and output device. Default is `None` and
        will use the system's default input and output.
    hw_buffer_size : int
        The preferred hardware buffer size. If not `None` the server
        program will attempt to set the hardware buffer frame size.
        Not all sizes are valid. See the documentation of your audio
        hardware for details. Default value is `None`.
    sample_rate : int
        The preferred sample rate. If not `None` the server app will
        attempt to set the sample rate of the hardware. The hardware
        has to support the sample rate that you choose.
    verbose : int
        Control the verbosity of server messages. A value of 0 is
        normal behaviour, -1 suppresses informational messages, -2
        suppresses informational and many error messages, as well as
        messages from `Poll`. The default is 0.

    memory_locking : bool
        Set whether the server should try to lock its memory into
        physical RAM. Default is `False`. Supernova only option.
    threads : int
        Number of audio threads that are spawned by supernova. For
        scsynth this value is ignored. If `None` or 0, it uses the one
        thread per CPU. Default is `None`. Supernova only option.
    use_system_clock : bool
        Set whether to sync to the driver's sample clock, or to the
        system clock. Supernova only option, scsynth always uses system
        clock and this value is ignored. If `True` (default), use the
        system clock. Timestamped messages will maintain consistent
        latency over long sessions, but may not be perfectly
        sample-accurate. If `False`, use the sample clock. This helps
        to support sample-accurate scheduling; however, messaging
        latency from the client language will drift over long
        periods of time.

    input_streams : str
        Allow turning off input streams that you are not interested
        in on the audio device. If the string is '01100', for example,
        then only the second and third input streams on the device
        will be enabled. Turning off streams can reduce CPU load.
        The default value is None. Darwin only option.
    output_streams : str
        Allow turning off output streams that you are not interested
        in on the audio device. If the string is '11000', for example,
        then only the first two output streams on the device will be
        enabled. Turning off streams can reduce CPU load. Darwin only
        option.

    reserved_audio_buses : int
        Undocumented client side option.
    reserved_control_buses : int
        Undocumented client side option.
    reserved_buffers : int
        Undocumented client side option.
    initial_node_id : int
        Node ID from which to start node allocation (client side
        option). By default, the Server object in the client begins
        allocating node IDs at 1000, reserving 0-999 for *permanent*
        nodes.

    rec_header_format : str
        Default header format for NRT rendering.
    rec_sample_format : str
        Default sample format for NRT rendering.

    rec_channels : int
        Undocumented/unused client side option.
    rec_buf_size : int
        Undocumented/unused client side option.

    '''

    # locals().update(Defaults.__members__)

    def __init__(self):
        self.program = plf.Platform.default_server_cmd
        self.protocol = 'upd'

        self.bind_address = Defaults.BIND_ADDRESS.default
        self.max_logins = 1  # not default cmd value.
        self.password = Defaults.PASSWORD.default
        self.zeroconf = 0  # not default cmd value.

        self.restricted_path = Defaults.RESTRICTED_PATH.default
        self.ugen_plugins_path = Defaults.UGEN_PLUGINS_PATH.default

        self.control_buses = Defaults.CONTROL_BUSES.default
        self.audio_buses = Defaults.AUDIO_BUSES.default
        self.input_channels = 2  # not default cmd value
        self.output_channels = 2  # not default cmd value
        self.block_size = Defaults.BLOCK_SIZE.default
        self.buffers = Defaults.BUFFERS.default
        self.max_nodes = Defaults.MAX_NODES.default
        self.max_synthdefs = Defaults.MAX_SYNTHDEFS.default
        self.rt_memory = Defaults.RT_MEMORY.default
        self.wires = Defaults.WIRES.default
        self.rgens = Defaults.RGENS.default
        self.load_synthdefs = Defaults.LOAD_SYNTHDEFS.default

        self.hw_device_name = Defaults.HW_DEVICE_NAME.default  # Was inDevice outDevice.
        self.hw_buffer_size = Defaults.HW_BUFFER_SIZE.default
        self.sample_rate = Defaults.SAMPLE_RATE.default
        # self.nrt = Defaults.NRT.default  # See options_list
        self.verbose = Defaults.VERBOSE.default

        # Supernova only.
        self.memory_locking = Defaults.MEMORY_LOCKING.default
        self.threads = Defaults.THREADS.default
        self.use_system_clock = Defaults.USE_SYSTEM_CLOCK.default

        # Darwin only.
        self.input_streams = Defaults.INPUT_STREAMS.default
        self.output_streams = Defaults.OUTPUT_STREAMS.default

        # Language side.
        self.reserved_audio_buses = 0  # not used, really.
        self.reserved_control_buses = 0  # not used, really.
        self.reserved_buffers = 0  # not used, really.
        self.initial_node_id = 1000
        # self.remote_control_volume = False  # ServerPlusGui makeGui, no GUI.
        self.rec_header_format = 'aiff'
        self.rec_sample_format = 'float'
        self.rec_channels = 2
        self.rec_buf_size = None

    def options_list(self, port, osc_file=None, input_file=None,
                     output_file=None):
        '''Return a list of options for the server command.

        '''

        o = []

        if port is None:
            o.append(Defaults.NRT.flag)
            if osc_file is None:
                raise ValueError('osc_file must be supplied for nrt')
            o.append(str(osc_file))
            input_file = '_' if input_file is None else str(input_file)
            o.append(input_file)
            if output_file is None:
                # *** TODO: Method in Platform for name generation. See Recorder & Buffer.
                output_file = plf.Platform.recording_dir
                output_file.mkdir(exist_ok=True)
                output_file = str(output_file / 'SC_')
                output_file += time.strftime('%Y%m%d_%H%M%S')
                output_file += '.' + self.rec_header_format
            else:
                output_file = str(output_file)
            o.append(output_file)
            # No default SR for NRT.
            o.append(str(self.sample_rate) if self.sample_rate else '44100')
            o.append(self.rec_header_format)
            o.append(self.rec_sample_format)
        else:
            if self.protocol == 'tcp':
                o.extend([Defaults.TCP_PORT.flag, str(port)])
            else:
                o.extend([Defaults.UDP_PORT.flag, str(port)])

            if self.bind_address != Defaults.BIND_ADDRESS.default:
                o.extend([Defaults.BIND_ADDRESS.flag, str(self.bind_address)])
            if self.max_logins != Defaults.MAX_LOGINS.default:
                o.extend([Defaults.MAX_LOGINS.flag, str(self.max_logins)])
            if self.password != Defaults.PASSWORD.default:
                o.extend([Defaults.PASSWORD.flag, str(self.password)])
            if self.zeroconf != Defaults.ZEROCONF.default:
                o.extend([Defaults.ZEROCONF.flag, str(int(self.zeroconf))])

            if self.sample_rate != Defaults.SAMPLE_RATE.default:
                o.extend([Defaults.SAMPLE_RATE.flag, str(self.sample_rate)])

        if self.restricted_path != Defaults.RESTRICTED_PATH.default:
            o.extend([Defaults.RESTRICTED_PATH.flag, str(self.restricted_path)])
        if self.ugen_plugins_path != Defaults.UGEN_PLUGINS_PATH.default:
            plist = utl.as_list(self.ugen_plugins_path)
            plist = [os.path.normpath(x) for x in plist]
            o.extend([Defaults.UGEN_PLUGINS_PATH.flag, ':'.join(plist)])

        if self.control_buses != Defaults.CONTROL_BUSES.default:
            o.extend([Defaults.CONTROL_BUSES.flag, str(self.control_buses)])
        if self.audio_buses != Defaults.AUDIO_BUSES.default:
            o.extend([Defaults.AUDIO_BUSES.flag, str(self.audio_buses)])
        if self.input_channels != Defaults.INPUT_CHANNELS.default:
            o.extend([Defaults.INPUT_CHANNELS.flag, str(self.input_channels)])
        if self.output_channels != Defaults.OUTPUT_CHANNELS.default:
            o.extend([Defaults.OUTPUT_CHANNELS.flag, str(self.output_channels)])

        if self.block_size != Defaults.BLOCK_SIZE.default:
            o.extend([Defaults.BLOCK_SIZE.flag, str(self.block_size)])
        if self.buffers != Defaults.BUFFERS.default:
            o.extend([Defaults.BUFFERS.flag, str(self.buffers)])
        if self.max_nodes != Defaults.MAX_NODES.default:
            o.extend([Defaults.MAX_NODES.flag, str(self.max_nodes)])
        if self.max_synthdefs != Defaults.MAX_SYNTHDEFS.default:
            o.extend([Defaults.MAX_SYNTHDEFS.flag, str(self.max_synthdefs)])
        if self.rt_memory != Defaults.RT_MEMORY.default:
            o.extend([Defaults.RT_MEMORY.flag, str(self.rt_memory)])
        if self.wires != Defaults.WIRES.default:
            o.extend([Defaults.WIRES.flag, str(self.wires)])
        if self.rgens != Defaults.RGENS.default:
            o.extend([Defaults.RGENS.flag, str(self.rgens)])
        if self.load_synthdefs != Defaults.LOAD_SYNTHDEFS.default:
            o.extend([Defaults.LOAD_SYNTHDEFS.flag,
                str(int(self.load_synthdefs))])

        if self.hw_device_name != Defaults.HW_DEVICE_NAME.default:
            flag = Defaults.HW_DEVICE_NAME.flag
            dev = self.hw_device_name
            if isinstance(dev, str):
                o.extend([flag, repr(dev)])
            elif isinstance(dev, tuple):
                o.extend([flag, repr(dev[0]), repr(dev[1])])
            else:
                raise TypeError('hw_device_name must be str or tuple')
        if self.hw_buffer_size != Defaults.HW_BUFFER_SIZE.default:
            o.extend([Defaults.HW_BUFFER_SIZE.flag, str(self.hw_buffer_size)])

        if self.verbose != Defaults.VERBOSE.default:
            o.extend([Defaults.VERBOSE.flag, str(self.verbose)])

        # Supernova only.
        if self.program == plf.Platform.SUPERNOVA_CMD:
            if self.memory_locking != Defaults.MEMORY_LOCKING.default:
                o.append(Defaults.MEMORY_LOCKING.flag)
            if self.threads != Defaults.THREADS.default:
                o.extend([Defaults.THREADS.flag, str(self.threads)])
            if True:  # self.use_system_clock != Defaults.USE_SYSTEM_CLOCK.default:
                o.extend([Defaults.USE_SYSTEM_CLOCK.flag,
                    str(int(self.use_system_clock))])

        # Darwin only.
        if plf.Platform.name.startswith('darwin'):
            if self.input_streams != Defaults.INPUT_STREAMS.default:
                o.extend([Defaults.INPUT_STREAMS.flag, str(self.input_streams)])
            if self.output_streams != Defaults.OUTPUT_STREAMS.default:
                o.extend([Defaults.OUTPUT_STREAMS.flag,
                    str(self.output_streams)])

        return o

    def first_private_bus(self):
        '''Return the bus number after output and input buses.

        '''

        return self.output_channels + self.input_channels


# class ServerShmInterface():
#     def __init__(self, port):
#         # Low level implementation.
#         self.ptr = None
#         self.finalizer = None
#         self.connect(port)
#
#     # Primitives.
#     # copy # // never ever copy! will cause duplicate calls to the finalizer!
#     def connect(self, port): ...
#     def disconnect(self): ...
#     def get_control_bus_value(self): ...
#     def get_control_bus_values(self): ...
#     def set_control_bus_value(self, value): ...
#     def set_control_bus_values(self, *values): ...


class ServerProcess():
    def __init__(self, on_exit=None):
        self.on_exit = on_exit or (lambda exit_code: None)
        self.proc = None
        self.timeout = 0.1
        self._detached = False

    def run(self, server):
        if self.proc:
            return

        cmd = [server.options.program]
        cmd.extend(server.options.options_list(server.addr.port))

        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True,
            start_new_session=True)
        self._redirect_outerr()

        def popen_wait_thread():
            self.proc.wait()
            self._tflag.set()
            # self._tout.join()
            # self._terr.join()
            if not self._detached:
                self.on_exit(self.proc.poll())

        t = threading.Thread(
            target=popen_wait_thread,
            name=f'{type(self).__name__}.popen_wait id: {id(self)}')
        t.daemon = True
        t.start()

    def running(self):
        if self.proc is None or self._detached:
            return False
        return self.proc.poll() is None

    def finish(self):
        if self._detached:
            return

        def terminate_proc_thread():
            try:
                if self.running():
                    self.proc.terminate()
                    self.proc.wait(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.communicate() # just to be polite

        t = threading.Thread(
            target=terminate_proc_thread,
            name=f'{type(self).__name__}.terminate id: {id(self)}')
        t.daemon = True
        t.start()

    def detach(self):
        self._tflag.set()
        self._detached = True

    def _redirect_outerr(self):
        def read(out, flag, logger):
            while not flag.is_set() and self.running():  # BUG: is still a different thread.
                line = out.readline()
                if line:
                    # print(line, end='')
                    logger.info(line.rstrip())

        def make_thread(out, flag, out_name):
            logger = logging.getLogger(f'SERVER.{out_name}')
            t = threading.Thread(
                target=read,
                name=f'{type(self).__name__}.{out_name} id: {id(self)}',
                args=(out, flag, logger))
            t.daemon = True
            t.start()
            return t

        self._tflag = threading.Event()
        self._tout = make_thread(self.proc.stdout, self._tflag, 'stdout')
        self._terr = make_thread(self.proc.stderr, self._tflag, 'stderr')


class MetaServer(type):
    sync_s = True
    '''Update global variable `s` when default server is changed.'''

    def __init__(cls, *_):
        def init_func(cls):
            cls.DEFAULT_ADDRESS = nad.NetAddr('127.0.0.1', 57110)
            cls.named = dict()
            cls.all = set()

            cls._node_alloc_class = eng.NodeIDAllocator
            # // cls._node_alloc_class = ReadableNodeIDAllocator;
            cls._buffer_alloc_class = eng.ContiguousBlockAllocator
            cls._bus_alloc_class = eng.ContiguousBlockAllocator

            cls.default = cls('localhost', cls.DEFAULT_ADDRESS)
            # cls.internal = cls(
            #     'internal', nad.NetAddr(None, None))  # No internal by now.

        clb.ClassLibrary.add(cls, init_func)

    # NOTE: The next code should go in a multiserver class, it cram the
    # interface too much. It is here because Python don't like metaclass
    # attributes and they don't show in autocompletion.

    @property
    def default(cls):
        '''Default server object usualy binded to the `s` global variable.

        '''

        return cls._default

    @default.setter
    def default(cls, value):
        cls._default = value
        if cls.sync_s:
            _logger.info(f"setting global variable 's' to '{value.name}'")
            global s
            s = value
        for server in cls.all:
            mdl.NotificationCenter.notify(server, 'default', value)

    def remove(cls, server):
        '''Remove a server instance from the instances registry.

        '''

        cls.all.remove(server)
        del cls.named[server.name]

    def _resume_status_threads(cls):  # NOTE: for System Actions.
        for server in cls.all:
            server._status_watcher._resume_alive_thread()

    def quit_all(cls, watch_shutdown=True):
        '''Quit all known local servers.'''
        for server in cls.all:
            if server._is_local:
                server.quit(watch_shutdown)

    def free_all(cls, even_remote=False):  # All refers to cls.all.
        '''Free nodes from all registered local or remote servers.

        Parameters
        ----------
        even_remote : bool
            Free also the nodes of remote server. False by default.

        '''

        if even_remote:
            for server in cls.all:
                if server._status_watcher.server_running:
                    server.free_nodes()
        else:
            for server in cls.all:
                if server._is_local and server._status_watcher.server_running:
                    server.free_nodes()

    def hard_free_all(cls, even_remote=False):
        '''Free nodes from all known local or remote servers.

        Parameters
        ----------
        even_remote : bool
            Free also the nodes of remote server. False by default.

        '''

        if even_remote:
            for server in cls.all:
                server.free_nodes()
        else:
            for server in cls.all:
                if server._is_local:
                    server.free_nodes()


class Server(gpp.NodeParameter, metaclass=MetaServer):
    def __init__(self, name, addr, options=None):
        super(gpp.NodeParameter, self).__init__(self)

        self.addr = addr  # @property setter
        self._set_name(name)  # Raises ValueError if duplicated.
        type(self).all.add(self)

        # These attributes are initialized through addr setter.
        # self._is_local
        # self._in_process

        self.options = options or ServerOptions()
        self.latency = 0.2
        self.dump_mode = 0

        # These attributes are initialized through self.client_id setter.
        # self._node_allocator
        # self._default_group
        # self._default_groups
        # self._control_bus_allocator
        # self._audio_bus_allocator
        # self._buffer_allocator
        # self._scope_buffer_allocator

        self._status_watcher = sst.ServerStatusWatcher(server=self)
        self._node_watcher = ndw.NodeWatcher(server=self)
        self._process_quit_requested = False

        self._set_client_id(0)  # Assumed id to work without booting.

        self._volume = vlm.Volume(server=self, persist=True)
        self._recorder = rcd.Recorder(server=self)
        self._recorder.notify_server = True

        self._pid = None
        self._shm_interface = None  # ServerShmInterface
        self._server_process = None  # ServerProcess
        self._pid_release_condition = stm.Condition(lambda: self._pid is None)
        mdl.NotificationCenter.notify(type(self), 'server_added', self)

    @property
    def addr(self):
        '''NetAddr object of the server.'''
        return self._addr

    @addr.setter
    def addr(self, value):
        if any(s.addr == value for s in type(self).all):
            raise ValueError(f'{value} already in use by other server')
        self._addr = value
        self._in_process = self._addr.addr == 0
        self._is_local = self._in_process or self._addr.is_local

    # @property
    # def in_process(self):
    #     return self._in_process

    @property
    def name(self):
        '''Custom name of the server, only setteable at creation time.

        '''

        return self._name

    def _set_name(self, value):
        # Name can be set only at creation time.
        if value in type(self).named:
            raise ValueError(f"server name '{value}' already exists")
        self._name = value
        type(self).named[value] = self

    @property
    def default_group(self, all_users=False):
        '''Servers' default group node (user space).

        Synth and Group target this node by default.

        Parameters
        ----------
        all_users: bool
            If true return a list of all default groups (multiuser setup).

        '''

        if all_users:
            return self._default_groups
        else:
            return self._default_group

    @property
    def status(self):
        '''ServerStatusWatcher instance that keeps track of server status.

        '''

        # This this read-only property (non-data descritor) is the only
        # intended user interface to ServerStatusWatcher instances. Library's
        # style always uses _status_watcher private attribute directly.
        # NodeWatcher, on the other hand, is an implementations detail. Nodes
        # are registered or not with their own interface. Other refinements
        # can be applied later, the idea is not to cram the Server interface
        # and to always use composition instead, e.g. addr, options, status,
        # volume, recorder, etc.
        return self._status_watcher

    @property
    def volume(self):
        '''Volume instance.

        '''

        return self._volume

    @property
    def recorder(self):
        '''Recorder instance

        '''

        return self._recorder

    @property
    def pid(self):
        '''Process ID of the server program.

        '''

        return self._pid

    @property
    def program_running(self):
        '''Returns ``True`` if the server program is running in localhost.

        '''

        if self._server_process is None:
            return False
        return self._server_process.running()


    ### Client ID  ##

    @property
    def client_id(self):
        '''Client ID, usually 0 in a single user scenario.

        '''

        return self._client_id

    def _set_client_id(self, value):
        if not isinstance(value, int):
            raise TypeError(f'value is not an int: {type(value)}')
        if value < 0 or value >= self.options.max_logins:
            # Supernova ignores max_logins option
            # and doesn't return max_logins info.
            _logger.error(
                f'id ({value}) outside options.max_logins '
                f'({s.options.max_logins}), current id is {self._client_id}')
            if self.options.program == plf.Platform.SUPERNOVA_CMD:
                _logger.info(
                    'NOTE: suepernova servers ignore options.max_logins')
            return
        self._client_id = value
        self._new_allocators()


    ### ClientID-based id allocators ###

    def _new_allocators(self):
        self._new_node_allocators()
        self._new_bus_allocators()
        self._new_buffer_allocators()
        # self._new_scope_buffer_allocators()
        mdl.NotificationCenter.notify(self, '_new_allocators')

    def _new_node_allocators(self):
        self._node_allocator = type(self)._node_alloc_class(
            self.client_id, self.options.initial_node_id)
        # // defaultGroup and defaultGroups depend
        # // on allocator, so always make them here:
        self._make_default_groups()

    def _make_default_groups(self):
        # // Keep defaultGroups for all clients on this server.
        self._default_groups = [nod.Group.basic_new(
            self, self._node_allocator.num_ids * client_id + 1
        ) for client_id in range(self._status_watcher.max_logins)]
        self._default_group = self._default_groups[self.client_id]

    def _new_bus_allocators(self):
        audio_bus_io_offset = self.options.first_private_bus()
        num_ctrl_per_client = (
            self.options.control_buses // self._status_watcher.max_logins)
        num_audio_per_client = (
            (self.options.audio_buses - audio_bus_io_offset) //
            self._status_watcher.max_logins)
        ctrl_reserved_offset = self.options.reserved_control_buses
        ctrl_bus_client_offset = num_ctrl_per_client * self.client_id
        audio_reserved_offset = self.options.reserved_audio_buses
        audio_bus_client_offset = num_audio_per_client * self.client_id

        self._control_bus_allocator = type(self)._bus_alloc_class(
            num_ctrl_per_client,
            ctrl_reserved_offset,
            ctrl_bus_client_offset)

        self._audio_bus_allocator = type(self)._bus_alloc_class(
            num_audio_per_client,
            audio_reserved_offset,
            audio_bus_client_offset + audio_bus_io_offset)

    def _new_buffer_allocators(self):
        num_buffers_per_client = (
            self.options.buffers // self._status_watcher.max_logins)
        num_reserved_buffers = self.options.reserved_buffers
        buffer_client_offset = num_buffers_per_client * self.client_id

        self._buffer_allocator = type(self)._buffer_alloc_class(
            num_buffers_per_client, num_reserved_buffers, buffer_client_offset)

    # shm for GUI.
    # def _new_scope_buffer_allocators(self):
    #     if self._is_local:
    #         self._scope_buffer_allocator = eng.StackNumberAllocator(0, 127)

    def _next_buffer_number(self, n):
        '''Allocate ``n`` consecutive buffer numbers and return the first
        index.

        Raises an exception if the buffers can't be allocated.

        '''

        bufnum = self._buffer_allocator.alloc(n)
        if bufnum is None:
            if n > 1:
                raise Exception(
                    f'No block of {n} consecutive '
                    'buffer numbers is available')
            else:
                raise Exception(
                    'No more buffer numbers, free '
                    'some buffers before allocating')
        return bufnum

    def _free_all_buffers(self):
        '''Free all the buffers of the server. Use Buffer.free_all(server).'''
        bundle = []
        for block in self._buffer_allocator.blocks():
            for i in range(block.address, block.address + block.size - 1):
                bundle.append(['/b_free', i])
            self._buffer_allocator.free(block.address)
        self.addr.send_bundle(None, *bundle)

    def _next_node_id(self):
        '''Return the next available node ID.

        Each time this method is called the node allocator returns a new ID.

        '''

        return self._node_allocator.alloc()

    # def next_perm_node_id(self):
    #     '''Next avaiable permanent (default) node ID.'''
    #     return self._node_allocator.alloc_perm()

    # def free_perm_node_id(self, id):
    #     return self._node_allocator.free_perm(id)


    ### Network messages ###

    def query_tree(self, controls=False, action=None, timeout=3):
        '''Query the servers's node tree.

        Parameters
        ----------
        controls: bool
            If `True` also request synth controls values.
        action: function
            A responder function that receives the data in JSON format.
        timeout: int | float
            Request timeout in seconds.

        '''

        nod.RootNode(self).query_tree(controls, action, timeout)

    def dump_tree(self, controls=False):
        '''Ask the server to dump its node tree to stdout.

        Parameters
        ----------
        controls: bool
            If `True` also print synth controls with current values.

        '''

        if not self._is_local:
            _logger.info(f'server {self.name} is not local')
        elif self._pid is None:
            _logger.info(f'server {self.name} is not running')
            return
        nod.RootNode(self).dump_tree(controls)  # Also needs stdout access.

    def dump_osc(self, code=1):
        '''Enable server-side message dumping.

        The flags for ``code`` are as follow:
          * 0 - turn dumping OFF.
          * 1 - print the parsed contents of the message.
          * 2 - print the contents in hexadecimal.
          * 3 - print both the parsed and hexadecimal representations of the
          contents.

        '''

        self.dump_mode = code
        self.addr.send_msg('/dumpOSC', code)
        mdl.NotificationCenter.notify(self, 'dump_osc', code)

    def sync(self, condition=None, latency=None, elements=None):
        '''Wait for previous asynchronous commands to finish.

        Parameters
        ----------
        condition: Condition
            An optional instance of Condition that will be used to wait for the
            reply.
        latancy: int | float
            Bundle's latency as in ``send_bundle``.
        elements: list
            A list of lists as OSC messages which will be sent before the
            ``'/sync'`` message.

        Notes
        -----
        This method is a generator that manages server's ``'/sync'`` message
        and its reply. Use as ``yield from s.sync()`` to sync previous commands
        sent to the server from within a routine.

        Internally, it sends a ``'/sync'`` message to the server, which will
        reply with the message ``'/synced'``, and waits in a Condition until
        all previous *asynchronous commands* have been completed.

        '''

        if _libsc3.main is _libsc3.NrtMain:
            yield 0
        else:
            yield from self.addr.sync(condition, latency, elements)

    def bind(self):
        '''Return a BundleNetAddr context manager that collects generated
        messages into a bundle and send it to the server.

        Note that ``sync`` will work as expected inside a routine by sending
        the generated bundle so far::

          with s.bind():
              s.addr.send_msg( ... )
              s.addr.send_msg( ... )
              yield from s.sync()  # Sends previous messages in a bundle.
              s.addr.send_msg( ... )
              ...

        '''

        return nad.BundleNetAddr(self)


    ### Default group ###

    def _init_tree(self):
        def init_task():
            self._send_default_groups()
            yield from self.sync()
            sac.ServerTree.run(self)
            yield from self.sync()

        stm.Routine.run(init_task, clk.AppClock)

    def _send_default_groups(self):
        for group in self._default_groups:
            self.addr.send_msg('/g_new', group.node_id, 0, 0)

    def _send_default_groups_for_client_ids(self, client_ids):  # unused
        for i in client_ids:
            group = self._default_groups[i]
            self.addr.send_msg('/g_new', group.node_id, 0, 0)


    ### Shared memory interface ###

    # def _disconnect_shm(self):  # Was _disconnect_shared_memory
    # def _connect_shm(self):  # Was _connect_shared_memory.
    # @property
    # def has_shm(self):  # Was has_shm_interface.
    #     return self._shm_interface is not None


    ### Boot and login ###

    def register(self, on_complete=None, on_failure=None):
        '''Register to a remote server.

        Parameters
        ----------
        on_complete: function
            A function to be called after registration succeeded. Optionally,
            the function receives the server object as its only argument.
        on_failure: function
            A function to be called if registration fails. Optionally, the
            function receives the server object as its only argument.

        '''

        if self._status_watcher._server_registering:
            _logger.info(f"server '{self.name}' already registeringing")
            return

        if not self._status_watcher.server_running:
            self._status_watcher._server_registering = True

            def _on_complete(server):
                self._status_watcher._server_registering = False
                fn.value(on_complete, self)
                _libsc3.main._atexitq.add(
                    _libsc3.main._atexitprio.SERVERS, self._unregister_atexit)

            def _on_failure(server):
                if self.addr.proto == 'tcp':
                    self.addr.disconnect()
                self._status_watcher._server_registering = False
                fn.value(on_failure, self)

            self._status_watcher._add_action(
                'register', _on_complete, _on_failure)

            if self.options.protocol == 'tcp':
                def success():
                    self._status_watcher._start_alive_thread()
                def failure():
                    self._status_watcher._server_registering = False
                self.addr.connect(success, failure)
            else:
                self._status_watcher._start_alive_thread()
        else:
            _logger.info(f"server '{self.name}' already running")

    def unregister(self, on_complete=None, on_failure=None):
        '''Unregister from a remote server.

        Parameters
        ----------
        on_complete: function
            A function called after deregistration succeeded. Optionally, the
            function receives the server object as its only argument.
        on_failure: function
            A function called if unregistration fails. Optionally, the function
            receives the server object as its only argument.

        '''

        if self._status_watcher._server_unregistering:
            _logger.info(f"server '{self.name}' already unregisteringing")
            return

        if self._status_watcher.server_running:
            self._status_watcher._server_unregistering = True

            def _on_complete(server):
                if self.addr.proto == 'tcp' and self.addr.is_connected:
                    self.addr.disconnect()
                self._status_watcher._server_unregistering = False
                if self._pid is not None:
                    self._server_process.detach()
                    self._server_process = None
                    self._pid = None
                fn.value(on_complete, self)
                _libsc3.main._atexitq.remove(self._unregister_atexit)

            def _on_failure(server):
                self._status_watcher._server_unregistering = False
                fn.value(on_failure, self)

            self._status_watcher._add_action(
                'unregister', _on_complete, _on_failure)
            self._status_watcher._unregister()
        else:
            _logger.info(f"server '{self.name}' is not registered")

    def _unregister_atexit(self):
        if self._status_watcher.server_running:
            self._status_watcher._unregister()
            # self.addr.send_msg('/notify', 0, self.client_id)
            # _logger.info(f"server '{self.name}' requested id unregistration")

    def boot(self, register=True, on_complete=None, on_failure=None):
        '''Start the local server program.

        Parameters
        ----------
        register: bool
            Register the client to receive server notifications.
        on_complete: function
            A function to be called after the server boot process is
            successfully finished. Optionally, the function receives the
            server object as its only argument.
        on_failure: function
            A function to be called if the server boot process fails.
            Optionally, the function receives the server object as its only
            argument.

        Notes
        -----
        It is not possible to boot a server application in a remote machine.
        To register to an already running server in a remote machine use
        the ``register`` method.

        '''

        if _libsc3.main is _libsc3.NrtMain:
            self._status_watcher._boot_nrt()
            return

        if self._status_watcher.unresponsive:
            _logger.info(f"server '{self.name}' unresponsive, rebooting...")
            self.quit(False)

        if self._status_watcher.server_running:
            _logger.info(f"server '{self.name}' already running")
            return

        if self._status_watcher._server_booting:
            _logger.info(f"server '{self.name}' already booting")
            return

        self._status_watcher._server_booting = True

        def _on_complete(server):
            server._status_watcher._server_booting = False
            server._status_watcher._server_rebooting = False
            server._boot_init()
            fn.value(on_complete, server)
            _libsc3.main._atexitq.add(
                _libsc3.main._atexitprio.SERVERS, self._quit_atexit)

        def _on_failure(server):
            if self.addr.proto == 'tcp':
                self.addr.disconnect()
            server._status_watcher._server_booting = False
            server._status_watcher._server_rebooting = False
            fn.value(on_failure, server)

        self._status_watcher._add_action('boot', _on_complete, _on_failure)

        if not self._is_local:
            _logger.info(f"remote server '{self.name}' needs manual boot")
        else:
            def boot_task():
                # Server can be quitting and booting at the same time, e.g.
                # rebooting, pid release blocks boot until quit is completed.
                if self._pid is not None:  # Is or was running.
                    yield from self._pid_release_condition.wait()

                if self._in_process:
                    _logger.info('booting internal server')
                    self._boot_in_process()  # Not implemented yet.
                    self._pid = _libsc3.main.pid  # Not implemented yet.
                else:
                    # self._disconnect_shm()  # Not implemented yet.
                    try:
                        self._server_process = ServerProcess(
                            self._on_server_process_exit)
                        self._server_process.run(self)
                    except OSError as e:
                        self._server_process = None
                        self._status_watcher._server_booting = False
                        self._status_watcher._server_rebooting = False
                        if e.errno == errno.ENOENT\
                        and e.filename == self.options.program:
                            _logger.error(
                                f'{self.name} failed to boot, program '
                                f'{e.filename} not found')
                            return
                        else:
                            raise
                    self._pid = self._server_process.proc.pid
                    _logger.info(
                        f"booting server '{self.name}' on address "
                        f"{self.addr.hostname}:{self.addr.port}")

                if register:
                    # Needs delay to avoid registering to another local server
                    # from another client in case of address already in use.
                    if self.options.protocol == 'tcp' and not self._in_process:
                        def success():
                            self._status_watcher._start_alive_thread(1)
                        def failure():
                            self._status_watcher._server_booting = False
                            self._status_watcher._server_rebooting = False
                            self._status_watcher._clear_actions()
                        self.addr.connect(success, failure)
                    else:
                        self._status_watcher._start_alive_thread(1)

            stm.Routine.run(boot_task, clk.AppClock)

    def _boot_init(self):
        if self.dump_mode != 0:
            self.addr.send_msg('/dumpOSC', self.dump_mode)
        # self._connect_shm()  # Not implemented yet

    def _on_server_process_exit(self, exit_code):
        # This method is called after quit or crash.
        self._server_process = None
        self._pid = None
        self._pid_release_condition.signal()
        _logger.info(f"server '{self.name}' exited with exit code {exit_code}")
        if not self._process_quit_requested\
        and self._status_watcher._server_booting:
            self._status_watcher._perform_actions('boot', 'on_failure')
            _logger.warning(f"server '{self.name}' failed to boot")
        self._process_quit_requested = False
        # In case of server crash or Exception in World_OpenUDP: bind: Address
        # already in use, status_watcher should stop to avoid registering to
        # another local server. See note in boot(). There sould be a better
        # option for the second case to avoid delay which is arbitrary.
        self._status_watcher._quit(False)

    def _quit_atexit(self):
        if self._status_watcher.server_running:
            event = threading.Event()
            set_func = lambda: event.set()
            self.quit(True, set_func, set_func)
            event.wait(5)  # _MainThread, set_func runs in AppClock thread.

    def reboot(self, func=None, on_failure=None):
        '''Quit and (re)start the server program.

        Parameters
        ----------
        func: function
            A function to be called after quit and before the server boots
            again.
        on_failure: function
            A function to be called if the server reboot process fails.
            Optionally, the function receives the server object as its only
            argument.

        '''

        if _libsc3.main is _libsc3.NrtMain:
            # self.quit()
            self.boot()
            return

        # // func is evaluated when server is off.
        if not self._is_local:
            _logger.info("can't reboot a remote server")
            return

        if self._status_watcher._server_booting:
            _logger.info(f"server '{self.name}' already booting")
            return

        self._status_watcher._server_rebooting = True

        if self._status_watcher.server_running\
        and not self._status_watcher.unresponsive:
            def _on_complete():
                if func is not None:
                    func()
                self.boot()
            self.quit(True, _on_complete, on_failure)
        else:
            if func is not None:
                func()
            self.boot(on_failure=on_failure)

    def quit(self, watch_shutdown=True, on_complete=None, on_failure=None):
        '''Stop the server program.

        Parameters
        ----------
        watch_shutdown: bool
            Tell the server whether to watch status during shutdown.
        on_complete: function
            A function to be called after the server quit process is
            successfully finished. Optionally, the function receives the
            server object as its only argument.
        on_failure: function
            A function to be called if the server quit process fails.
            Optionally, the function receives the server object as its only
            argument.

        '''

        if _libsc3.main is _libsc3.NrtMain:
            self._status_watcher._quit_nrt()
            return

        # if server is not running or is running but unresponsive.
        if not self._status_watcher.server_running\
        or self._status_watcher.unresponsive:
            _logger.info(f"server '{self.name}' is not running")
            return

        if self._status_watcher._server_quitting:
            _logger.info(f"server '{self.name}' already quitting")
            return

        self._status_watcher._server_quitting = True

        def _on_complete():
            if self.addr.proto == 'tcp':
                self.addr.disconnect()
            self._status_watcher._server_quitting = False
            _libsc3.main._atexitq.remove(self._quit_atexit)
            fn.value(on_complete, self)

        def _on_failure():
            self._status_watcher._server_quitting = False
            fn.value(on_failure, self)

        if watch_shutdown and self._status_watcher.unresponsive:
            _logger.info(
                f"server '{self.name}' was unresponsive, quitting anyway")
            watch_shutdown = False

        self._status_watcher._add_action('quit', _on_complete, _on_failure)
        self._status_watcher._quit(watch_shutdown)
        self._process_quit_requested = True
        self.addr.send_msg('/quit')  # Send quit after responders are in place.

        if self._in_process:
            self._quit_in_process()  # Not implemented.
            _logger.info('internal server has quit')
        else:
            _logger.info(f"'/quit' message sent to server '{self.name}'")

        # if(scopeWindow.notNil) { scopeWindow.quit }  # No GUI.
        self._volume.free_synth()
        nod.RootNode(self).free_all()
        self._set_client_id(0)

    def free_nodes(self):  # Was instance freeAll in sclang.
        '''Free all server's nodes.

        '''

        self.addr.send_msg('/g_freeAll', 0)
        self.addr.send_msg('/clearSched')
        self._init_tree()

    def free_default_group(self, all_users=False):
        '''Free all nodes within the client's default group.

        '''

        if all_users:
            for group in self._default_groups:
                self.addr.send_msg('/g_freeAll', group.node_id)
        else:
            self.addr.send_msg('/g_freeAll', self._default_group.node_id)

    def reorder(self, node_list, target, add_action='addToHead'):
        '''Reorder nodes in ``node_list`` relative to ``target``.

        '''

        target = gpp.node_param(target)._as_target()
        node_list = [x.node_id for x in node_list]
        self.addr.send_msg(
            '/n_order', nod.Node._action_number_for(add_action), # 62
            target.node_id, *node_list)


    ### Node parameter interface ###

    def _as_target(self):
        return self._default_group
