"""Kernel.sc & Main.sc"""

import enum
import threading
import atexit
import pathlib
import time
import random
import sys
import socket

import sc3
from . import _taskq as tsq
from . import platform as plf
from . import systemactions as sac
from . import stream as stm
from . import _oscinterface as osci
from . import _midiinterface as mii
from . import classlibrary as clb
from . import clock as clk
from . import builtins as bi
from . import responders as rpd


__all__ = ['main', 'RtMain', 'NrtMain']


main = None
'''Default main class global variable set by sc3.init().'''


### Kernel.sc ###


class Process(type):
    RT_MODE = 0
    NRT_MODE = 1

    class _atexitprio(enum.IntEnum):
        ''' Library predefined _atexitq priority numbers.'''
        CUSTOM = 0
        SERVERS = 500
        PLATFORM = 700
        CLOCKS = 800
        NETWORKING = 900
        MIDI = 1000

    _atexitq = tsq.TaskQueue()
    '''Functions registered in atexit with order by priority numbers.'''

    def __init__(cls, *_):
        # Main library lock (guards clock's threads).
        cls._main_lock = threading.RLock()

        # Main TimeThread random generator.
        cls._m_rgen = random.Random()

        # SynthDef graph build's global state.
        cls._current_synthdef = None
        cls._def_build_lock = threading.Lock()

        cls._init_platform()
        atexit.register(cls._shutdown)

    def _init_platform(cls):
        if sys.platform.startswith('linux'):
            cls._platform = plf.LinuxPlatform()
        elif sys.platform.startswith('darwin'):
            cls._platform = plf.DarwinPlatform()
        elif sys.platform.startswith('win32'):
            cls._platform = plf.Win32Platform()
        elif sys.platform.startswith('cygwin'):
            cls._platform = plf.CygwinPlatform()
        else:
            raise RuntimeError('platform not defined')
        cls._platform._startup()
        cls._atexitq.add(cls._atexitprio.PLATFORM, cls.platform._shutdown)

    def _startup(cls):
        raise NotImplementedError

    def _exec_startup_file(cls):
        # NOTE: This may change to a special kind
        # of file that only allows to set up certain
        # parameters like platform or server options.
        if sc3.LIB_SETUP_FILE:
            path = pathlib.Path(sc3.LIB_SETUP_FILE)
        else:
            path = plf.Platform.config_dir / 'startup.py'
        try:
            with open(path, 'r') as file:
                ast = compile(file.read(), path, 'exec')
                exec(ast, dict(), dict())
        except FileNotFoundError:
            pass

    def _shutdown(cls):
        sac.ShutDown.run()
        while not cls._atexitq.empty():
            with cls._main_lock:
                cls._atexitq.pop()[1]()
        atexit.unregister(cls._shutdown)

    @property
    def _rgen(cls):
        return cls.current_tt._rgen

    @property
    def platform(cls):
        return cls._platform

    def open_udp_port(cls, port):
        '''Open extra UDP port.'''
        with cls._main_lock:
            local_addr = (socket.gethostbyname('localhost'), port)
            if local_addr in osci.OscInterface._local_endpoints:
                return
            interface = osci.OscUdpInterface(port)
            interface.start()

    def close_udp_port(cls, port):
        '''Close extra UDP port. Default library port can't be closed.'''
        with cls._main_lock:
            local_addr = (socket.gethostbyname('localhost'), port)
            if cls._osc_interface.port == port\
            or local_addr not in osci.OscInterface._local_endpoints:
                return
            interface = osci.OscInterface._local_endpoints[local_addr]
            interface.stop()

    def add_osc_recv_func(cls, func):
        type(cls._osc_interface).add_recv_func(func)

    def remove_osc_recv_func(cls, func):
        type(cls._osc_interface).remove_recv_func(func)

    def elapsed_time(cls):
        pass

    def _update_logical_time(cls, seconds):
        pass


### Main.sc ###


class RtMain(metaclass=Process):
    @classmethod
    def _init(cls):
        # time.monotonic() will not work, it can stop if the system is
        # suspended and will need to resync _elapsed_osc_offset which, if done
        # periodically, generates jitter/jumps in logical time. Also, it can't
        # avoid the glitches produced by the system's ntp synchronization
        # because that affects the wake up time of the threads at system level.
        cls._init_time = time.time()  # time_since_epoch
        cls.main_tt = stm._MainTimeThread()
        cls.current_tt = cls.main_tt

        cls._osc_interface = osci.OscUdpInterface(
            sc3.LIB_PORT, sc3.LIB_PORT_RANGE)
        cls._osc_interface.start()

        cls._midi_interface = mii.MidiRtInterface()
        cls._midi_interface.start()

        # State to mimic time behaviour for all awakables in rt.
        cls._in_awake_call = False

        cls._wait_cond = threading.Condition(cls._main_lock)
        cls._wait_count = 0

        clb.ClassLibrary.init()
        cls._startup()

    @classmethod
    def _startup(cls):
        import sc3.synth.systemdefs as sds
        sds.SystemDefs.add_all()
        cls._exec_startup_file()
        sac.StartUp.run()

    @classmethod
    def elapsed_time(cls):
        '''Physical time since library initialization.'''
        return time.time() - cls._init_time

    @classmethod
    def _update_logical_time(cls, seconds):
        # // When code is run from the code editor, the command line, or in
        # // response to OSC and MIDI messages, the main Thread's logical time
        # // is set to the current physical time (see Process: *elapsedTime).
        # // When code scheduled on a Clock is run, the main Thread's logical
        # // time is set to the time the code was scheduled for. Child Threads
        # // inherit logical time from their parents - whenever a Thread
        # // (Routine) is started or resumed, its logical time is set to that
        # // of the parent Thread.
        # Text above doesn't hold all true here, updates are done by clocks
        # when data is schedule but can't capture code before excecution.
        # _MainTimeThread updates logical time when calling seconds property
        # and OSC updates logical time by scheduling its task in SystemClock.
        with cls._main_lock:
            if not cls._in_awake_call:
                cls.main_tt._m_seconds = seconds


    # Main thread blocking control for scripts.

    @classmethod
    def _is_main_thread(cls):
        if threading.main_thread() is threading.current_thread():
            return True
        else:
            return False

    @classmethod
    def wait(cls, timeout=None, tasks=1, tailtime=0):
        '''Main thread lock until timeout or notified by ``resume``.

        This method doesn't have to acquire a lock before calling.
        Internally it uses a counter to follow the calls to `main.resume()`
        which may happen even before this method is called and will resume
        when the count is less or equal to zero or after timeout (if present).
        The internal counter is reset after this method resumes.

        Note: This is an utility method that makes less verbose the code for
        some simple actions that need to wait for routines to finish.

        Parameters
        ----------
        timeout: float
            Optional wait time for the lock in seconds.
        tasks: int
            Number of tasks that have to call `main.resume()` to unlock the
            main thread.
        tailtime: float
            Optional sleep time in seconds added after ``resume`` is called,
            tailtime time is ignored if the the given timeout expired.
        Returns
        -------
        bool
            The value is False if `timeout` expired otherwise is True.
        '''

        if not cls._is_main_thread():
            raise Exception('main.wait() must be called from the main thread')
        not_expired = True  # It may not even enter the while loops.
        with cls._wait_cond:
            try:
                cls._wait_count += tasks
                if timeout is None:
                    while cls._wait_count > 0:
                        cls._wait_cond.wait()
                else:
                    prev_time = curr_time = time_diff = None
                    while cls._wait_count > 0:
                        prev_time = time.time()
                        not_expired = cls._wait_cond.wait(timeout)
                        curr_time = time.time()
                        if not_expired and cls._wait_count > 0:
                            time_diff = curr_time - prev_time
                            prev_time = curr_time
                            timeout -= time_diff
                        else:
                            break
            except KeyboardInterrupt:
                pass
            finally:
                cls._wait_count = 0
        if not_expired and tailtime > 0:
            time.sleep(tailtime)
        return not_expired

    @classmethod
    def resume(cls):
        '''Unlock the main thread.

        This method must be called from another thread, e.g. from a routine
        scheduled by a clock using `play`.
        '''

        if cls._is_main_thread():
            raise Exception(
                'main.resume() cannot be called from the main thread')
        with cls._wait_cond:
            cls._wait_count -= 1
            cls._wait_cond.notify()

    @classmethod
    def sync(cls, server, timeout=None):
        '''Main thread blocking sync command.

        Parameters
        ----------
        server: Server
            Instance to wait for.
        timeout: float
            Optional wait time for the lock in seconds.
        Returns
        -------
        bool
            The value is False if ``timeout`` expired otherwise is True.
        '''

        if not cls._is_main_thread():
            raise Exception('main.sync() must be called from the main thread')

        id = bi.uid()

        def resp_func(msg, *_):
            if msg[1] == id:
                resp.free()
                with cls._wait_cond:
                    cls._wait_cond.notify()

        resp = rpd.OscFunc(resp_func, '/synced', server.addr)

        with cls._wait_cond:
            server.addr.send_msg('/sync', id)
            try:
                return cls._wait_cond.wait(timeout)
            except KeyboardInterrupt:
                resp.free()


class NrtMain(metaclass=Process):
    @classmethod
    def _init(cls):
        cls._init_time = 0.0
        cls.main_tt = stm._MainTimeThread()
        cls.main_tt._m_seconds = 0.0
        cls.current_tt = cls.main_tt
        cls._clock_scheduler = clk.ClockScheduler()
        cls._osc_interface = osci.OscNrtInterface()
        cls._osc_interface.init()
        cls._midi_interface = mii.MidiNrtInterface()
        cls._midi_interface.init()

        clb.ClassLibrary.init()
        cls._startup()

    @classmethod
    def _startup(cls):
        # Server setup and boot is only for user convenience.
        import sc3.synth.server as srv
        srv.Server.default.latency = 0
        srv.Server.default.options.sample_rate = 48000
        srv.Server.default.boot()  # Sets _status_watcher._has_booted = True
        cls._exec_startup_file()
        sac.StartUp.run()

    @classmethod
    def elapsed_time(cls):
        '''Return main time thread's seconds.'''
        return float(cls.main_tt._seconds)

    @classmethod
    def _update_logical_time(cls, seconds):
        # In nrt physical time and logical time are the same.
        cls.main_tt._m_seconds = seconds

    @classmethod
    def process(cls, tailtime=0, proto='osc'):
        '''Generate and return OSC or MIDI command scores.

        Parameters
        ----------
        tailtime : float
            Wait time after the last event. Used for reverb time or alike.
            Only has effect for OSC scores.
        proto : str
            Score protocol to generate, possible values are `'osc'` or`'midi'`.

        Returns
        -------
        An instance of either OscScore or MidiScore.

        '''

        cls._clock_scheduler.run()
        if proto == 'osc':
            cls._osc_interface._osc_score.finish(tailtime)
            return cls._osc_interface._osc_score
        elif proto == 'midi':
            cls._midi_interface._midi_score.finish()
            return cls._midi_interface._midi_score
        else:
            ValueError(f'invalid protocol name {repr(proto)}')

    @classmethod
    def reset(cls):
        '''Reset sc3 time, scheduler and command scores to initial state.'''

        cls.main_tt._m_seconds = 0.0
        cls._clock_scheduler.reset()
        cls._osc_interface.init()  # Reset OscScore.
        cls._midi_interface.init()  # Reset MidiScore.
