"""Server.sc"""

import subprocess as _subprocess
import threading as _threading
import atexit as _atexit
import warnings as _warnings
import os

import liblo as _lo

import supercollie.utils as ut
import supercollie.netaddr as na
import supercollie.client as cl


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
        self.num_buffers = 1026; # getter setter, es 1026 a propósito

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
        o.append(self.num_private_audio_bus_channels\
                 + self.num_input_bus_channels\
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
            plist = ut.as_list(self.ugen_plugins_path)
            plist = [os.path.normpath(x) for x in plist] # BUG: ensure platform format? # BUG: windows drive?
            o.append(os.pathsep.join(plist))
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


@ut.initclass
class Server(object):
    # TODO: falta, está solo lo necesario para probar SynthDef.
    named = dict()
    all = set()

    def __init_class__(cls):
        cls.default = cls('localhost', na.NetAddr('127.0.0.1', 57110))

    def __init__(self, name, addr, options=None, clientID=None):
        self.name = name # @property setter
        self.addr = addr # @property setter, TODO
        self.options = options or ServerOptions()
        # TODO...
        self.all.add(self)
        # TODO...

    # L349
    # maxNumClients

    def remove(self):
        self.all.remove(self)
        del self.named[self.name]

    # L357
    @property
    def addr(self):
        return self._addr
    @addr.setter
    def addr(self, value):
        self._addr = value or na.NetAddr("127.0.0.1", 57110) # TODO: podría hacer que se pueda pasar también una tupla como en liblo
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
            msg = "Server name already exists: '{}'. Please use a unique name"
            _warnings.warn(msg.format(value)) # BUG: en sclang, pasa dos parámetros a format # TODO: por qué no es una excepción?
        else:
            self.named[value] = self

    def boot(self):
        # localserver
        self.sproc = _ServerProcesses(self.options)
        self.sproc.run()

    def quit(self):
        # check running
        self.addr.send_msg('/quit')
        self.sproc.finish()

    def send_msg(self, *args):
        self.addr.send_msg(*args)

    def send_bundle(self, time, *args):
        self.addr.send_bundle(time, *args)

    # L835
    # hasBooted { ^statusWatcher.hasBooted }
    def has_booted(self):
        return True # BUG! falta implementar StatusWatcher

    # L1110
    @classmethod
    def all_booted_servers(cls):
        return [x for x in cls.all if x.has_booted()]


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
