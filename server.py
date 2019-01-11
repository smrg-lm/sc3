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

import liblo as _lo
import supercollie.client as cl


class Server(object):
    def __init__(self, options=None, client=None): # clientID lo paso a Client BUG: clietnID es un paramétro que tiene que estar acá también.
        self.options = options or ServerOptions()

    def boot(self):
        # localserver
        self.sproc = _ServerProcesses(self.options)
        self.sproc.run()

    def quit(self):
        # check running
        target = (self.options.hostname, self.options.port)
        cl.Client.default.send_msg(target, '/quit')
        self.sproc.finish()

    def value(self): # cambiar a name o algo similar.
        return 'cambiame el nombre value() en Server' # Es el método value de Object que devuelve self.options.name
    def is_local(self, *args):
        raise NotImplementedError('Implementar Server-is_local()')
    def send_msg(self, *args):
        raise NotImplementedError('Implementar Server-send_msg()')

class ServerOptions(object):
    def __init__(self):
        self.name = 'localhost'
        self.hostname = '127.0.0.1'
        self.port = 57110
        self.proto = _lo.UDP
        self.program = 'scsynth' # test
        self.cmd_options = [
            '-u', '57110', '-a', '1024',
            '-i', '2', '-o', '2', '-b', '1026',
            '-R', '0', '-C', '0', '-l', '1'] # test

    def cmd(self):
        return [self.program] + self.cmd_options


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
