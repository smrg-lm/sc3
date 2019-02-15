"""Server.sc"""

import subprocess as _subprocess
import threading as _threading
import atexit as _atexit
import warnings as _warnings
import os as _os
import pathlib as _pathlib

import liblo as _lo

import supercollie.utils as utl
import supercollie.netaddr as nad
import supercollie.client as clt
import supercollie.model as mdl
import supercollie.engine as eng
import supercollie.synthdef as sdf
import supercollie.clock as clk
import supercollie.systemactions as sac

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


class ServerOptions(object):
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

    def as_options_string(self, port=57110):
        o = []

        if self.protocol == 'tcp':
            o.append('-t')
        else:
            o.append('-u')
        o.append(str(port))

        o.append('-a')
        o.append(self.num_private_audio_bus_channels
                 + self.num_input_bus_channels
                 + self.num_output_bus_channels)

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

        if xxx.Main.singleton.platform.name != 'osx'\
        or self.in_device == self.out_device: # BUG: no está implementado: thisProcess.platform.name
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
    def num_audio_bus_channels(self, value=1024):
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


# TODO: TEST, acá uso una metaclase para definir propiedades de la
# (sub)clase. revisar la construcción de UGen y otras, aunque creo
# que no era necesario emplear este tipo de mencanismos. Me falta ver
# bien cómo es que funcionan las metaclases y cuál es us uso habitual.
# Las propiedades de metaclass son propiedades de clase en la clase
# derivada, ojo, no hay relación instancia/clase como en los
# métodos comunes, en la metaclass todo es selfy, así funciona.
# TODO: El único problema es que no aparecen en dir(Server)
# TODO: Veo que se usa también type(self) para acceder a la clase en vez
# de self.__class__, ver cuál es la diferencia.
class MetaServer(type):
    local = None
    internal = None
    _default = None

    named = dict()
    all = set()
    program = None
    sync_s = True

    node_alloc_class = eng.NodeIDAllocator
    # // node_alloc_class = ReadableNodeIDAllocator;
    buffer_alloc_class = eng.ContiguousBlockAllocator
    bus_alloc_class = eng.ContiguousBlockAllocator

    @property
    def default(self):
        return self._default

    @default.setter
    def default(self, value):
        self._default = value
        if self.sync_s:
            global s
            s = value
        for server in self.all:
            #server # .changed(\default, value) # BUG: usar mdl.NotificationCenter
            raise Exception('Implementar la funcionalidad mdl.NotificationCenter en MetaServer @default.setter')


@utl.initclass
class Server(metaclass=MetaServer):
    def __init_class__(cls): # BUG: ver: __new__ es un método estático tratado de manera especial por el intérprete, tal vez este se podría definir como tal, los métodos estáticos no están ligados ni a la clase ni a la instancia.
                             # BUG: PERO __init_subclass___: "If defined as a normal instance method, this method is implicitly converted to a class method."
        cls._default = cls.local = cls('localhost', nad.NetAddr('127.0.0.1', 57110))
        cls.internal = Server('internal', nad.NetAddr(None, None))

    @classmethod
    def from_name(cls, name):
        return cls.named[name] or cls(name, nad.NetAddr("127.0.0.1", 57110)) # BUG: en sclang, no tiene sentido llamar a ServerOptions.new, init provee una instancia por defecto

    @classmethod
    def remote(cls, name, addr, options, client_id):
        result = cls(name, addr, options, client_id)
        result.start_alive_thread()
        return result

    def __init__(self, name, addr, options=None, client_id=None):
        # // set name to get readable posts from client_id set
        self._name = name # no usa @property setter
        self.addr = addr # @property setter
        self.options = options or ServerOptions()
        # // make statusWatcher before clientID, so .serverRunning works
        self.status_watcher = xxx.ServerStatusWatcher(server=self)
        # // go thru setter to test validity
        self.client_id = client_id or 0 # es @property y usa el setter

        self.volume = xxx.Volume(server=self, persist=True) # BUG: falta implementar
        self.recorder = xxx.Recorder(server=self) # BUG: falta implementar
        self.recorder.notify_server = True # BUG: falta implementar

        self.name = name # ahora si usa @property setter
        self.__class__.all.add(self)

        self._pid_release_condition = # BUG: implementar Condition({ this.pid == nil });
        self.__class__ # .changed(\serverAdded, self) # BUG: usar mdl.NotificationCenter

        self._max_num_clients = None # // maxLogins as sent from booted scsynth # la setea en _handle_client_login_info_from_server
        self.tree = None # lambda *args: None # ver dónde se inicializa, se usa en init_tree

        self.node_allocator = None # se inicializa en new_node_allocators
        self.control_bus_allocator = None # se inicializa en new_bus_allocators
        self.audio_bus_allocator = None # se inicializa en new_bus_allocators
        self.buffer_allocator = None # se inicializa en new_buffer_allocators
        self.scope_buffer_allocator = None # se inicializa en new_scope_buffer_allocators

        # TODO: faltan variables de instancia, siempre revisar que no esté usando
        # las de clase porque no va a funcionar con metaclass sin llamar a __class__.

    @property
    def max_num_clients(self):
        return self._max_num_clients or self.options.max_logins

    def remove(self):
        self.__class__.all.remove(self)
        del self.__class__.named[self.name]

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
        if value in self.named:
            msg = "Server name '{}' already exists. Please use a unique name"
            _warnings.warn(msg.format(value)) # BUG: en sclang, pasa dos parámetros a format # TODO: por qué no es una excepción?
        else:
            self.named[value] = self

    # TODO: este método tal vez debería ir abajo de donde se llame por primera vez
    def init_tree(self):
        def init_task():
            self.send_default_groups()
            self.tree(self) # tree es una propiedad de instancia que contiene una función
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
        if self.server_running:
            _warnings.warn(msg.format(self.name, value,
                                      'server is running', self.client_id))
            return # BUG: los setters de la propiedades retornan el valor? qué pasa cuando falla un setter?
        if not isinstance(value, int):
            _warnings.warn(msg.format(self.name, value
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
        mdl.NotificationCenter.notify(self, 'newAllocators')

    def new_node_allocators(self):
        self.node_allocator = self.__class__.node_alloc_class(
            self.client_id,
            self.options.initial_node_id,
            self.max_num_clients
        )
        # // defaultGroup and defaultGroups depend on allocator,
        # // so always make them here:
        self.make_default_groups()

    def new_bus_allocators(self):
        audio_bus_io_offset = self.options.first_private_bus
        num_ctrl_per_client = (self.options.num_control_bus_channels
                               // self.max_num_clients)
        num_audio_per_client = (self.options.num_audio_bus_channels
                                - audio_bus_io_offset) // self.max_num_clients
        ctrl_reserved_offset = self.options.reserved_num_control_bus_channels
        ctrl_bus_client_offset = num_ctrl_per_client * self.client_id
        audio_reserved_offset = self.options.reserved_num_audio_bus_channels
        audio_bus_client_offset = num_audio_per_client * self.client_id

        self.control_bus_allocator = self.__class__.bus_alloc_class(
            num_ctrl_per_client,
            ctrl_reserved_offset,
            ctrl_bus_client_offset
        )
        self.audio_bus_allocator = self.__class__.bus_alloc_class(
            num_audio_per_client,
            audio_reserved_offset,
            audio_bus_client_offset + audio_bus_io_offset
        )

    def new_buffer_allocators(self):
        num_buffers_per_client = self.options.num_buffers // self.max_num_clients
        num_reserved_buffers = self.options.reserved_num_buffers
        buffer_client_offset = num_buffers_per_client * self.client_id

        self.buffer_allocator = self.__class__.buffer_alloc_class(
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
            print(log_msg.format(self.name, msg[3])) # BUG: es log
            self.status_watcher._handle_login_when_already_registered(msg[3]) # BUG: falta implmementar, cuidado con el nombre
        elif 'not registered' in fail_string:
            # // unregister when already not registered:
            log_msg = "{} - not registered"
            print(log_msg.format(self.name)) # BUG: ídem
            self.status_watcher.notified = False # BUG: falta implementar
        elif 'too many users' in fail_string:
            log_msg = "{} - could not register, too many users"
            print(log_msg.format(self.name)) # BUG: ídem
            self.status_watcher.notified = False # BUG: falta implementar
        else:
            # // throw error if unknown failure
            e_msg = "Failed to register with server '{}' for notifications: {}\n"
            e_msg += "To recover, please reboot the server"
            raise Exception(e_msg.format(self.name, msg)) # BUG: el formato de msg y la nueva línea de e_msg

    # L571
    # /* network messages */

    def send_msg(self, *args):
        self.addr.send_msg(*args)

    def send_bundle(self, time, *args):
        self.addr.send_bundle(time, *args)

    # def send_raw(self, raw_bytes): # send a raw message without timestamp to the addr.
    #    self.addr.send_raw(raw_bytes)

    def send_msg_sync(self, condition, *args): # este método no se usa en la libreríá de clases
        condition = condition or _threading.Condition()
        cmd_name = str(args[0]) # BUG: TODO: el método reorder de abajo envía con send_msg y el número de mensaje como int, VER que hace sclang a bajo nivel, pero puede que esta conversión esté puesta para convertir símbolos a strings en sclang?
        if cmd_name[0] != '/':
            cmd_name = '/' + cmd_name # BUG: ver reorder abajo, ver por qué agrega la barra acá y no en otras partes.
            #args = list(args); args[0] = cmd_name # BUG: esto no está en sclang, supongo que se encarga luego no sé liblo depende de ella.
        # BUG: usa OSCFunc, pero es toda una parafernalia que tengo que ponerme a ver
        # cambiar por OSCFunc luego en todo caso.
        def responder(*msg):
            if msg[1] == cmd_name:
                clt.Client.default._osc_server_thread.del_method('/done', None) # BUG: no se cómo funciona liblo, None acepta mensajes /done con cualquier typespec, borra todos los responder? qué pasa si hay dos iguales?
                with condition:
                    condition.notify()
        clt.Client.default._osc_server_thread.add_method('/done', None, responder) # BUG: no se cómo funciona liblo, None hacepta mensajes /done con cualquier typespec, borra todos los responder? qué pasa si hay dos iguales?
        self.addr.send_bundle(0, *args)
        with condition:
            condition.wait()

    def sync(self, condition, bundles, latency): # BUG: dice bundles, tengo que ver el nivel de anidamiento
        self.addr.sync(condition, bundles, latency)

    def sched_sync(self, func): # este método no se usa en la libreríá de clases
        raise Exception('implementar Server sched_sync con @routine') # BUG

    # def list_send_msg(self, msg): # TODO: creo que es un método de conveniencia que genera confusión sobre la interfaz, acá msg es una lista no más.
    #     pass
    # def list_send_bundle(self, time, msgs):# TODO: creo que es un método de conveniencia que genera confusión sobre la interfaz, acá msgs es una lista no más.
    #     pass

    def reorder(self, node_list, target, add_action='addToHead'): # BUG: ver los comandos en notación camello, creo que el servidor los usa así, no se puede cambiar.
        raise Exception('implementar Server reorder con asTarget, ver el 62') # BUG

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

    # L659
    # /* network message bundling */
    # TODO

    # L698
    # /* scheduling */
    # TODO

    # L814
    # /* recording formats */
    # TODO

    # L825
    # /* server status */
    # TODO

    # L835
    # hasBooted { ^statusWatcher.hasBooted }
    def has_booted(self):
        #return True # BUG! falta implementar StatusWatcher
        pass
    # ...
    # L868 REDO
    def boot(self):
        # localserver
        #self.sproc = _ServerProcesses(self.options)
        #self.sproc.run()
        pass
    # ...
    # L1017 REDO
    def quit(self):
        # check running
        # self.addr.send_msg('/quit')
        # self.sproc.finish()
        pass
    # ...
    # L1110
    @classmethod
    def all_booted_servers(cls):
        return [x for x in cls.all if x.has_booted()]

    # L1118
    # /* volume control */
    # TODO

    # L1132
    # /* recording output */
    # TODO

    # L1140
    # /* internal server commands */
    # TODO

    # L1169
    # /* CmdPeriod support for Server-scope and Server-record and Server-volume */
    # TODO


class _ServerProcesses(object):
    def __init__(self, options):
        self.options = options
        self.proc = None
        self.timeout = 0.1

    def run(self):
        self.proc = _subprocess.Popen(
            self.options.cmd(),
            stdout=_subprocess.PIPE,
            stderr=_subprocess.PIPE,
            bufsize=1,
            universal_newlines=True) # or with asyncio.Subprocesses? :-/
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
        def read(out, prefix, flag):
            while not flag.is_set():
                line = out.readline()
                if line:
                    print(prefix, line, end='')
            print('*** {} redirect fin ***'.format(prefix)) # debug

        def make_thread(out, prefix, flag):
            thr = _threading.Thread(target=read, args=(out, prefix, flag))
            thr.daemon = True
            thr.start()
            return thr

        self._tflag = _threading.Event()
        self._tout = make_thread(self.proc.stdout, 'SCOUT:', self._tflag)
        self._terr = make_thread(self.proc.stdout, 'SCERR:', self._tflag)
