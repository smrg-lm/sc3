"""Server.sc"""

import subprocess as _subprocess
import threading as _threading
import atexit as _atexit
import warnings as _warnings

import liblo as _lo

import supercollie.utils as ut
import supercollie.netaddr as na
import supercollie.client as cl


class ServerOptions(object):
    # TEST BORRAR
    # def cmd(self):
    #     return [self.program] + self.cmd_options

    def __init__(self):
        # TEST BORRAR
        # self.program = 'scsynth' # test
        # self.cmd_options = [
        #     '-u', '57110', '-a', '1024',
        #     '-i', '2', '-o', '2', '-b', '1026',
        #     '-R', '0', '-C', '0', '-l', '1'] # test

        self.num_audio_bus_channels = 1024 # solo getter # TODO: tiene setter especial
        self.num_control_bus_channels = 16384 # getter/setter
        self.num_input_bus_channels = 2 # solo getter # TODO: tiene setter especial
        self.num_output_bus_channels = 2 # solo getter # TODO: tiene setter especial
        self.num_buffers = 1026; # getter setter

        self.max_nodes = 1024 # Todos los métodos siguientes tiene getter y setter salvo indicación contraria
        self.max_synth_defs = 1024
        self.protocol = 'UDP'
        self.block_size = 64
        self.hardware_buffer_size = None

        self.mem_size = 8192
        self.num_rgens = 64
        self.num_wire_bufs = 64

        self.sample_rate = None
        self.load_defs = True

        self.input_streams_enabled = # None/False # no inicializada por defecto
        self.output_streams_enabled = # None/False # no inicializada por defecto

        self.in_device = None
        self.out_device = None

        self.verbosity = 0
        self.zeroconf = False # // Whether server publishes port to Bonjour, etc.

        self.restricted_path = None
        self.ugen_plugins_path = None

        self.initial_node_id = 1000
        self.remote_control_volume = False

        self.memory_locking = False
        self.threads = None # // for supernova
        self.use_system_clock = False # // for supernova

        self.num_private_audio_bus_channels = 1020 # solo getter # TODO: tiene setter especial

        self.reserved_num_audio_bus_channels = 0
        self.reserved_num_control_bus_channels = 0
        self.reserved_num_buffers = 0
        self.pings_before_considered_dead = 5

        self.max_logins = 1

        self.rec_header_format = 'aiff'
        self.rec_sample_format = 'float'
        self.rec_channels = 2
        self.rec_buf_size = None

        # @property
        self._device = None # BUG: ver el valor por defecto.

    @property
    def device(self): pass
    @device.setter
    def device(self, value): pass
    # TODO: esta propiedad también tiene un método de clase lo mismo que inDevices and outDevices

    def as_options_string(self, port=57110): pass

    def first_private_bus(self): pass
    def boot_in_process(self): pass
    # numPrivateAudioBusChannels_ { |numChannels = 112|
    # numAudioBusChannels_ { |numChannels=1024|
    # numInputBusChannels_ { |numChannels=8|
    # numOutputBusChannels_ { |numChannels=8|

    def recalc_channels(self): pass

    # *prListDevices { # TODO: llama a primitiva
    # *devices { # llama a *prListDevices
    # *inDevices { # llama a *prListDevices
    # *outDevices { # llama a *prListDevices


class ServerShmInterface():
    def __init__(self, port):
        self.ptr = None # BUG variable de bajo nivel, depende de la implementación.
        self.finalizer = None # BUG variable de bajo nivel, depende de la implementación.
        self.connect(port) # BUG: llama a una primitiva y debe guardar port a bajo nivel

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
