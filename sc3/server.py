"""Server.sc"""

import subprocess as _subprocess
import threading as _threading
import atexit as _atexit
import warnings as _warnings
import os as _os
import pathlib as _pathlib

from . import main as _libsc3
from . import utils as utl
from . import netaddr as nad
from . import model as mdl
from . import engine as eng
from . import synthdef as sdf
from . import clock as clk
from . import systemactions as sac
from . import serverstatus as sst
from . import responsedefs as rdf
from . import stream as stm
from . import node as nod
from . import bus
from . import graphparam as gpp
from . import buffer as bff


# BUG: revisar porque hay un patch que cambió esto y otros que cambiaron un par
# BUG: de cosas, el problema es que los patch se aplican meses después a master.
# Esto de acá abajo lo hace con un diccionario en initClass, me parece mejor.
# command line server exec default values
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


class ServerOptions():
    def __init__(self):
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

    @property
    def device(self):
        if self.in_device == self.out_device:
            return self.in_device
        else:
            return (self.in_device, self.out_device)
    @device.setter
    def device(self, value):
        self.in_device = self.out_device = value

    def as_options_string(self, port=57110): # BUG: el nombre está mal, acá no es un string, tengo que reveer la generación de cmd
        o = []

        if self.protocol == 'tcp':
            o.append('-t')
        else:
            o.append('-u')
        o.append(str(port))

        o.append('-a')
        o.append(str(self.num_private_audio_bus_channels
                     + self.num_input_bus_channels
                     + self.num_output_bus_channels))

        if self.num_control_bus_channels != _NUM_CONTROL_BUS_CHANNELS:
            o.append('-c')
            o.append(str(self.num_control_bus_channels))
        if self.num_input_bus_channels != _NUM_INPUT_BUS_CHANNELS:
            o.append('-i')
            o.append(str(self.num_input_bus_channels))
        if self.num_output_bus_channels != _NUM_OUTPUT_BUS_CHANNELS:
            o.append('-o')
            o.append(str(self.num_output_bus_channels))
        if self.num_buffers != _NUM_BUFFERS:
            o.append('-b')
            o.append(str(self.num_buffers))
        if self.max_nodes != _MAX_NODES:
            o.append('-n')
            o.append(str(self.max_nodes))
        if self.max_synth_defs != _MAX_SYNTH_DEFS:
            o.append('-d')
            o.append(str(self.max_synth_defs))
        if self.block_size != _BLOCK_SIZE:
            o.append('-z')
            o.append(str(self.block_size))
        if self.hardware_buffer_size is not None: # BUG: ver, la lógica de esto es endeble
            o.append('-Z')
            o.append(str(self.hardware_buffer_size))
        if self.mem_size != _MEM_SIZE:
            o.append('-m')
            o.append(str(self.mem_size))
        if self.num_rgens != _NUM_RGENS:
            o.append('-r')
            o.append(str(self.num_rgens))
        if self.num_wire_bufs != _NUM_WIRE_BUFS:
            o.append('-w')
            o.append(str(self.num_wire_bufs))
        if self.sample_rate is not None: # BUG: ver, la lógica de esto es endeble
            o.append('-S')
            o.append(str(self.sample_rate))
        if not self.load_defs: # BUG: ver, la lógica de esto es endeble
            o.append('-D')
            o.append('0')
        if self.input_streams_enabled is not None: # BUG: ver, la lógica de esto es endeble
            o.append('-I')
            o.append(self.input_streams_enabled) # es un string
        if self.output_streams_enabled is not None: # BUG: ver, la lógica de esto es endeble
            o.append('-O')
            o.append(self.output_streams_enabled) # es un string

        # if _libsc3.main.platform.name != 'osx'\
        # or self.in_device == self.out_device: # BUG: no está implementado: thisProcess.platform.name
        if self.in_device == self.out_device: # BUG: borrar, va lo de arriba pero implementado
            if self.in_device is not None:
                o.append('-H')
                o.append('"{}"'.format(self.in_device)) # BUG: comprobar que funciona en Python
        else:
            o.append('-H')
            params = '"{}" "{}"'.format(str(self.in_device), str(self.out_device)) # BUG: comprobar que funciona en Python
            o.append(params)

        if self.verbosity != _VERBOSITY:
            o.append('-V')
            o.append(str(self.verbosity))
        if not self.zeroconf: # BUG: ver, la lógica de esto es endeble
            o.append('-R')
            o.append('0')
        if self.restricted_path is not None:
            o.append('-P')
            o.append(str(self.restricted_path)) # puede ser str o Path
        if self.ugen_plugins_path is not None:
            o.append('-U')
            plist = utl.as_list(self.ugen_plugins_path)
            plist = [_os.path.normpath(x) for x in plist] # BUG: ensure platform format? # BUG: windows drive?
            o.append(_os.pathsep.join(plist))
        if self.memory_locking:
            o.append('-L')
        if self.threads is not None:
            if Server.program.endswith('supernova'):
                o.append('-T')
                o.append(str(self.threads))
        if self.use_system_clock is not None:
            o.append('-C')
            o.append(int(self.use_system_clock))
        if self.max_logins is not None:
            o.append('-l')
            o.append(str(self.max_logins))
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
        cls.named = dict()
        cls.all = set()
        cls.program = 'scsynth' # *** BUG: setea en Platform OSX/Linux startup
        cls.sync_s = True

        cls.node_alloc_class = eng.NodeIDAllocator
        # // cls.node_alloc_class = ReadableNodeIDAllocator;
        cls.buffer_alloc_class = eng.ContiguousBlockAllocator
        cls.bus_alloc_class = eng.ContiguousBlockAllocator

        cls._default = cls.local = cls('localhost',
                                       nad.NetAddr('127.0.0.1', 57110))
        # cls.internal = cls('internal',
        #                    nad.NetAddr(None, None))  # No internal by now.

    @property
    def default(cls):
        return cls._default

    @default.setter
    def default(cls, value):
        cls._default = value
        if cls.sync_s:
            global s
            s = value # BUG: ver, puede que no sea bueno para Python.
        for server in cls.all:
            # server.changed(\default, value)
            mdl.NotificationCenter.notify(server, 'default', value)


class Server(gpp.NodeParameter, metaclass=MetaServer):
    @classmethod
    def from_name(cls, name):
        return cls.named[name] or cls(name, nad.NetAddr("127.0.0.1", 57110)) # BUG: en sclang, no tiene sentido llamar a ServerOptions.new, init provee una instancia por defecto

    @classmethod
    def remote(cls, name, addr, options, client_id):
        result = cls(name, addr, options, client_id)
        result.start_alive_thread()
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
        self.send_quit = None # inicializa en boot_init

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

        #self.volume = xxx.Volume(server=self, persist=True) # BUG: falta implementar
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
        self._server_interface = None
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

    # L357
    @property
    def addr(self):
        return self._addr

    @addr.setter
    def addr(self, value):
        self._addr = value or nad.NetAddr("127.0.0.1", 57110) # TODO: podría hacer que se pueda pasar también una tupla como en liblo
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
            msg = "Server name '{}' already exists. Please use a unique name"
            _warnings.warn(msg.format(value)) # BUG: en sclang, pasa dos parámetros a format # TODO: por qué no es una excepción?
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
        clk.AppClock.sched(0, init_task)

    # client ID

    # // clientID is settable while server is off, and locked while server is running
    # // called from prHandleClientLoginInfoFromServer once after booting.
    @property
    def client_id(self):
        return self._client_id

    @client_id.setter
    def client_id(self, value):
        msg = "Server {} couldn't set client_id to {} - {}. clientID is still {}"
        if self.status_watcher.server_running:
            _warnings.warn(msg.format(self.name, value,
                                      'server is running', self.client_id))
            return # BUG: los setters de la propiedades retornan el valor? qué pasa cuando falla un setter?
        if not isinstance(value, int):
            _warnings.warn(msg.format(self.name, value,
                                      'not an int', self.client_id))
            return # BUG: idem
        if value < 0 or value >= self.max_num_clients:
            msg2 = '"outside max_num_clients range of 0 - {}"'
            msg2 = msg2.format(self.max_num_clients - 1)
            _warnings.warn(msg.format(self.name, value, msg2, self.client_id))
            return # BUG: idem
        if self._client_id != value:
            print("{} : setting clientID to {}".format(self.name, value)) # TODO: es un LOG, probablemente hayan funciones para hacer logs!
        self._client_id = value
        self.new_allocators() # TODO: parece un método privado pero lo usan en UnitTest-bootServer

    # L414
    # /* clientID-based id allocators */

    def new_allocators(self):
        self.new_node_allocators()
        self.new_bus_allocators()
        self.new_buffer_allocators()
        self.new_scope_buffer_allocators()
        mdl.NotificationCenter.notify(self, 'new_allocators')

    def new_node_allocators(self):
        self.node_allocator = type(self).node_alloc_class(
            self.client_id,
            self.options.initial_node_id,
            # self.max_num_clients # BUG: en sclang, node_alloc_class es eng.NodeIDAllocator por defecto, los alocadores originales reciben 2 parámetros, ContiguousBlockAllocator, que se usa para buses y buffers, recibe uno más, cambia la interfaz. Acá se pasa el tercer parámetro y NodeIDAllocator lo ignora (característica de las funciones de sclang), tengo que ver cómo maneja los ids de los nodos por cliente.
        )
        # // defaultGroup and defaultGroups depend on allocator,
        # // so always make them here:
        self.make_default_groups()

    def new_bus_allocators(self):
        audio_bus_io_offset = self.options.first_private_bus()
        num_ctrl_per_client = (self.options.num_control_bus_channels
                               // self.max_num_clients)
        num_audio_per_client = (self.options.num_audio_bus_channels
                                - audio_bus_io_offset) // self.max_num_clients
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
                msg = 'No block of {} consecutive buffer numbers is available'
                raise Exception(msg.format(n))
            else:
                msg = 'No more buffer numbers, free some buffers before allocating'
                raise Exception(msg)
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

    # BUG: VER: esta función y la siguiente no parecen usarde desde sclang
    def _handle_client_login_info_from_server(self, new_client_id=None,
                                              new_max_logins=None): # BUG: name!
        # // only set maxLogins if not internal server
        if not self.in_process:
            if new_max_logins is not None:
                if new_max_logins != self.options.max_logins:
                    msg = "{}: server process has max_logins {} - adjusting options accordingly"
                    print(msg.format(self.name, new_max_logins)) # BUG: es log
                else:
                    msg = "{}: server process's max_logins ({}) matches current options"
                    print(msg.format(self.name, new_max_logins)) # BUG: ídem
                self.options.max_logins = self._max_num_clients = new_max_logins
            else:
                msg = "{}: no max_logins info from server process" # BUG: no entiendo por qué dice from si es un parámetro que se le pasa a esta función
                print(msg.format(self.name, new_max_logins)) # BUG: ídem
        if new_client_id is not None:
            if new_client_id == self.client_id:
                msg = "{}: keeping client_id ({}) as confirmed by server process"
                print(msg.format(self.name, new_client_id)) # BUG: ídem
            else:
                msg = "{}: setting client_id to {}, as obtained from server process" # BUG: ídem no entiendo, no sé quién llama a esta función
                print(msg.format(self.name, new_client_id))
            self.client_id = new_client_id # usa el setter de @property

    def _handle_notify_fail_string(self, fail_string, msg): # TODO: yo usé msg en vez de failstr arriba.
        # // post info on some known error cases
        if 'already registered' in fail_string: # TODO: es un poco cruda la comparación con el mensaje... y tiene que coincidir, no sé dónde se genera.
            # // when already registered, msg[3] is the clientID by which
            # // the requesting client was registered previously
            log_msg = "{} - already registered with client_id {}"
            print(log_msg.format(self.name, msg[3])) # BUG: log
            self.status_watcher._handle_login_when_already_registered(msg[3]) # BUG: falta implmementar, cuidado con el nombre
        elif 'not registered' in fail_string:
            # // unregister when already not registered:
            log_msg = "{} - not registered"
            print(log_msg.format(self.name)) # BUG: log
            self.status_watcher.notified = False
        elif 'too many users' in fail_string:
            log_msg = "{} - could not register, too many users"
            print(log_msg.format(self.name)) # BUG: log
            self.status_watcher.notified = False
        else:
            # // throw error if unknown failure
            e_msg = "Failed to register with server '{}' for notifications: {}\n"
            e_msg += "To recover, please reboot the server"
            raise Exception(e_msg.format(self.name, msg)) # BUG: el formato de msg y la nueva línea de e_msg

    # L634
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

        def resp_func(*msg): # TODO: agregar decorador luego
            if str(msg[1]) == cmd_name:
                resp.free()
                condition.test = True
                condition.signal()

        resp = rdf.OSCFunc(resp_func, '/done', self.addr) # BUG: aún faltan implementar la clase OSCFuncAddrMessageMatcher que llama internamente el dispatcher
        self.send_bundle(0, args)
        yield from condition.wait()

    def sync(self, condition=None, bundles=None, latency=0): # BUG: dice bundles, tengo que ver el nivel de anidamiento
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
            target.node_id, *node_list
        )

    # // load from disk locally, send remote
    def send_synthdef(self, name, dir=None):
        dir = dir or sdf.SynthDef.synthdef_dir
        dir = _pathlib.Path(dir)
        full_path = dir / (name + '.scsyndef')
        try:
            with open(full_path, 'rb') as file:
                buffer = file.read()
                self.send_msg('/d_recv', buffer)
        except FileNotFoundError:
            msg = "Server: send_synthdef FileNotFoundError: {}"
            _warnings.warn(msg.format(full_path))

    # // tell server to load from disk
    def load_synthdef(self, name, completion_msg=None, dir=None): # BUG: creo que completion_msg no tiene efecto, nota listSendMsg no hace nada.
        dir = dir or sdf.SynthDef.synthdef_dir
        dir = _pathlib.Path(dir)
        path = str(dir / (name + '.scsyndef'))
        self.send_msg('/d_load', path) # BUG: completion_msg BUG: puede ser que se invoque a bajo nivel en sclang?

    # // /d_loadDir
    def load_directory(self, dir, completion_msg=None): # BUG: completion_msg
        self.send_msg('/d_loadDir', dir) # BUG: completion_msg

    # L722
    ### network message bundling ###
    # TODO

    # L761
    ### scheduling ###

    def wait(self, response_name): # BUG: la implementación en sclang parece un bug, pero tendríá que ver cómo responde _RoutineResume y cómo se hace el reschedule.
        cond = stm.Condition()

        def resp_func():
            cond.test = True
            cond.signal()

        rdf.OSCFunc(resp_func, response_name, self.addr).one_shot()
        yield from cond.wait()

    def wait_for_boot(self, on_complete, limit=100, on_failure=None):
        # // onFailure.true: why is this necessary?
        # // this.boot also calls doWhenBooted.
        # // doWhenBooted prints the normal boot failure message.
        # // if the server fails to boot, the failure error gets posted TWICE.
        # // So, we suppress one of them.
        if not self.status_watcher.server_running:
            self.boot(on_failure=True) # BUG: ver true y por qué no nil, es la razón de todo el comentario
        self.do_when_booted(on_complete, limit, on_failure)

    def do_when_booted(self, on_complete, limit=100, on_failure=None):
        self.status_watcher.do_when_booted(on_complete, limit, on_failure)

    def if_running(self, func, fail_func=lambda s: None): # TODO: no se usa, pero como llama a statusWatcher puede ser útil
        if self.status_watcher.unresponsive:
            print("server '{}' not responsive".fromat(self.name)) # BUG: log
            fail_func(self)
        elif self.status_watcher.server_running:
            func(self)
        else:
            print("server '{}' no running".fromat(self.name)) # BUG: log
            fail_func(self)
        # NOTE: no retorna nada a diferencia de sclang, se podría comprobar el
        # valor de retorno en vez de postear, esta función no está documentada.

    def if_not_running(self, func): # TODO: no se usa, pero como llama a statusWatcher puede ser útil
        self.if_running(lambda s: None, func) # NOTE: para el caso if_running deberíá postear 'server tal funning' en caso de error
        # NOTE: Ídem.

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
            print('server not running')
            return
        result = 0

        def task():
            t = _libsc3.main.elapsed_time()
            self.sync()
            dt = _libsc3.main.elapsed_time() - t
            print('measured latency: {}s'.format(dt))
            result = max(result, dt)
            n -= 1
            if n > 0:
                clk.SystemClock.sched(wait, lambda: ping_func())
            else:
                msg = 'maximum determined latency of {}: {}s'
                print(msg.format(self.name, result))

        def ping_func():
            stm.Routine.run(task, clk.SystemClock) # NOTE: Routine.run usa SystemClock por defecto (con un checkeo puesto demás en sclang, y acá, porque es lo que pasa a bajo nivel)
        ping_func()

    def cached_buffers_do(self, func):
        bff.Buffer.cached_buffers_do(self, func)

    def cached_buffer_at(self, bufnum):
        return bff.Buffer.cached_buffer_at(self, bufnum)

    # // keep defaultGroups for all clients on this server:
    def make_default_groups(self):
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

    # L877
    ### recording formats ###
    # TODO

    # L888
    ### server status ###

    @property
    def num_ugens(self):
        return self.status_watcher.num_ugens

    @property
    def num_synths(self):
        return self.status_watcher.num_synths

    @property
    def num_groups(self):
        return self.status_watcher.num_groups

    @property
    def num_synthdefs(self):
        return self.status_watcher.num_synthdefs

    @property
    def avg_cpu(self):
        return self.status_watcher.avg_cpu

    @property
    def peak_cpu(self):
        return self.status_watcher.peak_cpu

    @property
    def sample_rate(self):
        return self.status_watcher.sample_rate

    @property
    def actual_sample_rate(self):
        return self.status_watcher.actual_sample_rate

    @property
    def has_booted(self):
        return self.status_watcher.has_booted

    @property
    def server_running(self):
        return self.status_watcher.server_running

    @property
    def server_booting(self):
        return self.status_watcher.server_booting

    @property
    def unresponsive(self):
        return self.status_watcher.unresponsive

    # no es property
    def start_alive_thread(self, delay=0.0):
        self.status_watcher.start_alive_thread(delay)

    # no es property
    def stop_alive_thread(self):
        self.status_watcher.stop_alive_thread()

    @property
    def alive_thread_is_running(self):
        return self.status_watcher.alive_thread.playing()

    @property
    def alive_thread_period(self):
        return self.status_watcher.alive_thread_period

    @alive_thread_period.setter
    def alive_thread_period(self, value):
        self.status_watcher.alive_thread_period = value

    # shm
    def disconnect_shared_memory(self):
        pass

    def connect_shared_memory(self):
        pass

    def has_shm_interface(self):
        pass

    @classmethod
    def resume_threads(cls):
        for server in cls.all:
            server.status_watcher.resume_thread()

    # L931
    def boot(self, start_alive=True, recover=False, on_failure=None):
        if self.status_watcher.unresponsive:
            print("server '{}' unresponsive, rebooting...".format(self.name)) # BUG: log
            self.quit(watch_shutdown=False)
        if self.status_watcher.server_running:
            print("server '{}' already running".format(self.name))
            return
        if self.status_watcher.server_booting:
            print("server '{}' already booting".format(self.name))
            return
        self.status_watcher.server_booting = True

        def on_complete():
            self.status_watcher.server_booting = False
            self.boot_init(recover)
        self.status_watcher.do_when_booted(on_complete, on_failure) # BUG: en sclang, esta llamada pasa false si on_failure es nil y do_when_booted checkea por notNil (false es true)

        if self.remote_controlled:
            print("remote server '{}' needs manual boot".format(self.name)) # BUG: log
        else:
            def ping_func():
                self.quit()
                self.boot()

            def on_failure():
                self._wait_for_pid_release(
                    lambda: self.boot_server_app(\
                        lambda: self.status_watcher.start_alive_thread()\
                        if start_alive else None\
                    ) # TODO: lambda siempre retorna un valor, no afecta pero no se puede usar como en sclang es rebuscado acá
                )
            self._ping_app(ping_func, on_failure, 0.25)

    # // FIXME: recover should happen later, after we have a valid clientID!
    # // would then need check whether maxLogins and clientID have changed or not,
    # // and recover would only be possible if no changes.
    def boot_init(self, recover=False):
        # // if(recover) { this.newNodeAllocators } {
        # // 	"% calls newAllocators\n".postf(thisMethod);
        # // this.newAllocators };
        if self.dump_mode != 0:
            self.send_msg('/dumpOSC', self.dump_mode)
        if self.send_quit is None:
            self.send_quit = self.in_process or self.is_local
        self.connect_shared_memory() # BUG: no está implementado

    def _ping_app(self, func, on_failure=None, timeout=3): # subida de 'internal server commands'
        id = func.__hash__() # *** BUG: el número excede el tipo int de OSC.

        def resp_func(msg, *args):
            if msg[1] == id:
                func()
                task.stop()

        if timeout is not None:
            def task():
                yield timeout
                resp.free()
                if on_failure is not None:
                    on_failure()
        else:
            def task():
                pass # no hace nada

        resp = rdf.OSCFunc(resp_func, '/synced', self.addr)
        stm.Routine.run(task, clk.AppClock)
        self.addr.send_msg('/sync', id)

    def _wait_for_pid_release(self, on_complete, on_failure=None, timeout=1):
        if self.in_process or self.is_local or self.pid is None:
            on_complete()
            return

        # // FIXME: quick and dirty fix for supernova reboot hang on macOS:
        # // if we have just quit before running server.boot,
        # // we wait until server process really ends and sets its pid to nil
        # BUG: puede que todo esto no sea necesario con python Popen (_ServerProcess)
        waiting = True
        clk.AppClock.sched( # usa SystemClock pero no me parece que bootear el servidor sea time critical, y dice que es un hack
            timeout,
            lambda: self.pid_release_condition.unhang() if waiting else None # BUG: la condición no está definida
        )
        def task():
            self.pid_release_condition.hang() # BUG: revisar
            if self.pid_release_condition.test(): # BUG: revisar
                waiting = False
                on_complete()
            else:
                on_failure()
        stm.Routine.run(task, clk.AppClock)

    def boot_server_app(self, on_complete):
        print('* boot_server_app: falta implementar todo lo relacionado con popen y options')
        if self.in_process:
            print('booting internal server')
            self.boot_in_process() # BUG: no está implementado
            self.pid = _libsc3.main.pid # BUG: no está implementado
            on_complete()
        else:
            self.disconnect_shared_memory() # BUG: no está implementado
            self.server_process = _ServerProcess(self.options)
            self.server_process.run()
            # this.prOnServerProcessExit(exitCode) BUG: falta implementar en _ServerProcess
            self.pid = self.server_process.proc.pid # BUG: con Popen la implementación de algunas cosas puede cambiar
            msg = "booting server '{}' on address {}:{}."
            print(msg.format(self.name, self.addr.hostname, self.addr.port)) # BUG: log
            if self.options.protocol == 'tcp':
                print('implementar conexión tcp')
                # self.addr.try_connect_tcp(on_complete)
            else:
                on_complete()

    def _on_server_process_exit(self, exit_code): # BUG: este método sería distinto porque process es distinto acá, se usaba en boot_server_app
        pass

    def reboot(self, func=None, on_failure=None): # // func is evaluated when server is off
        if not self.is_local:
            print("can't reboot a remote server") # BUG: log
            return
        if self.server_status.server_running\
        and not self.status_watcher.unresponsive:
            def _():
                if func is not None:
                    func()
                clk.defer(lambda: self.boot()) # NOTE: usa AppClock en sclang
            self.quit(_, on_failure)
        else:
            if func is not None:
                func()
            self.boot(on_failure=on_failure)

    def application_running(self): # TODO: este método se relaciona con server_running que es propiedad, ver
        return self.server_process.proc.poll() is None

    def status(self):
        self.addr.send_status_msg() # // backward compatibility

    def send_status_msg(self): # BUG: este método tal vez no vaya? o el de arriba?
        self.addr.send_status_msg()

    @property
    def notify(self):
        return self.status_watcher.notify

    @notify.setter
    def notify(self, value):
        self.status_watcher.notify = value

    @property
    def notified(self):
        return self.status_watcher.notified

    def dump_osc(self, code=1):
        # 0 - turn dumping OFF.
        # 1 - print the parsed contents of the message.
        # 2 - print the contents in hexadecimal.
        # 3 - print both the parsed and hexadecimal representations of the contents.
        self.dump_mode = code
        self.send_msg('/dumpOSC', code)
        mdl.NotificationCenter.notify(self, 'dump_osc', code)

    def quit(self, on_complete=None, on_failure=None, watch_shutdown=True):
        self.addr.send_msg('/quit')

        if watch_shutdown and self.status_watcher.unresponsive:
            msg = "Server '{}' was unresponsive, quitting anyway"
            print(msg.format(self.name)) # BUG: log
            watch_shutdown = False

        if self.options.protocol == 'tcp':
            self.status_watcher.quit(
                lambda: self.addr.try_disconnect_tcp(on_complete, on_failure),
                None, watch_shutdown
            )
        else:
            self.status_watcher.quit(on_complete, on_failure, watch_shutdown)

        if self.in_process:
            self.quit_in_process()
            print('internal server has quit') # BUG: log
        else:
            print("'/quit' message sent to server '{}'".format(self.name))

        self.server_process.finish()
        self.pid = None
        self.send_quit = None
        self._max_num_clients = None

        # TODO:
        print('server.py: implementar scope_window (tal vez no) y volume')
        # if(scopeWindow.notNil) { scopeWindow.quit }
        # self.volume.free_synth
        nod.RootNode(self).free_all() # BUG: no entiendo por qué crea una instancia
        self.new_allocators()

    @classmethod
    def quit_all(cls, watch_shutdown=True):
        for server in cls.all:
            if server.send_quit is True:
                server.quit(watch_shutdown=watch_shutdown)

    @classmethod
    def kill_all(cls):
        # // if you see Exception in World_OpenUDP: unable to bind udp socket
        # // its because you have multiple servers running, left
        # // over from crashes, unexpected quits etc.
        # // you can't cause them to quit via OSC (the boot button)
        # // this brutally kills them all off
        # thisProcess.platform.killAll(this.program.basename);
        # this.quitAll(watchShutDown: false);
        print('* implementar Server.kill platform.kill_all') # BUG: implementar

    def free_all(self): # BUG: VER tiene variante como @classmethod
        self.send_msg('/g_freeAll', 0)
        self.send_msg('/clearSched')
        self.init_tree()
    # @classmethod
    # def free_all(cls, even_remote=False): pass # BUG: IMPLEMENTAR NO SÉ CÓMO, hace lo mismo que hard_free_all, llama al método de instancia en cada server.

    def free_my_default_group(self):
        self.send_msg('g_freeAll', self.default_group.node_id)

    def free_default_groups(self):
        for group in self.default_groups:
            self.send_msg('g_freeAll', group.node_id)

    @classmethod
    def hard_free_all(cls, even_remote=False):
        if even_remote:
            for server in cls.all:
                server.free_all()
        else:
            for server in cls.all:
                if server.is_local:
                    server.free_all()

    @classmethod
    def all_booted_servers(cls):
        return [x for x in cls.all if x.has_booted]

    @classmethod
    def all_running_servers(cls):
        return [x for x in cls.all if x.server_running]

    # L1181
    ### volume control ###
    # TODO

    # L1195
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
                    _warnings.warn(
                        f"remote server '{self.name}' failed to respond "
                        f"to '/g_queryTree' after {timeout} seconds"
                    )

            self.send_msg('/g_queryTree', 0, int(query_controls))
            clk.SystemClock.sched(timeout, timeout_func)

    # L1315
    # funciones set/getControlBug*
    # TODO

    @classmethod
    def scsynth(cls):
        # BUG: ver, no me parece buena idea, además setea el valor en
        # ./Platform/osx/OSXPlatform.sc o ./Platform/linux/LinuxPlatform.sc
        # dentro del método startup.
        cls.program = cls.program.replace('supernova', 'scsynth')

    @classmethod
    def supernova(cls):
        cls.program = cls.program.replace('scsynth', 'supernova')


    ### Node parameter interface ###

    def _as_target(self):
        return self.default_group


class _ServerProcess():
    def __init__(self, options):
        self.options = options
        self.proc = None
        self.timeout = 0.1

    def run(self):
        # TEST HACK
        cmd = [Server.program]
        cmd.extend(self.options.as_options_string())
        # END OF TEST HACK
        self.proc = _subprocess.Popen(
            cmd, # self.options.cmd(), # BUG: ver cómo defino cmd, podría ser una función que lo genere a partir de server options, server y platform.
            stdout=_subprocess.PIPE,
            stderr=_subprocess.PIPE,
            bufsize=1,
            universal_newlines=True)
        self._redirect_outerr()
        _atexit.register(self._terminate_proc) # BUG: no compruebo que no se agreguen más si se reinicia el cliente.

    def _terminate_proc(self):
        try:
            if self.proc.poll() is None:
                self.proc.terminate()
                self.proc.wait(timeout=self.timeout)
        except _subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.communicate() # just to be polite

    def finish(self):
        self._tflag.set()
        self._tout.join()
        self._terr.join()
        self.proc.wait(timeout=self.timeout) # async must be
        self._terminate_proc() # same

    def _redirect_outerr(self):
        def read(out, flag):
            while not flag.is_set():
                line = out.readline()
                if line:
                    print(line, end='')

        def make_thread(out, flag):
            t = _threading.Thread(target=read, args=(out, flag))
            t.daemon = True
            t.start()
            return t

        self._tflag = _threading.Event()
        self._tout = make_thread(self.proc.stdout, self._tflag) # 'SCOUT:'
        self._terr = make_thread(self.proc.stdout, self._tflag) # 'SCERR:'
