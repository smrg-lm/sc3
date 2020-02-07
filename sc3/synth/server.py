"""Server.sc"""

import enum
import subprocess as _subprocess
import threading as _threading
import atexit as _atexit
import logging as _logging
import os as _os
import pathlib as _pathlib

from ..base import main as _libsc3
from ..base import utils as utl
from ..base import netaddr as nad
from ..base import model as mdl
from ..base import responsedefs as rdf
from ..base import systemactions as sac
from ..base import functions as fn
from ..base import platform as plt
from ..seq import stream as stm
from ..seq import clock as clk
from . import _engine as eng
from . import synthdef as sdf
from . import _serverstatus as sst
from . import _nodewatcher as ndw
from . import _volume as vlm
from . import recorder as rcd
from . import node as nod
from . import bus
from . import _graphparam as gpp
from . import buffer as bff


__all__ = ['s', 'Server', 'ServerOptions']


_logger = _logging.getLogger(__name__)


class Defaults(enum.Enum):
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
    USE_SYSTEM_CLOCK = ('-C', 0)  # opt bool

    # Darwin only.
    INPUT_STREAMS = ('-I', None)  # opt str, input_streams_enabled
    OUTPUT_STREAMS = ('-O', None)  # opt str, output_streams_enabled

    def __init__(self, flag, default):
        self.flag = flag
        self.default = default


class ServerOptions():
    # locals().update(Defaults.__members__)

    def __init__(self):
        self.program = plt.Platform.default_server_cmd
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

        # removed sclang's inDevice, outDevice, prListDevices, etc., the
        # solution would be to use an IOAudioDevice class that generate
        # the string for this options.
        self.hw_device_name = Defaults.HW_DEVICE_NAME.default
        self.hw_buffer_size = Defaults.HW_BUFFER_SIZE.default
        self.sample_rate = Defaults.SAMPLE_RATE.default
        self.nrt = Defaults.NRT.default
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
        self.pings_before_dead = 5
        self.rec_header_format = 'aiff'
        self.rec_sample_format = 'float'
        self.rec_channels = 2
        self.rec_buf_size = None

    def options_list(self, port=57110):
        o = []

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

        if self.restricted_path != Defaults.RESTRICTED_PATH.default:
            o.extend([Defaults.RESTRICTED_PATH.flag, str(self.restricted_path)])
        if self.ugen_plugins_path != Defaults.UGEN_PLUGINS_PATH.default:
            plist = utl.as_list(self.ugen_plugins_path)
            plist = [_os.path.normpath(x) for x in plist]
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
            o.extend([Defaults.HW_DEVICE_NAME.flag, str(self.hw_device_name)])
        if self.hw_buffer_size != Defaults.HW_BUFFER_SIZE.default:
            o.extend([Defaults.HW_BUFFER_SIZE.flag, str(self.hw_buffer_size)])
        if self.sample_rate != Defaults.SAMPLE_RATE.default:
            o.extend([Defaults.SAMPLE_RATE.flag, str(self.sample_rate)])
        if self.nrt != Defaults.NRT.default:
            o.append(Defaults.NRT.flag)
        if self.verbose != Defaults.VERBOSE.default:
            o.extend([Defaults.VERBOSE.flag, str(self.verbose)])

        # Supernova only.
        if self.program == plt.Platform.SUPERNOVA_CMD:
            if self.memory_locking != Defaults.MEMORY_LOCKING.default:
                o.append(Defaults.MEMORY_LOCKING.flag)
            if self.threads != Defaults.THREADS.default:
                o.extend([Defaults.THREADS.flag, str(self.threads)])
            if self.use_system_clock != Defaults.USE_SYSTEM_CLOCK.default:
                o.extend([Defaults.USE_SYSTEM_CLOCK.flag,
                    str(int(self.use_system_clock))])

        # Darwin only.
        if plt.Platform.name.startswith('darwin'):
            if self.input_streams != Defaults.INPUT_STREAMS.default:
                o.extend([Defaults.INPUT_STREAMS.flag, str(self.input_streams)])
            if self.output_streams != Defaults.OUTPUT_STREAMS.default:
                o.extend([Defaults.OUTPUT_STREAMS.flag,
                    str(self.output_streams)])

        return o

    def first_private_bus(self):
        return self.output_channels + self.input_channels

    def boot_in_process(self):
        raise NotImplementedError('in process server is not available')


class ServerShmInterface():
    def __init__(self, port):
        self.ptr = None # variable de bajo nivel, depende de la implementación.
        self.finalizer = None # variable de bajo nivel, depende de la implementación.
        self.connect(port) # llama a una primitiva y debe guardar port a bajo nivel

    # copy # // never ever copy! will cause duplicate calls to the finalizer!
    def connect(self, port): ... # primitiva
    def disconnect(self): ... # primitiva
    def get_control_bus_value(self): ... # primitiva
    def get_control_bus_values(self): ... # primitiva
    def set_control_bus_value(self, value): ... # primitiva # BUG: desconozco los parámetros.
    def set_control_bus_values(self, *values): ... # primitiva # BUG: desconozco los parámetros.


class ServerProcess():
    def __init__(self, on_exit=None):
        self.on_exit = on_exit or (lambda exit_code: None)
        self.proc = None
        self.timeout = 0.1

    def run(self, server):
        cmd = [server.options.program]
        cmd.extend(server.options.options_list(server.addr.port))

        self.proc = _subprocess.Popen(
            cmd,  # TODO: maybe a method popen_cmd regarding server, options and platform.
            stdout=_subprocess.PIPE,
            stderr=_subprocess.PIPE,
            bufsize=1,
            universal_newlines=True)
        self._redirect_outerr()

        def popen_wait_thread():
            self.proc.wait()
            self._tflag.set()
            # self._tout.join()
            # self._terr.join()
            _atexit.unregister(self._terminate_proc)
            self.on_exit(self.proc.poll())

        t = _threading.Thread(
            target=popen_wait_thread,
            name=f'{type(self).__name__}.popen_wait id: {id(self)}')
        t.daemon = True
        t.start()
        _atexit.register(self._terminate_proc)

    def running(self):
        return self.proc.poll() is None

    def finish(self):
        self._terminate_proc()

    def _terminate_proc(self):
        def terminate_proc_thread():
            try:
                if self.running():
                    self.proc.terminate()
                    self.proc.wait(timeout=self.timeout)  # TODO: ver, llama a wait de nuevo desde otro hilo, popen_thread están en wait.
            except _subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.communicate() # just to be polite

        t = _threading.Thread(
            target=terminate_proc_thread,
            name=f'{type(self).__name__}.terminate id: {id(self)}')
        t.daemon = True
        t.start()

    def _redirect_outerr(self):
        def read(out, flag, logger):
            while not flag.is_set() and self.running():  # BUG: is still a different thread.
                line = out.readline()
                if line:
                    # print(line, end='')
                    logger.info(line.rstrip())

        def make_thread(out, flag, out_name):
            logger = _logging.getLogger(f'SERVER.{out_name}')
            t = _threading.Thread(
                target=read,
                name=f'{type(self).__name__}.{out_name} id: {id(self)}',
                args=(out, flag, logger))
            t.daemon = True
            t.start()
            return t

        self._tflag = _threading.Event()
        self._tout = make_thread(self.proc.stdout, self._tflag, 'stdout')
        self._terr = make_thread(self.proc.stderr, self._tflag, 'stderr')


class MetaServer(type):
    def __init__(cls, *_):
        cls.DEFAULT_ADDRESS = nad.NetAddr('127.0.0.1', 57110)

        def init_func(cls):
            cls.named = dict()
            cls.all = set()
            cls.sync_s = True

            cls._node_alloc_class = eng.NodeIDAllocator
            # // cls._node_alloc_class = ReadableNodeIDAllocator;
            cls._buffer_alloc_class = eng.ContiguousBlockAllocator
            cls._bus_alloc_class = eng.ContiguousBlockAllocator

            cls.default = cls.local = cls('localhost', cls.DEFAULT_ADDRESS)
            # cls.internal = cls(
            #     'internal', nad.NetAddr(None, None))  # No internal by now.

        utl.ClassLibrary.add(cls, init_func)

    @property
    def default(cls):
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


class Server(gpp.NodeParameter, metaclass=MetaServer):
    def __init__(self, name, addr, options=None):
        super(gpp.NodeParameter, self).__init__(self)  # *** BUG: VER AHORA: ESTO SE SOLUCIONA CON __INIT_SUBCLASS__ HOOCK? (NO TENER QUE PONER EN CADA UNA)

        self.addr = addr  # @property setter
        self._set_name(name)  # Raises ValueException if duplicated.
        type(self).all.add(self)

        # self.is_local # inicializa con el setter de addr
        # self.in_process # inicializa con el setter de addr
        # self.remote_controlled # inicializa con el setter de addr

        self.options = options or ServerOptions()
        self.latency = 0.2
        self.dump_mode = 0

        # These attributes are initialized through self.client_id property setter.
        # self._node_allocator = None # init in _new_node_allocators()
        # self._default_group = None # init in _new_node_allocators() -> _make_default_groups()
        # self._default_groups = None # init in _new_node_allocators() -> _make_default_groups()
        # self._control_bus_allocator = None # init in _new_bus_allocators()
        # self._audio_bus_allocator = None # init in _new_bus_allocators()
        # self._buffer_allocator = None # init in _new_buffer_allocators()
        # self._scope_buffer_allocator = None # init in _new_scope_buffer_allocators()

        self._status_watcher = sst.ServerStatusWatcher(server=self)
        self._node_watcher = ndw.NodeWatcher(server=self)

        self._set_client_id(0)  # Assumed id to work without booting.

        self._volume = vlm.Volume(server=self, persist=True)
        self._recorder = rcd.Recorder(server=self)
        self._recorder.notify_server = True

        self.tree = lambda *args: None # TODO: ver dónde se inicializa (en la clase no lo hace), se usa en init_tree

        self._pid = None
        self._shm_interface = None  # ServerShmInterface
        self._server_process = None  # ServerProcess
        self._pid_release_condition = stm.Condition(lambda: self._pid is None)
        mdl.NotificationCenter.notify(type(self), 'server_added', self)

    def remove(self):
        type(self).all.remove(self)
        del type(self).named[self.name]

    @property
    def addr(self):
        return self._addr

    @addr.setter
    def addr(self, value):
        if any(s.addr == value for s in type(self).all):
            raise ValueError(f'{value} already in use by other server')
        self._addr = value
        self.in_process = self._addr.addr == 0
        self.is_local = self.in_process or self._addr.is_local
        self.remote_controlled = not self.is_local

    @property
    def name(self):
        return self._name

    def _set_name(self, value):
        # Name can be set only at creation time.
        if value in type(self).named:
            raise ValueError(f"server name '{value}' already exists")
        self._name = value
        type(self).named[value] = self

    @property
    def default_group(self):
        return self._default_group

    @property
    def default_groups(self):
        return self._default_groups

    @property
    def status(self):
        '''
        ServerStatusWatcher instance that keeps track of server status.
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
        return self._volume

    @property
    def recorder(self):
        return self._recorder

    @property
    def pid(self):
        return self._pid


    ### Client ID  ##

    @property
    def client_id(self):
        return self._client_id

    def _set_client_id(self, value):
        if not isinstance(value, int):
            raise TypeError(f'value is not an int: {type(value)}')
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
            #, self._status_watcher.max_logins) # *** BUG: en sclang, _node_alloc_class es eng.NodeIDAllocator por defecto, los alocadores originales reciben 2 parámetros, ContiguousBlockAllocator, que se usa para buses y buffers, recibe uno más, cambia la interfaz. Acá se pasa el tercer parámetro y NodeIDAllocator lo ignora (característica de las funciones de sclang), tengo que ver cómo maneja los ids de los nodos por cliente.
        # // defaultGroup and defaultGroups depend on allocator,
        # // so always make them here:
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
            num_buffers_per_client,
            num_reserved_buffers,
            buffer_client_offset)

    # shm for GUI.
    # def _new_scope_buffer_allocators(self):
    #     if self.is_local:
    #         self._scope_buffer_allocator = eng.StackNumberAllocator(0, 127)

    def next_buffer_number(self, n):
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

    def free_all_buffers(self):
        bundle = []
        for block in self._buffer_allocator.blocks():
            for i in range(block.address, block.address + block.size - 1):
                bundle.append(['/b_free', i])
            self._buffer_allocator.free(block.address)
        self.send_bundle(None, *bundle)

    def next_node_id(self):
        return self._node_allocator.alloc()

    def next_perm_node_id(self):
        return self._node_allocator.alloc_perm()

    def free_perm_node_id(self, id):
        return self._node_allocator.free_perm(id)


    ### Network messages ###

    def send_msg(self, *args):
        self.addr.send_msg(*args)

    def send_bundle(self, time, *args):
        self.addr.send_bundle(time, *args)

    def send_synthdef(self, name, dir=None):
        # // Load from disk locally, send remote.
        dir = dir or sdf.SynthDef.synthdef_dir
        dir = _pathlib.Path(dir)
        full_path = dir / (name + '.scsyndef')
        try:
            with open(full_path, 'rb') as file:
                buffer = file.read()
                self.send_msg('/d_recv', buffer)
        except FileNotFoundError:
            _logger.warning(f'send_synthdef FileNotFoundError: {full_path}')

    def load_synthdef(self, name, completion_msg=None, dir=None):
        # // Tell server to load from disk.
        dir = dir or sdf.SynthDef.synthdef_dir
        dir = _pathlib.Path(dir)
        path = str(dir / (name + '.scsyndef'))
        self.send_msg('/d_load', path, fn.value(completion_msg, self))

    def load_directory(self, dir, completion_msg=None):
        self.send_msg('/d_loadDir', dir, fn.value(completion_msg, self))

    def send_status_msg(self):
        self.addr.send_status_msg()

    def dump_osc(self, code=1):
        # 0 - turn dumping OFF.
        # 1 - print the parsed contents of the message.
        # 2 - print the contents in hexadecimal.
        # 3 - print both the parsed and hexadecimal representations of the contents.
        self.dump_mode = code
        self.send_msg('/dumpOSC', code)
        mdl.NotificationCenter.notify(self, 'dump_osc', code)

    def reorder(self, node_list, target, add_action='addToHead'):
        target = gpp.node_param(target)._as_target()
        node_list = [x.node_id for x in node_list]
        self.send(
            '/n_order', nod.Node.action_number_for(add_action), # 62
            target.node_id, *node_list)

    def sync(self, condition=None, bundle=None, latency=None):
        yield from self.addr.sync(condition, bundle, latency)


    ### Network message bundling ###

    # TODO...


    ### Default group ###

    def init_tree(self):
        def init_task():
            self._send_default_groups()
            self.tree(self) # tree es un atributo de instancia que contiene una función
            yield from self.sync()
            sac.ServerTree.run(self)
            yield from self.sync()

        stm.Routine.run(init_task, clk.AppClock)

    def _send_default_groups(self):
        for group in self._default_groups:
            self.send_msg('/g_new', group.node_id, 0, 0)

    def _send_default_groups_for_client_ids(self, client_ids):  # unused
        for i in client_ids:
            group = self._default_groups[i]
            self.send_msg('/g_new', group.node_id, 0, 0)


    # These atributes are just a wrapper of ServerOptions, use s.options.
    # @property rec_header_format
    # @property rec_sample_format
    # @property rec_channels
    # @property rec_buf_size


    ### Server status ###

    @classmethod
    def _resume_status_threads(cls):  # NOTE: for System Actions.
        for server in cls.all:
            server._status_watcher.resume_alive_thread()


    ### Shared memory interface ###

    def _disconnect_shared_memory(self):
        ...

    def _connect_shared_memory(self):
        ...

    @property
    def has_shm_interface(self):
        return self._shm_interface is not None


    ### Boot and login ###

    def register(self):
        self._status_watcher.start_alive_thread()
        _atexit.register(self._unregister_atexit)

    def unregister(self):
        self._status_watcher._unregister()
        _atexit.unregister(self._unregister_atexit)

    def _unregister_atexit(self):
        if self._status_watcher.server_running:
            self.send_msg('/notify', 0, self.client_id)
            _logger.info(f"server '{self.name}' requested id unregistration")

    def boot(self, on_complete=None, on_failure=None, register=True):
        if self._status_watcher.unresponsive:
            _logger.info(f"server '{self.name}' unresponsive, rebooting...")
            self.quit(watch_shutdown=False)

        if self._status_watcher.server_running:
            _logger.info(f"server '{self.name}' already running")
            return

        if self._status_watcher.server_booting:
            _logger.info(f"server '{self.name}' already booting")
            return

        self._status_watcher.server_booting = True

        def _on_complete(server):
            server._status_watcher.server_booting = False
            server._boot_init()
            fn.value(on_complete, server)

        def _on_failure(server):
            server._status_watcher.server_booting = False
            fn.value(on_failure, server)

        self._status_watcher._add_boot_action(_on_complete, _on_failure)

        if self.remote_controlled:
            _logger.info(f"remote server '{self.name}' needs manual boot")
        else:
            def boot_task():
                if self._pid is not None:  # NOTE: pid es el flag que dice si se está/estuvo ejecutando un server local o internal
                    yield from self._pid_release_condition.hang()  # NOTE: signal from _on_server_process_exit from ServerProcess
                self._boot_server_app()
                if register:
                    # Needs delay to avoid registering to another local server
                    # from another client in case of address already in use.
                    self._status_watcher.start_alive_thread(1)

            stm.Routine.run(boot_task, clk.AppClock)

    def _boot_init(self):
        if self.dump_mode != 0:
            self.send_msg('/dumpOSC', self.dump_mode)
        self._connect_shared_memory()  # BUG: not implemented yet

    def _boot_server_app(self):
        if self.in_process:
            _logger.info('booting internal server')
            self.boot_in_process()  # BUG: not implemented yet
            self._pid = _libsc3.main.pid  # BUG: not implemented yet
            fn.value(on_complete, self)
        else:
            self._disconnect_shared_memory()  # BUG: not implemented yet
            self._server_process = ServerProcess(self._on_server_process_exit)
            self._server_process.run(self)
            self._pid = self._server_process.proc.pid
            _logger.info(f"booting server '{self.name}' on address "
                         f"{self.addr.hostname}:{self.addr.port}")
            if self.options.protocol == 'tcp':
                raise NotImplementedError('missing tcp implementation')
                # self.addr.try_connect_tcp(on_complete, None, 20)  # BUG: not implemented yet
                # on_complete was a callback with start_alive_thread(delay=0).

    def _on_server_process_exit(self, exit_code):
        self._pid = None
        self._pid_release_condition.signal()
        _logger.info(f"server '{self.name}' exited with exit code {exit_code}")
        self._status_watcher._quit(watch_shutdown=False)  # *** NOTE: este quit se llama cuando termina el proceso y cuando se llama a server.quit.

    def reboot(self, func=None, on_failure=None): # // func is evaluated when server is off
        if not self.is_local:
            _logger.info("can't reboot a remote server")
            return

        if self._status_watcher.server_running\
        and not self._status_watcher.unresponsive:
            def _():
                if func is not None:
                    func()
                clk.defer(lambda: self.boot())
            self.quit(_, on_failure)
        else:
            if func is not None:
                func()
            self.boot(on_failure=on_failure)

    def application_running(self):  # *** TODO: este método se relaciona con server_running que es propiedad, ver
        return self._server_process.running()

    def quit(self, on_complete=None, on_failure=None, watch_shutdown=True):
        # if server is not running or is running but unresponsive.
        if not self._status_watcher.server_running\
        or self._status_watcher.unresponsive:
            _logger.info(f'server {self.name} is not running')
            return

        if self._status_watcher.server_quiting:
            _logger.info(f"server '{self.name}' already quiting")
            return

        self._status_watcher.server_quiting = True
        self.addr.send_msg('/quit')

        def _on_complete():
            self._status_watcher.server_quiting = False
            fn.value(on_complete, self)  # *** BUG: try_disconnect_tcp

        def _on_failure():
            self._status_watcher.server_quiting = False
            fn.value(on_failure, self)  # *** BUG: try_disconnect_tcp

        if watch_shutdown and self._status_watcher.unresponsive:
            _logger.info(
                f"server '{self.name}' was unresponsive, quitting anyway")
            watch_shutdown = False

        if self.options.protocol == 'tcp':
            self._status_watcher._quit(
                lambda: self.addr.try_disconnect_tcp(_on_complete, _on_failure),  # *** BUG: envuelvo las funciones que son para server y _status_watcher para pasar self, la implementación en sclang de try_disconnect_tcp le pasa addr a ambos incluso cuando a onComplete no se le pasa nada nunca y a onFailure se le pasa server *solo* en _status_watcher.
                None, watch_shutdown)
        else:
            self._status_watcher._quit(
                _on_complete, _on_failure, watch_shutdown)

        if self.in_process:
            self.quit_in_process()  # *** BUG: no existe.
            _logger.info('internal server has quit')
        else:
            _logger.info(f"'/quit' message sent to server '{self.name}'")

        # if(scopeWindow.notNil) { scopeWindow.quit }  # No GUI.
        self._volume.free_synth()
        nod.RootNode(self).free_all()
        self._set_client_id(0)

    @classmethod
    def quit_all(cls, watch_shutdown=True):
        for server in cls.all:
            if server.is_local:
                server.quit(watch_shutdown=watch_shutdown)

    @classmethod
    def free_all(cls, even_remote=False):  # All refers to cls.all.
        if even_remote:
            for server in cls.all:
                if server._status_watcher.server_running:
                    server.free_nodes()
        else:
            for server in cls.all:
                if server.is_local and server._status_watcher.server_running:
                    server.free_nodes()

    def free_nodes(self):  # Instance free_all in sclang.
        self.send_msg('/g_freeAll', 0)
        self.send_msg('/clearSched')
        self.init_tree()

    def free_default_group(self):
        self.send_msg('g_freeAll', self._default_group.node_id)

    def free_default_groups(self):
        for group in self._default_groups:
            self.send_msg('g_freeAll', group.node_id)

    @classmethod
    def hard_free_all(cls, even_remote=False):
        if even_remote:
            for server in cls.all:
                server.free_nodes()
        else:
            for server in cls.all:
                if server.is_local:
                    server.free_nodes()


    # L1203
    ### internal server commands ###
    # TODO

    # L1232
    # /* CmdPeriod support for Server-scope and Server-record and Server-volume */
    # TODO

    def query_tree(self, query_controls=False, timeout=3):
        if self.is_local and self._pid is not None:  # Also needs stdout access.
            nod.RootNode(self).dump_tree(query_controls)
        else:
            nod.RootNode(self).query_tree(query_controls, timeout)

    # L1315
    # funciones set/getControlBug*
    # TODO

    def input_bus(self):  # utility
        return bus.Bus('audio', self.options.output_channels,
                        self.options.input_channels, self)

    def output_bus(self):  # utility
        return bus.Bus('audio', 0, self.options.output_channels, self)


    ### Node parameter interface ###

    def _as_target(self):
        return self._default_group

    # def scsynth(cls): No.
    # def supernova(cls): No.
    # def from_name(cls): No.
    # def kill_all(cls): No.
