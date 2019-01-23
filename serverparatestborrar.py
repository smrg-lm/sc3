"""
Se encarga de:
    * iniciar y terminar scsynth/supernova
    * iniciar shm
    * monitorear el estatus?
    * quién envía los msj osc?
    * ...
"""

import subprocess as _subprocess
import threading as _threading
import atexit as _atexit
import warnings as _warnings

import liblo as _lo

import supercollie.utils as ut
import supercollie.netaddr as na
import supercollie.client as cl


class ServerOptions(object):
    def __init__(self):
        self.program = 'scsynth' # test
        self.cmd_options = [
            '-u', '57110', '-a', '1024',
            '-i', '2', '-o', '2', '-b', '1026',
            '-R', '0', '-C', '0', '-l', '1'] # test

    def cmd(self):
        return [self.program] + self.cmd_options

    # TODO: todo...


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
