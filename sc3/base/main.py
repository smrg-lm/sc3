"""Kernel.sc & Main.sc"""

import enum
import threading
import atexit
import time
import random
import sys

from ..seq import _taskq as tsq
from ..seq import stream as stm
from ..seq import clock as clk
from . import platform as plf
from . import _oscinterface as osci
from . import utils as utl


__all__ = ['main', 'RtMain', 'NrtMain']


main = None
'''Default main class global variable set by sc3.init().'''


class TimeException(ValueError):
    pass


### Kernel.sc ###


class Process(type):
    class _atexitprio(enum.IntEnum):
        ''' Library predefined _atexitq priority numbers.'''
        USER = 0
        SERVERS = 500
        PLATFORM = 700
        CLOCKS = 800
        NETWORKING = 900

    _atexitq = tsq.TaskQueue()
    '''Functions registered in atexit with order by priority numbers.'''

    def __init__(cls, name, bases, dict):
        # Main library lock.
        cls._main_lock = threading.RLock()

        # Mode switch lock.
        cls._switch_cond = threading.Condition(cls._main_lock)

        # Main TimeThread random generator.
        cls._rgen = random.Random()

        # SynthDef graph build's global state.
        cls._current_synthdef = None
        cls._def_build_lock = threading.Lock()

        cls._init_platform()
        atexit.register(cls.shutdown)

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

    def _create_main_thread(cls):
        # PyrInterpreter3 L157 newPyrProcess y PyrPrimitive initPyrThread.
        cls.main_tt = stm.TimeThread.__new__(stm.TimeThread)
        cls.main_tt.parent = None
        cls.main_tt.func = None
        cls.main_tt.state = stm.TimeThread.State.Init
        cls.main_tt._thread_player = None
        cls.main_tt._beats = 0.0  # Only for main_tt.
        cls.main_tt._seconds = 0.0
        cls.main_tt._rgen = cls._rgen

    @property
    def rgen(cls):
        return cls.current_tt.rgen

    @property
    def platform(cls):
        return cls._platform

    def startup(cls):
        ...

    def run(cls):
        ...

    def stop(cls):
        ...

    def shutdown(cls):
        while not cls._atexitq.empty():
            cls._atexitq.pop()[1]()
        atexit.unregister(cls.shutdown)

    def add_osc_recv_func(cls, func):
        cls._osc_interface.add_recv_func(func)

    def remove_osc_recv_func(cls, func):
        cls._osc_interface.remove_recv_func(func)

    def elapsed_time(cls):
        pass

    def update_logical_time(cls, seconds=None):
        pass


### Main.sc ###


class RtMain(metaclass=Process):
    @classmethod
    def _init(cls):
        # In sclang these two are the same clock, it obtains time_since_epoch
        # as gHostStartNanos = duration_cast<nanoseconds>
        # (hrTimeOfInitialization.time_since_epoch()).count().
        # I think is not important for these reference points to be sampled at
        # the same time because main.elapsed_time() == 0 is in logic relation
        # to main._time_of_initialization. Comment to be removed later if
        # true.
        cls._time_of_initialization = time.time()  # time_since_epoch
        cls._perf_counter_time_of_initialization = time.perf_counter()  # monotonic clock.
        cls._create_main_thread()
        cls._osc_interface = osci.OscUdpInterface()
        cls._osc_interface.start()

        with cls._switch_cond:  # ******************************* BORRAR/CAMBIAR
            cls.current_tt = cls.main_tt

    @classmethod
    def elapsed_time(cls):
        '''Physical time since library initialization.'''
        # *elapsedTime _ElapsedTime
        # Returns the more accurate clock time minus _time_of_initialization.
        return time.perf_counter() - cls._perf_counter_time_of_initialization

    @classmethod
    def update_logical_time(cls, seconds=None):
        # // When code is run from the code editor, the command line, or in
        # // response to OSC and MIDI messages, the main Thread's logical time
        # // is set to the current physical time (see Process: *elapsedTime).
        # // When code scheduled on a Clock is run, the main Thread's logical
        # // time is set to the time the code was scheduled for. Child Threads
        # // inherit logical time from their parents - whenever a Thread
        # // (Routine) is started or resumed, its logical time is set to that
        # // of the parent Thread.
        # This is an internal library interface function meant to be general,
        # although could be less efficient for clocks.
        now = cls.elapsed_time()
        if seconds is None:
            # This case is the update when queried from main_tt, clocks check
            # if the call satisfies the condition current_tt is cls.main_tt
            # and *logical time* is set to *physical time*.
            cls.main_tt.seconds = now
        elif seconds > now:
            raise TimeException(
                "logical time can't be set to the future of physical time")
        else:
            cls.main_tt.seconds = seconds


class NrtMain(metaclass=Process):
    @classmethod
    def _init(cls):
        cls._time_of_initialization = 0.0
        cls._create_main_thread()
        cls._clock_scheduler = clk.ClockScheduler()
        cls._osc_interface = osci.OscNrtInterface()
        cls._osc_interface.init()

        with cls._switch_cond:  # ******************************* BORRAR/CAMBIAR
            cls.current_tt = cls.main_tt  # *** BUG: see no reset case.

    @classmethod
    def elapsed_time(cls):
        '''Physical time is main_Thread.seconds in nrt.'''
        return float(cls.main_tt.seconds)

    @classmethod
    def update_logical_time(cls, seconds=None):
        if seconds is None:
            return
        else:
            cls.main_tt.seconds = seconds
