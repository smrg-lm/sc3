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


__all__ = ['main']


class TimeException(ValueError):
    pass


### Kernel.sc ###


class Process(type):
    RT = 0
    NRT = 1

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
        cls._main_lock = threading.RLock()
        cls._switch_cond = threading.Condition(cls._main_lock)
        cls._mode = None
        cls._rgen = random.Random()
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

    def _init_rt(cls):
        # In sclang these two are the same clock, it obtains time_since_epoch
        # as gHostStartNanos = duration_cast<nanoseconds>
        # (hrTimeOfInitialization.time_since_epoch()).count().
        # I think is not important for these reference points to be sampled at
        # the same time because main.elapsed_time() == 0 is in logic relation
        # to main._rt_time_of_initialization. Comment to be removed later if
        # true.
        cls._rt_time_of_initialization = time.time()  # time_since_epoch
        cls._rt_perf_counter_time_of_initialization = time.perf_counter()  # monotonic clock.
        cls._create_main_thread('rt')
        cls._osc_interface = osci.OscUdpInterface()
        cls._osc_interface.start()

    def _init_nrt(cls):
        cls._nrt_time_of_initialization = 0.0
        cls._create_main_thread('nrt')
        cls._clock_scheduler = clk.ClockScheduler()

    def _create_main_thread(cls, prefix):
        # PyrInterpreter3 L157 newPyrProcess y PyrPrimitive initPyrThread.
        main_tt = stm.TimeThread.__new__(stm.TimeThread)
        main_tt.parent = None
        main_tt.func = None
        main_tt.state = stm.TimeThread.State.Init
        main_tt._thread_player = None
        main_tt._beats = 0.0  # Only for main_tt.
        main_tt._seconds = 0.0
        main_tt._rgen = cls._rgen

        main_vname = '_' + prefix + '_main_tt'
        curr_vname = '_' + prefix + '_current_tt'
        setattr(cls, main_vname, main_tt)
        setattr(cls, curr_vname, getattr(cls, main_vname))

    def rt(cls):
        '''Sets the library in rt mode.'''
        if not hasattr(cls, '_rt_time_of_initialization'):
            cls._init_rt()
        with cls._switch_cond:
            cls._time_of_initialization = cls._rt_time_of_initialization
            cls.main_tt = cls._rt_main_tt
            cls.current_tt = cls.main_tt
            setattr(cls, 'elapsed_time', cls._rt_elapsed_time)
            setattr(cls, 'update_logical_time', cls._rt_update_logical_time)
            cls._mode = cls.RT

    def nrt(cls):
        '''Sets the library in nrt mode.'''
        # *** BUG: nrt no va a funcionar con las clases que llaman a
        # *** BUG: SystemClock directamente, por ejemplo Event.
        if not hasattr(cls, '_nrt_time_of_initialization'):
            cls._init_nrt()
        with cls._switch_cond:
            cls._time_of_initialization = cls._nrt_time_of_initialization
            cls.main_tt = cls._nrt_main_tt
            cls.current_tt = cls.main_tt  # *** BUG: see no reset case.
            setattr(cls, 'elapsed_time', cls._nrt_elapsed_time)
            setattr(cls, 'update_logical_time', cls._nrt_update_logical_time)
            cls._mode = cls.NRT

    @property
    def mode(cls):
        return cls._mode

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

    def _rt_elapsed_time(cls) -> float:
        '''Physical time since library initialization.'''
        # *elapsedTime _ElapsedTime
        # Returns the more accurate clock time minus _time_of_initialization.
        return time.perf_counter() - cls._rt_perf_counter_time_of_initialization

    def _nrt_elapsed_time(cls) -> float:
        '''Physical time is main_Thread.seconds in nrt.'''
        return float(cls.main_tt.seconds)

    def monotonic_clock_time(cls) -> float:
        # # *monotonicClockTime _monotonicClockTime
        # monotonic_clock::now().time_since_epoch(), don't know where
        # is used, on linux is hdclock es time.perf_counter().
        return time.monotonic()

    def _rt_update_logical_time(cls, seconds=None):
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
                "logical time can't be set in the future of physical time")
        else:
            cls.main_tt.seconds = seconds

    def _nrt_update_logical_time(cls, seconds=None):
        if seconds is None:
            return
        else:
            cls.main_tt.seconds = seconds


### Main.sc ###


class main(metaclass=Process):
    pass


### After import's compile-time initialization ###


main.rt()
utl.ClassLibrary.init()
