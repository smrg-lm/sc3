"""Server.sc"""

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
from . import node as nod
from . import bus
from . import _graphparam as gpp
from . import buffer as bff


_logger = _logging.getLogger(__name__)


### Command line server exec default values ###

_NUM_CONTROL_BUS_CHANNELS = 16384
_NUM_AUDIO_BUS_CHANNELS = 1024 # esta no se usa, hace self.num_private_audio_bus_channels + self.num_input_bus_channels + self.num_output_bus_channels
_NUM_INPUT_BUS_CHANNELS = 8
_NUM_OUTPUT_BUS_CHANNELS = 8
_NUM_BUFFERS = 1024

_MAX_NODES = 1024
_MAX_SYNTH_DEFS = 1024
_BLOCK_SIZE = 64
#_HARDWARE_BUFFER_SIZE = 0 (None) # BUG: ver abajo, la lógica de esto es endeble

_MEM_SIZE = 8192
_NUM_RGENS = 64
_NUM_WIRE_BUFS = 64

#_SAMPLE_RATE = 0 (None) # BUG: ver abajo, la lógica de esto es endeble
#_LOAD_DEFS = 1 (True) # BUG: ver abajo, la lógica de esto es endeble

_VERBOSITY = 0
#_ZEROCONF = 1 (True) # BUG: ver abajo, la lógica de esto es endeble
_MAX_LOGINS = 64

_BIND_ADDRESS = '127.0.0.1'


class ServerOptions():
    def __init__(self):
        self.program = plt.Platform.default_server_cmd
        self.num_control_bus_channels = _NUM_CONTROL_BUS_CHANNELS # getter/setter
        self._num_audio_bus_channels = _NUM_AUDIO_BUS_CHANNELS # @property
        self._num_input_bus_channels = 2 # @property, es 2 a propósito
        self._num_output_bus_channels = 2 # @property, es 2 a propósito
        self._num_private_audio_bus_channels = 1020 # @property
        self.num_buffers = 1026 # getter setter, es 1026 a propósito

        self.max_nodes = _MAX_NODES # Todos los métodos siguientes tiene getter y setter salvo indicación contraria
        self.max_synth_defs = _MAX_SYNTH_DEFS
        self.protocol = 'upd'
        self.block_size = _BLOCK_SIZE
        self.hardware_buffer_size = None # BUG: ver, la lógica de esto es endeble

        self.mem_size = _MEM_SIZE
        self.num_rgens = _NUM_RGENS
        self.num_wire_bufs = _NUM_WIRE_BUFS

        self.sample_rate = None # BUG: ver, la lógica de esto es endeble
        self.load_defs = True # BUG: ver, la lógica de esto es endeble

        self.input_streams_enabled = None # es nil o un string, e.g. '0110000' # BUG: ver, la lógica de esto es endeble
        self.output_streams_enabled = None # es nil o un string, e.g. '0110000' # BUG: ver, la lógica de esto es endeble

        self.in_device = None
        self.out_device = None

        self.verbosity = _VERBOSITY
        self.zeroconf = False # BUG: ver, la lógica de esto es endeble # // Whether server publishes port to Bonjour, etc.

        self.restricted_path = None
        self.ugen_plugins_path = None

        self.initial_node_id = 1000
        self.remote_control_volume = False

        self.memory_locking = False
        self.threads = None # // for supernova
        self.use_system_clock = None # // for supernova # BUG semántico en sclang, lo inicializa en False, pero la lógica es que si no es None usa true/false para 1/0, entonces siempre pasa al valor por defecto (0)

        self.reserved_num_audio_bus_channels = 0
        self.reserved_num_control_bus_channels = 0
        self.reserved_num_buffers = 0
        self.pings_before_considered_dead = 5

        self.max_logins = 1

        self.rec_header_format = 'aiff'
        self.rec_sample_format = 'float'
        self.rec_channels = 2
        self.rec_buf_size = None

        self.bind_address = _BIND_ADDRESS

    @property
    def device(self):
        if self.in_device == self.out_device:
            return self.in_device
        else:
            return (self.in_device, self.out_device)

    @device.setter
    def device(self, value):
        self.in_device = self.out_device = value

    def options_list(self, port=57110):
        o = []

        if self.protocol == 'tcp':
            o.extend(['-t', str(port)])
        else:
            o.extend(['-u', str(port)])

        o.extend(['-a', str(self.num_private_audio_bus_channels +
                        self.num_input_bus_channels +
                        self.num_output_bus_channels)])
        o.extend(['-i', str(self.num_input_bus_channels)])  # BUG: ver default de _NUM_INPUT_BUS_CHANNELS
        o.extend(['-o', str(self.num_output_bus_channels)])  # BUG: ver default de _NUM_OUTPUT_BUS_CHANNELS

        if self.bind_address != _BIND_ADDRESS:
            o.extend(['-B', self.bind_address])
        if self.num_control_bus_channels != _NUM_CONTROL_BUS_CHANNELS:
            o.extend(['-c', str(self.num_control_bus_channels)])
        if self.num_buffers != _NUM_BUFFERS:
            o.extend(['-b', str(self.num_buffers)])
        if self.max_nodes != _MAX_NODES:
            o.extend(['-n', str(self.max_nodes)])
        if self.max_synth_defs != _MAX_SYNTH_DEFS:
            o.extend(['-d', str(self.max_synth_defs)])
        if self.block_size != _BLOCK_SIZE:
            o.extend(['-z', str(self.block_size)])
        if self.hardware_buffer_size is not None: # BUG: ver, la lógica de esto es endeble
            o.extend(['-Z', str(self.hardware_buffer_size)])
        if self.mem_size != _MEM_SIZE:
            o.extend(['-m', str(self.mem_size)])
        if self.num_rgens != _NUM_RGENS:
            o.extend(['-r', str(self.num_rgens)])
        if self.num_wire_bufs != _NUM_WIRE_BUFS:
            o.extend(['-w', str(self.num_wire_bufs)])
        if self.sample_rate is not None: # BUG: ver, la lógica de esto es endeble
            o.extend(['-S', str(self.sample_rate)])
        if not self.load_defs: # BUG: ver, la lógica de esto es endeble
            o.extend(['-D', '0'])
        if self.input_streams_enabled is not None: # BUG: ver, la lógica de esto es endeble
            o.extend(['-I', self.input_streams_enabled])
        if self.output_streams_enabled is not None: # BUG: ver, la lógica de esto es endeble
            o.extend(['-O', self.output_streams_enabled])
        if self.in_device == self.out_device:
            if self.in_device is not None:
                o.extend(['-H', f'"{self.in_device}"'])  # BUG: comprobar que funciona en Python
        else:
            o.extend(['-H', f'"{self.in_device}" "{self.out_device}"'])  # BUG: comprobar que funciona en Python
        if self.verbosity != _VERBOSITY:
            o.extend(['-V', str(self.verbosity)])
        if not self.zeroconf: # BUG: ver, la lógica de esto es endeble
            o.extend(['-R', '0'])
        if self.restricted_path is not None:
            o.extend(['-P', str(self.restricted_path)])  # may be str o Path
        if self.ugen_plugins_path is not None:
            plist = utl.as_list(self.ugen_plugins_path)
            plist = [_os.path.normpath(x) for x in plist] # BUG: ensure platform format? # BUG: windows drive?
            o.extend(['-U', _os.pathsep.join(plist)])
        if self.memory_locking:
            o.append('-L')
        if self.threads is not None:
            if self.program == plt.Platform.SUPERNOVA_CMD:
                o.extend(['-T', str(self.threads)])
        if self.use_system_clock is not None:
            o.extend(['-C', str(int(self.use_system_clock))])
        if self.max_logins is not None:
            o.extend(['-l', str(self.max_logins)])
        return o

    def first_private_bus(self):
        return self.num_output_bus_channels + self.num_input_bus_channels

    def boot_in_process(self):
        raise NotImplementedError('in process server is not available')

    @property
    def num_private_audio_bus_channels(self):
        return self._num_private_audio_bus_channels

    @num_private_audio_bus_channels.setter
    def num_private_audio_bus_channels(self, value=112): # TODO: no sé por qué 112
        self._num_private_audio_bus_channels = value
        self._recalc_channels()

    @property
    def num_audio_bus_channels(self):
        return self._num_audio_bus_channels

    @num_audio_bus_channels.setter
    def num_audio_bus_channels(self, value): #=1024): es un setter, no puede tener valor por defecto
        self._num_audio_bus_channels = value
        self._num_private_audio_bus_channels = self._num_audio_bus_channels\
            - self._num_input_bus_channels - self._num_output_bus_channels

    @property
    def num_input_bus_channels(self):
        return self._num_input_bus_channels

    @num_input_bus_channels.setter
    def num_input_bus_channels(self, value=8):
        self._num_input_bus_channels = value
        self._recalc_channels()

    @property
    def num_output_bus_channels(self):
        return self._num_output_bus_channels

    @num_output_bus_channels.setter
    def num_output_bus_channels(self, value=8):
        self._num_output_bus_channels = value
        self._recalc_channels()

    def _recalc_channels(self):
        self._num_audio_bus_channels = self._num_private_audio_bus_channels\
            + self._num_input_bus_channels + self._num_output_bus_channels

    # TODO: estas funciones están implementadas solo para CoreAudio en
    # SC_CoreAudioPrim.cpp. Hay una función de port audio PaQa_ListAudioDevices
    # en external_libraries con un nombre similar, server/scsynth/SC_PortAudio.cpp
    # y server/supernova/audio_backend/portaudio_backend.hpp/cpp
    # *prListDevices { # primitiva
    # *devices { # llama a *prListDevices
    # *inDevices { # llama a *prListDevices
    # *outDevices { # llama a *prListDevices


class ServerShmInterface():
    def __init__(self, port):
        self.ptr = None # variable de bajo nivel, depende de la implementación.
        self.finalizer = None # variable de bajo nivel, depende de la implementación.
        self.connect(port) # llama a una primitiva y debe guardar port a bajo nivel

    # copy # // never ever copy! will cause duplicate calls to the finalizer!
    def connect(self, port): pass # primitiva
    def disconnect(self): pass # primitiva
    def get_control_bus_value(self): pass # primitiva
    def get_control_bus_values(self): pass # primitiva
    def set_control_bus_value(self, value): pass # primitiva # BUG: desconozco los parámetros.
    def set_control_bus_values(self, *values): pass # primitiva # BUG: desconozco los parámetros.


class MetaServer(type):
    def __init__(cls, *_):
        cls.DEFAULT_ADDRESS = nad.NetAddr('127.0.0.1', 57110)

        def init_func(cls):
            cls.named = dict()
            cls.all = set()
            cls.sync_s = True

            cls.node_alloc_class = eng.NodeIDAllocator
            # // cls.node_alloc_class = ReadableNodeIDAllocator;
            cls.buffer_alloc_class = eng.ContiguousBlockAllocator
            cls.bus_alloc_class = eng.ContiguousBlockAllocator

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
    @classmethod
    def remote(cls, name, addr, options=None, client_id=None):
        result = cls(name, addr, options, client_id)
        result.status_watcher.start_alive_thread()
        return result

    def __init__(self, name, addr, options=None, client_id=None):
        super(gpp.NodeParameter, self).__init__(self)  # *** BUG: VER AHORA: ESTO SE SOLUCIONA CON __INIT_SUBCLASS__ HOOCK? (NO TENER QUE PONER EN CADA UNA)
        self._max_num_clients = None # BUG: subida, se necesita antes de setear self.client_id # // maxLogins as sent from booted scsynth # la setea en _handle_client_login_info_from_server
        self._client_id = None # BUG: se necesita antes de setear self.client_id

        # // set name to get readable posts from client_id set
        self._name = name # no usa @property setter
        self.addr = addr # @property setter

        # self.is_local # inicializa con el setter de addr
        # self.in_process # inicializa con el setter de addr
        # self.remote_controlled # inicializa con el setter de addr

        self.options = options or ServerOptions()
        self.latency = 0.2
        self.dump_mode = 0

        # NOTE: Estos valores se inicializan al llamar self.client_id = x abajo.
        # self.node_allocator = None # se inicializa en new_node_allocators
        # self.default_group = None # se inicializa en node_allocator -> make default_groups # solo tiene getter en la declaración, init en make_default_groups
        # self.default_groups = None # se inicializa en node_allocator -> make default_groups # solo tienen getter en la declaración, init en make_default_groups
        # self.control_bus_allocator = None # se inicializa en new_bus_allocators
        # self.audio_bus_allocator = None # se inicializa en new_bus_allocators
        # self.buffer_allocator = None # se inicializa en new_buffer_allocators
        # self.scope_buffer_allocator = None # se inicializa en new_scope_buffer_allocators

        # // make statusWatcher before clientID, so .serverRunning works
        self.status_watcher = sst.ServerStatusWatcher(server=self)
        # // go thru setter to test validity
        self.client_id = client_id or 0 # es @property y usa el setter

        self.node_watcher = ndw.NodeWatcher(server=self)

        self._volume = vlm.Volume(server=self, persist=True)
        #self.recorder = xxx.Recorder(server=self) # BUG: falta implementar
        #self.recorder.notify_server = True # BUG: falta implementar

        self.name = name # ahora si usa @property setter
        type(self).all.add(self)

        #self._max_num_clients = None # // maxLogins as sent from booted scsynth # la setea en _handle_client_login_info_from_server
        self.tree = lambda *args: None # TODO: ver dónde se inicializa (en la clase no lo hace), se usa en init_tree

        self.sync_thread = None # solo getter en la declaración # se usa en sched_sync
        self.sync_tasks = [] # solo getter en la declaración # se usa en sched_sync
        # var <window, <>scopeWindow, <emacsbuf;
        # var <volume, <recorder, <statusWatcher;

        self.pid = None # iniicaliza al bootear, solo tiene getter en la declaración
        self._server_interface = None  # shm
        self._server_process = None  # _ServerProcess
        self._pid_release_condition = stm.Condition(lambda: self.pid is None)
        mdl.NotificationCenter.notify(type(self), 'server_added', self)

        # TODO: siempre revisar que no esté usando las de variables clase
        # porque no va a funcionar con metaclass sin llamar a type(self).
        # TODO: ver qué atributos no tienen setter y convertirlos en propiedad.

    @property
    def max_num_clients(self):
        return self._max_num_clients or self.options.max_logins

    def remove(self):
        type(self).all.remove(self)
        del type(self).named[self.name]

    @property
    def addr(self):
        return self._addr

    @addr.setter
    def addr(self, value):
        self._addr = value
        self.in_process = self._addr.addr == 0
        self.is_local = self.in_process or self._addr.is_local()
        self.remote_controlled = not self.is_local

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        if value in type(self).named:
            _logger.warning(f"server name '{value}' already "  # BUG: in sclang, two params to format
                            "exists, please use a unique name")  # TODO: why not an exception?
        else:
            type(self).named[value] = self

    # TODO: este método tal vez debería ir abajo de donde se llama por primera vez
    def init_tree(self):
        def init_task():
            self.send_default_groups()
            self.tree(self) # tree es un atributo de instancia que contiene una función
            self.sync()
            sac.ServerTree.run(self)
            self.sync()

        clk.defer(init_task)


    ### client ID  ##

    # // clientID is settable while server is off, and locked while server is
    # // running called from prHandleClientLoginInfoFromServer once after booting.

    @property
    def client_id(self):
        return self._client_id

    @client_id.setter
    def client_id(self, value):
        msg = "server '%s' couldn't set client_id "\
              "to %s - %s, client_id is still %s"
        if self.status_watcher.server_running:
            args = (self.name, value, 'server is running', self.client_id)
            _logger.warning(msg, *args)
            return
        if not isinstance(value, int):
            args = (self.name, value, 'not an int', self.client_id)
            _logger.warning(msg, *args)
            return
        if value < 0 or value >= self.max_num_clients:
            msg2 = 'outside max_num_clients range '\
                   f'0..{self.max_num_clients - 1}'
            _logger.warning(msg, self.name, value, msg2, self.client_id)
            return
        if self._client_id != value:
            _logger.info(f"server '{self.name}' setting client_id to {value}")
        self._client_id = value
        self.new_allocators() # *** BUG: parece un método privado pero lo usan en UnitTest-bootServer


    ### clientID-based id allocators ###

    def new_allocators(self):
        self.new_node_allocators()
        self.new_bus_allocators()
        self.new_buffer_allocators()
        self.new_scope_buffer_allocators()
        mdl.NotificationCenter.notify(self, 'new_allocators')

    def new_node_allocators(self):
        self.node_allocator = type(self).node_alloc_class(
            self.client_id, self.options.initial_node_id)
            #, self.max_num_clients) # BUG: en sclang, node_alloc_class es eng.NodeIDAllocator por defecto, los alocadores originales reciben 2 parámetros, ContiguousBlockAllocator, que se usa para buses y buffers, recibe uno más, cambia la interfaz. Acá se pasa el tercer parámetro y NodeIDAllocator lo ignora (característica de las funciones de sclang), tengo que ver cómo maneja los ids de los nodos por cliente.
        # // defaultGroup and defaultGroups depend on allocator,
        # // so always make them here:
        self.make_default_groups()

    def new_bus_allocators(self):
        audio_bus_io_offset = self.options.first_private_bus()
        num_ctrl_per_client = (self.options.num_control_bus_channels //
                               self.max_num_clients)
        num_audio_per_client = (self.options.num_audio_bus_channels -
                                audio_bus_io_offset) // self.max_num_clients
        ctrl_reserved_offset = self.options.reserved_num_control_bus_channels
        ctrl_bus_client_offset = num_ctrl_per_client * self.client_id
        audio_reserved_offset = self.options.reserved_num_audio_bus_channels
        audio_bus_client_offset = num_audio_per_client * self.client_id

        self.control_bus_allocator = type(self).bus_alloc_class(
            num_ctrl_per_client,
            ctrl_reserved_offset,
            ctrl_bus_client_offset
        )
        self.audio_bus_allocator = type(self).bus_alloc_class(
            num_audio_per_client,
            audio_reserved_offset,
            audio_bus_client_offset + audio_bus_io_offset
        )

    def new_buffer_allocators(self):
        num_buffers_per_client = self.options.num_buffers // self.max_num_clients
        num_reserved_buffers = self.options.reserved_num_buffers
        buffer_client_offset = num_buffers_per_client * self.client_id

        self.buffer_allocator = type(self).buffer_alloc_class(
            num_buffers_per_client,
            num_reserved_buffers,
            buffer_client_offset
        )

    def new_scope_buffer_allocators(self):
        if self.is_local:
            self.scope_buffer_allocator = eng.StackNumberAllocator(0, 127)

    def next_buffer_number(self, n):
        bufnum = self.buffer_allocator.alloc(n)
        if bufnum is None:
            if n > 1:
                raise Exception(f'No block of {n} consecutive '
                                'buffer numbers is available')
            else:
                raise Exception('No more buffer numbers, free '
                                'some buffers before allocating')
        return bufnum

    def free_all_buffers(self):
        bundle = []
        for block in self.buffer_allocator.blocks():
            for i in range(block.address, block.address + block.size - 1):
                bundle.append(['/b_free', i])
            self.buffer_allocator.free(block.address)
        self.send_bundle(None, *bundle) # BUG: comprobar que esté en formato correcto para client.send_bundle

    def next_node_id(self):
        return self.node_allocator.alloc()

    def next_perm_node_id(self):
        return self.node_allocator.alloc_perm()

    def free_perm_node_id(self, id):
        return self.node_allocator.free_perm(id)

    def _handle_client_login_info_from_server(self, new_client_id=None,
                                              new_max_logins=None): # BUG: name!
        # // only set maxLogins if not internal server
        if not self.in_process:
            if new_max_logins is not None:
                if new_max_logins != self.options.max_logins:
                    _logger.info(f"'{self.name}' server process has "
                                 f"max_logins {new_max_logins} - adjusting "
                                 "options accordingly")
                else:
                    _logger.info(f"'{self.name}' server process's max_logins "
                                 f"({new_max_logins}) matches current options")
                self.options.max_logins = self._max_num_clients = new_max_logins
            else:
                _logger.info(f"'{self.name}' no max_logins "  # *** BUG: in sclang, passes two arguments.
                             "info from server process")  # BUG: why 'from' if data is a parameter to this method.
        if new_client_id is not None:
            if new_client_id == self.client_id:
                _logger.info(f"'{self.name}' keeping client_id  "
                             f"({new_client_id}) as confirmed "
                             "by server process")
            else:
                _logger.info(f"'{self.name}' setting client_id to "
                             f"{new_client_id}, as obtained "
                             "from server process")
            self.client_id = new_client_id

    # // This method attempts to recover from a loss of client-server contact,
    # // which is a serious emergency in live shows. So it posts a lot of info
    # // on the recovered state, and possibly helpful next user actions.
    def _handle_login_when_already_registered(self, client_id_from_process):
        _logger.info(f"'{self.name}' handling login request "
                     "though already registered")
        if client_id_from_process is None:
            _logger.info(f"'{self.name}' notify response did not contain "
                         "already-registered clientID from server process. "
                         "Assuming all is well.")
        elif client_id_from_process != self.client_id:
            # // By default, only reset clientID if changed,
            # // to leave allocators untouched.
            # // Make sure we can set the clientID, and set it.
            self.status_watcher.notified = False  # just for setting client_id restored below, looks hackie.
            self.client_id = client_id_from_process
            _logger.info(  # We need to talk about these messages.
                'This seems to be a login after a crash, or from a new server '
                'object, so you may want to release currently running synths '
                'by hand with: server.default_group.release(). '
                'And you may want to redo server boot finalization by hand:'
                'server.status_watcher._finalize_boot()')
        else:
            # // Same clientID, so leave all server
            # // resources in the state they were in!
            _logger.info(
                'This seems to be a login after a loss of network contact. '
                'Reconnected with the same clientID as before, so probably all '
                'is well.')
        # // Ensure that statuswatcher is in the correct state immediately.
        self.status_watcher.notified = True
        self.status_watcher.unresponsive = False
        mdl.NotificationCenter.notify(self, 'server_running')

    def _handle_notify_fail_string(self, fail_string, msg): # *** BUG: yo usé msg en vez de failstr arriba.
        # // post info on some known error cases
        if 'already registered' in fail_string:
            # // when already registered, msg[3] is the clientID by which
            # // the requesting client was registered previously
            _logger.info(f"'{self.name}' - already registered "
                         f"with client_id {msg[3]}")
            self._handle_login_when_already_registered(msg[3])
        elif 'not registered' in fail_string:
            # // unregister when already not registered:
            _logger.info(f"'{self.name}' - not registered")
            self.status_watcher.notified = False  # *** BUG: si no setea a True no se cumple la condición en la función osc de ServerStatusWatcher.add_status_watcher y vuelve a crear los responders de booteo al llamar a _send_notify_request
        elif 'too many users' in fail_string:
            _logger.info(f"'{self.name}' - could not register, too many users")
            self.status_watcher.notified = False  # *** BUG: si no setea a True no se cumple la condición en la función osc de ServerStatusWatcher.add_status_watcher y vuelve a crear los responders de booteo al llamar a _send_notify_request
        else:
            # // throw error if unknown failure
            raise Exception(f"Failed to register with server '{self.name}' "
                            f"for notifications: {msg}. To recover, please "
                            "reboot the server")


    ### network messages ###

    def send_msg(self, *args):
        self.addr.send_msg(*args)

    def send_bundle(self, time, *args):
        self.addr.send_bundle(time, *args)

    # def send_raw(self, raw_bytes): # send a raw message without timestamp to the addr.
    #    self.addr.send_raw(raw_bytes)

    def send_msg_sync(self, condition, *args): # este método no se usa en la libreríá de clases
        condition = condition or stm.Condition()
        cmd_name = str(args[0]) # BUG: TODO: el método reorder de abajo envía con send_msg y el número de mensaje como int, VER que hace sclang a bajo nivel, pero puede que esta conversión esté puesta para convertir símbolos a strings en sclang?
        if cmd_name[0] != '/':
            cmd_name = '/' + cmd_name # BUG: ver reorder abajo, ver por qué agrega la barra acá y no en otras partes.
        args = list(args)
        args[0] = cmd_name # BUG: esto no está en sclang, supongo que se encarga luego a bajo nivel.

        def resp_func(msg, *_):
            if str(msg[1]) == cmd_name:
                resp.free()
                condition.test = True
                condition.signal()

        resp = rdf.OSCFunc(resp_func, '/done', self.addr) # BUG: aún faltan implementar la clase OSCFuncAddrMessageMatcher que llama internamente el dispatcher
        self.send_bundle(None, args)
        yield from condition.wait()

    def sync(self, condition=None, bundles=None, latency=None): # BUG: dice bundles, tengo que ver el nivel de anidamiento
        yield from self.addr.sync(condition, bundles, latency)

    # Este método no se usa en la libreríá de clases
    # y no especifica cómo debería usarse la condición interna.
    # BUG: El problema es que le crea dos atributos a Server.
    # TODO: Probablemente se pueda borrar, ver.
    def sched_sync(self, func):
        self.sync_tasks.append(func) # NOTE: las func tienen que ser generadores que hagna yield form cond.wait()?
        if self.sync_thread is None:
            def sync_thread_rtn():
                cond = stm.Condition()
                while len(self.sync_tasks) > 0:
                    yield from self.sync_tasks.pop(0)(cond) # BUG: no se si esto funcione así como así, sin más, por cond. Si el control vuelve a sync_thread_rtn nunc ase ejecuta el código en espera.
                self.sync_thread = None
            self.sync_thread = stm.Routine.run(sync_thread_rtn, clk.AppClock) # BUG:s en sclang usa TempoClock, ver arriba, acá deberíá pasar todos los AppClock a SystemClock (el reloj por defecto orginialmente de las rutinas).

    # def list_send_msg(self, msg): # TODO: creo que es un método de conveniencia que genera confusión sobre la interfaz, acá msg es una lista no más.
    #     pass
    # def list_send_bundle(self, time, msgs):# TODO: creo que es un método de conveniencia que genera confusión sobre la interfaz, acá msgs es una lista no más.
    #     pass

    def reorder(self, node_list, target, add_action='addToHead'): # BUG: ver los comandos en notación camello, creo que el servidor los usa así, no se puede cambiar.
        target = gpp.node_param(target)._as_target()
        node_list = [x.node_id for x in node_list]
        self.send(
            '/n_order', nod.Node.action_number_for(add_action), # 62
            target.node_id, *node_list)

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


    ### network message bundling ###

    # TODO...


    ### scheduling ###

    def wait(self, response_name): # BUG: la implementación en sclang parece un bug, pero tendríá que ver cómo responde _RoutineResume y cómo se hace el reschedule.
        cond = stm.Condition()

        def resp_func(*_):
            cond.test = True
            cond.signal()

        rdf.OSCFunc(resp_func, response_name, self.addr).one_shot()
        yield from cond.wait()

    # wait_for_boot, is the same as boot except no on_complete if running
    # do_when_booted, is status_watcher._add_boot_action
    # if_running, No.
    # if_not_running, No.

    def boot_sync(self, condition=None):
        condition = condition or stm.Condition()
        condition.test = False

        def func():
            condition.test = True
            condition.signal()

        self.wait_for_boot(func)
        yield from condition.wait()

    def ping(self, n=1, wait=0.1, func=None):
        if not self.status_watcher.server_running:
            _logger.info(f"server '{self.name}' not running")
            return
        result = 0

        def task():
            t = _libsc3.main.elapsed_time()
            self.sync()
            dt = _libsc3.main.elapsed_time() - t
            _logger.info(f'measured latency: {dt}s')
            result = max(result, dt)
            n -= 1
            if n > 0:
                clk.SystemClock.sched(wait, lambda: ping_func())
            else:
                _logger.info(f"maximum determined latency of "
                             f"server '{self.name}': {result}s")

        def ping_func():
            stm.Routine.run(task, clk.SystemClock)

        ping_func()

    def cached_buffers_do(self, func):
        bff.Buffer.cached_buffers_do(self, func)

    def cached_buffer_at(self, bufnum):
        return bff.Buffer.cached_buffer_at(self, bufnum)

    def make_default_groups(self):
        # // Keep defaultGroups for all clients on this server.
        self.default_groups = [nod.Group.basic_new(
            self, self.node_allocator.num_ids * client_id + 1
        ) for client_id in range(self.max_num_clients)]
        self.default_group = self.default_groups[self.client_id]

    def default_group_id(self):
        return self.default_group.node_id

    def send_default_groups(self):
        for group in self.default_groups:
            self.send_msg('/g_new', group.node_id, 0, 0)

    def send_default_groups_for_client_ids(self, client_ids):
        for i in client_ids:
            group = self.default_groups[i]
            self.send_msg('/g_new', group.node_id, 0, 0)

    def input_bus(self):
        return bus.Bus('audio', self.options.num_output_bus_channels,
                        self.options.num_input_bus_channels, self)

    def output_bus(self):
        return bus.Bus('audio', 0, self.options.num_output_bus_channels, self)


    ### recording formats ###

    # These atributes are just a wrapper of ServerOptions, use s.options.
    # @property rec_header_format
    # @property rec_sample_format
    # @property rec_channels
    # @property rec_buf_size


    ### server status ###

    @classmethod
    def resume_status_threads(cls):  # NOTE: for SystemActions.
        for server in cls.all:
            server.status_watcher.resume_alive_thread()


    ### Shared memory interface ###

    def disconnect_shared_memory(self):
        ...

    def connect_shared_memory(self):
        ...

    def has_shm_interface(self):
        ...


    def boot(self, on_complete=None, on_failure=None,
             start_alive=True, recover=False):
        if self.status_watcher.unresponsive:
            _logger.info(f"server '{self.name}' unresponsive, rebooting...")
            self.quit(watch_shutdown=False)

        if self.status_watcher.server_running:
            _logger.info(f"server '{self.name}' already running")
            return

        if self.status_watcher.server_booting:
            _logger.info(f"server '{self.name}' already booting")
            return

        self.status_watcher.server_booting = True

        def _on_complete(server):
            server.status_watcher.server_booting = False
            server._boot_init(recover)
            fn.value(on_complete, server)

        def _on_failure(server):
            server.status_watcher.server_booting = False
            fn.value(on_failure, server)

        self.status_watcher._add_boot_action(_on_complete, _on_failure)

        if self.remote_controlled:
            _logger.info(f"remote server '{self.name}' needs manual boot")
        else:
            def boot_task():
                if self.pid is not None:  # NOTE: pid es el flag que dice si se está/estuvo ejecutando un server local o internal
                    yield from self._pid_release_condition.hang()  # NOTE: signal from _on_server_process_exit from _ServerProcess
                if start_alive:
                    self.boot_server_app(
                        lambda: self.status_watcher.start_alive_thread())
                else:
                    self.boot_server_app()

            stm.Routine.run(boot_task, clk.AppClock)

    # // FIXME: recover should happen later, after we have a valid clientID!
    # // would then need check whether maxLogins and clientID have changed or not,
    # // and recover would only be possible if no changes.
    def _boot_init(self, recover=False):
        # // if(recover) { this.newNodeAllocators } {
        # // 	"% calls newAllocators\n".postf(thisMethod);
        # // this.newAllocators };
        if self.dump_mode != 0:
            self.send_msg('/dumpOSC', self.dump_mode)
        self.connect_shared_memory() # BUG: no está implementado

    def boot_server_app(self, on_complete=None):
        if self.in_process:
            _logger.info('booting internal server')
            self.boot_in_process()  # BUG: not implemented yet
            self.pid = _libsc3.main.pid  # BUG: not implemented yet
            fn.value(on_complete, self)
        else:
            self.disconnect_shared_memory()  # BUG: not implemented yet
            self._server_process = _ServerProcess(self._on_server_process_exit)
            self._server_process.run(self)
            self.pid = self._server_process.proc.pid
            _logger.info(f"booting server '{self.name}' on address "
                         f"{self.addr.hostname}:{self.addr.port}")
            if self.options.protocol == 'tcp':
                print('*** implement tcp connections')
                # self.addr.try_connect_tcp(on_complete)  # BUG: not implemented yet, on_complete would need a wrapper as in quit.
            else:
                fn.value(on_complete, self)

    def _on_server_process_exit(self, exit_code):
        self.pid = None
        self._pid_release_condition.signal()
        _logger.info(f"Server '{self.name}' exited with exit code {exit_code}.")
        self.status_watcher.quit(watch_shutdown=False)  # *** NOTE: este quit se llama cuando temina el proceso y cuando se llama a server.quit.

    def reboot(self, func=None, on_failure=None): # // func is evaluated when server is off
        if not self.is_local:
            _logger.info("can't reboot a remote server")
            return

        if self.status_watcher.server_running\
        and not self.status_watcher.unresponsive:
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

    def quit(self, on_complete=None, on_failure=None, watch_shutdown=True):
        # if server is not running or is running but unresponsive.
        if not self.status_watcher.server_running\
        or self.status_watcher.unresponsive:
            _logger.info(f'server {self.name} is not running')
            return

        if self.status_watcher.server_quiting:
            _logger.info(f"server '{self.name}' already quiting")
            return

        self.status_watcher.server_quiting = True
        self.addr.send_msg('/quit')

        def _on_complete():
            self.status_watcher.server_quiting = False
            fn.value(on_complete, self)  # *** BUG: try_disconnect_tcp

        def _on_failure():
            self.status_watcher.server_quiting = False
            fn.value(on_failure, self)  # *** BUG: try_disconnect_tcp

        if watch_shutdown and self.status_watcher.unresponsive:
            _logger.info(f"server '{self.name}' was "
                         "unresponsive, quitting anyway")
            watch_shutdown = False

        if self.options.protocol == 'tcp':
            self.status_watcher.quit(
                lambda: self.addr.try_disconnect_tcp(_on_complete, _on_failure),  # *** BUG: envuelvo las funciones que son para server y status_watcher para pasar self, la implementación en sclang de try_disconnect_tcp le pasa addr a ambos incluso cuando a onComplete no se le pasa nada nunca y a onFailure se le pasa server *solo* en status_watcher.
                None, watch_shutdown)
        else:
            self.status_watcher.quit(_on_complete, _on_failure, watch_shutdown)

        if self.in_process:
            self.quit_in_process()  # *** BUG: no existe.
            _logger.info('internal server has quit')
        else:
            _logger.info(f"'/quit' message sent to server '{self.name}'")

        self._max_num_clients = None

        # *** TODO:
        # if(scopeWindow.notNil) { scopeWindow.quit }  # No.
        self._volume.free_synth()
        nod.RootNode(self).free_all()
        self.new_allocators()

    @classmethod
    def quit_all(cls, watch_shutdown=True):
        for server in cls.all:
            if server.is_local:
                server.quit(watch_shutdown=watch_shutdown)

    @classmethod
    def free_all(cls, even_remote=False):  # All refers to cls.all.
        if even_remote:
            for server in cls.all:
                if server.status_watcher.server_running:
                    server.free_nodes()
        else:
            for server in cls.all:
                if server.is_local and server.status_watcher.server_running:
                    server.free_nodes()

    def free_nodes(self):  # Instance free_all in sclang.
        self.send_msg('/g_freeAll', 0)
        self.send_msg('/clearSched')
        self.init_tree()

    def free_default_group(self):
        self.send_msg('g_freeAll', self.default_group.node_id)

    def free_default_groups(self):
        for group in self.default_groups:
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

    @classmethod
    def all_booted_servers(cls):
        return set(s for s in cls.all if s.status_watcher.has_booted)

    @classmethod
    def all_running_servers(cls):
        return set(s for s in cls.all if s.status_watcher.server_running)


    ### volume control ###

    @property
    def volume(self):
        return self._volume

    @property
    def gain(self):
        return self._volume.gain

    @gain.setter
    def gain(self, value):  # Was volume_
        self._volume.gain = value

    def mute(self):
        self._volume.mute()

    def unmute(self):
        self._volume.unmute()


    ### recording output ###
    # TODO

    # L1203
    ### internal server commands ###
    # TODO

    # L1232
    # /* CmdPeriod support for Server-scope and Server-record and Server-volume */
    # TODO

    def query_all_nodes(self, query_controls=False, timeout=3):
        if self.is_local:
            self.send_msg('/g_dumpTree', 0, int(query_controls))
        else:
            done = False

            def resp_func(msg, *_):
                i = 2
                tabs = 0
                if msg[1] != 0:
                    print_controls = True
                else:
                    print_controls = False
                outstr = f'NODE TREE Group {msg[2]}\n'
                if msg[3] > 0:
                    def dump_func(num_children):
                        nonlocal i, tabs, outstr
                        tabs += 1
                        for _ in range(num_children):
                            if msg[i + 1] >= 0:
                                i += 2
                            else:
                                if print_controls:
                                    i += msg[i + 3] * 2 + 1
                                i += 3
                            outstr += '   ' * tabs + f'{msg[i]}' # // nodeID
                            if msg[i + 1] >= 0:
                                outstr += ' group\n'
                                if msg[i + 1] > 0:
                                    dump_func(msg[i + 1])
                            else:
                                outstr += f' {msg[i + 2]}\n' # // defname
                                if print_controls:
                                    if msg[i + 3] > 0:
                                        outstr += ' ' + '   ' * tabs
                                    j = 0
                                    for _ in range(msg[i + 3]):
                                        outstr += ' '
                                        if type(msg[i + 4 + j]) is str:
                                            outstr += f'{msg[i + 4 + j]}: '
                                        outstr += f'{msg[i + 5 + j]}'
                                        j += 2
                                    outstr += '\n'
                        tabs -= 1

                    dump_func(msg[3])

                print(outstr)
                nonlocal done
                done = True

            resp = rdf.OSCFunc(resp_func, '/g_queryTree.reply', self.addr)
            resp.one_shot()

            def timeout_func():
                if not done:
                    resp.free()
                    _logger.warning(f"remote server '{self.name}' failed "
                                    "to respond to '/g_queryTree' after "
                                    f"{timeout} seconds")

            self.send_msg('/g_queryTree', 0, int(query_controls))
            clk.SystemClock.sched(timeout, timeout_func)

    # L1315
    # funciones set/getControlBug*
    # TODO


    ### Node parameter interface ###

    def _as_target(self):
        return self.default_group

    # def scsynth(cls): No.
    # def supernova(cls): No.
    # def from_name(cls): No.
    # def kill_all(cls): No.


class _ServerProcess():
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
