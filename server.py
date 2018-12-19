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
import liblo as _liblo

#import supercollie as _sc


class Server(object):
    def __init__(self, options=None, client=None): # clientID lo paso a Client
        if options is None:
            self.options = ServerOptions()
        else:
            self.options = options

    def boot(self):
        # localserver
        self.sproc = _ServerProcesses(self.options)
        self.sproc.run()

    def quit(self):
        # check running
        target = (self.options.hostname, self.options.port)
        msg = _liblo.Message('/quit')
        _liblo.send(target, msg)
        self.sproc.finish()


class ServerOptions(object):
    def __init__(self):
        self.name = 'localhost'
        self.hostname = '127.0.0.1'
        self.port = 57110
        self.proto = _liblo.UDP
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
        _atexit.register(self._terminate_proc)

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
