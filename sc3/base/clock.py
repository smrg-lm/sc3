"""Clock.sc"""

import logging
import threading
import weakref

from . import classlibrary as clb
from . import main as _libsc3
from . import builtins as bi
from . import functions as fn
from . import systemactions as sac
from . import model as mdl
from . import _taskq as tsq
from . import stream as stm


__all__ = [
    'SystemClock', 'AppClock', 'Quant', 'TempoClock', 'defer']


_logger = logging.getLogger(__name__)


class ClockError(RuntimeError):
    pass


class ClockNotRunning(ClockError):
    pass


### Clocks for timing threads ###


class MetaClock(type):
    _pure_nrt = False  # Must be set by sub metaclasses in __init__.

    def play(cls, task, quant=None):
        '''Schedule a Routine or Function to be evaluated in this clock.

        If the return value of functions or yield value of routines is int
        or float the task will be rescheduled using that value as delta.
        This method shares semantics with other objects `play` methods that
        use clocks to schedule tasks.

        Parameters
        ----------
        task : Routine | Function
            Task to be scheduled. If the argument is a common function it
            will be wrapped into a Function object to be scheduled.
        quant : Quant
            A Quant object or a any value that can be cast into one with
            Quant.as_quant constructor. This parameter only works for
            TempoClock and is ignored by other clocks.

        '''

        cls.sched(0, task)

    @property
    def mode(cls):
        '''Return the rt/nrt mode flag of the clock.'''
        if cls._pure_nrt:
            return _libsc3.main.NRT_MODE
        elif _libsc3.main is _libsc3.RtMain:
            return _libsc3.main.RT_MODE
        else:
            return _libsc3.main.NRT_MODE

    @property
    def seconds(cls):
        '''Return the logial time of the current time thread.'''
        return _libsc3.main.current_tt._seconds

    # // tempo clock compatibility

    @property
    def beats(cls):
        '''Return the tempo dependent logial time of the current time thread.'''
        return _libsc3.main.current_tt._seconds

    def beats2secs(cls, beats):
        '''Convert beats to seconds of the current time thread.'''
        return beats

    def secs2beats(cls, secs):
        '''Convert seconds to beats of the current time thread.'''
        return secs

    def beats2bars(cls, beats):
        '''Return the number of bars corresponding to the amount of `beats`.'''
        return 0

    def bars2beats(cls, bars):
        '''Return the number of beats corresponding to the amount of `bars`.'''
        return 0

    def time_to_next_beat(cls, quant=1):
        '''Return the duration remaining until the next beat.'''
        return 0

    # def next_time_on_grid(cls, quant=1, phase=0):
    #     '''Return the time of the next beat.'''
    #     if quant == 0:
    #         return cls.beats + phase
    #     if phase < 0:
    #         phase = bi.mod(phase, quant)
    #     return bi.roundup(cls.beats - bi.mod(phase, quant), quant) + phase


class Clock(metaclass=MetaClock):
    pass


class MetaSystemClock(MetaClock):
    def __init__(cls, *_):

        def init_func(cls):
            if _libsc3.main is _libsc3.RtMain:
                cls._task_queue = tsq.TaskQueue()
                cls._sched_cond = threading.Condition(_libsc3.main._main_lock)
                cls._thread = threading.Thread(
                    target=cls._run,
                    name=cls.__name__,
                    daemon=True)
                cls._thread.start()
                cls._sched_init()
                _libsc3.main._atexitq.add(
                    _libsc3.main._atexitprio.CLOCKS, cls._sched_stop)
            else:
                cls._pure_nrt = True
                cls._elapsed_osc_offset = 0.0

        clb.ClassLibrary.add(cls, init_func)


class SystemClock(Clock, metaclass=MetaSystemClock):
    '''
    Clock running on separate accurately timed thread. Singleton class object.

    This is the default clock of the library, it's an accurate scheduler based
    on `physical time` with support for routines' `logical time` but without
    tempo control.

    Note
    ----
    SystemClock and TempoClock should be used only for sequencing musical
    tasks. Any resource intensive task that blocks the execution of the
    clock's thread long enough will cause dispatch timing issues. Thus,
    are not recommended for tasks like GUI updates or similar, for those cases
    use AppClock.

    '''

    _SECONDS_FROM_1900_TO_1970 = 2208988800  # 17 leap years
    _SECONDS_TO_OSC = pow(2, 32) / 1
    _OSC_TO_SECONDS = 1 / pow(2, 32)

    def __new__(cls):
        return cls

    @classmethod
    def _sched_init(cls):
        # _init_time was moved to main because rt/nrt clock switch.
        offset = (_libsc3.main._init_time + cls._SECONDS_FROM_1900_TO_1970)
        cls._elapsed_osc_offset = int(offset * cls._SECONDS_TO_OSC)

    @classmethod
    def elapsed_time_to_osc(cls, elapsed: float) -> int:  # int64
        '''Convert elapsed time in seconds to OSC timetag format.'''
        return int(elapsed * cls._SECONDS_TO_OSC) + cls._elapsed_osc_offset

    @classmethod
    def osc_to_elapsed_time(cls, osctime: int) -> float:
        '''Convert time in OSC timetag format to elapsed time in seconds.'''
        return float(osctime - cls._elapsed_osc_offset) * cls._OSC_TO_SECONDS

    @classmethod
    def osc_time(cls) -> int:
        '''Return elapsed time as OSC timetag.'''
        return cls.elapsed_time_to_osc(_libsc3.main.elapsed_time())

    @classmethod
    def _sched_add(cls, secs, task):
        # Call with acquired lock.
        if cls._task_queue.empty():
            prev_time = -1e10
        else:
            prev_time = cls._task_queue.peek()[0]
        cls._task_queue.add(secs, task)
        if cls._task_queue.peek()[0] != prev_time:
            cls._sched_cond.notify_all()

    @classmethod
    def _sched_stop(cls):
        if not cls._run_sched:
            return
        with cls._sched_cond:
            cls._task_queue.clear()
            cls._run_sched = False
            cls._sched_cond.notify_all()
        cls._thread.join()

    @classmethod
    def _run(cls):
        cls._run_sched = True

        with cls._sched_cond:
            while True:
                # // wait until there is something in scheduler
                while cls._task_queue.empty():
                    cls._sched_cond.wait()
                    if not cls._run_sched:
                        return

                # // wait until an event is ready
                now = 0
                while not cls._task_queue.empty():
                    now = _libsc3.main.elapsed_time()
                    sched_secs = cls._task_queue.peek()[0]
                    if now >= sched_secs:
                        break
                    # cls._sched_cond.wait(sched_point - now)
                    cls._sched_cond.wait(sched_secs - now)
                    if not cls._run_sched:
                        return

                # // perform all events that are ready
                while not cls._task_queue.empty()\
                and now >= cls._task_queue.peek()[0]:
                    item = cls._task_queue.pop()
                    sched_time = item[0]
                    task = item[1]
                    try:
                        _libsc3.main._update_logical_time(sched_time)
                        _libsc3.main._in_awake_call = True
                        delta = task.__awake__(cls)
                        if isinstance(delta, (int, float))\
                        and not isinstance(delta, bool):
                            time = sched_time + delta
                            cls._sched_add(time, task)
                    except stm.StopStream:
                        pass
                    except Exception:
                        # Always recover.
                        _logger.error(
                            '%s(%s) scheduled on SystemClock',
                            type(task).__name__, task.func.__qualname__,
                            exc_info=1)
                    finally:
                        _libsc3.main._in_awake_call = False

    @classmethod
    def clear(cls):
        '''Remove all pending tasks from the scheduler queue.'''
        if cls.mode == _libsc3.main.NRT_MODE:
            return
        with cls._sched_cond:
            while not cls._task_queue.empty():
                cls._task_queue.pop()
            cls._sched_cond.notify_all()

    @classmethod
    def sched(cls, delta, item):
        '''
        Schedule a new task `item` to be evaluated after `delta` seconds
        from current `elapsed time`.

        '''

        if not hasattr(item, '__awake__'):
            item = fn.Function(item)
        item._clock = cls
        if cls.mode == _libsc3.main.NRT_MODE:
            seconds = _libsc3.main.current_tt._seconds
            seconds += delta
            if seconds == float('inf'):
                return
            ClockTask(seconds, cls, item, _libsc3.main._clock_scheduler)
        else:
            with cls._sched_cond:
                seconds = _libsc3.main.current_tt._seconds
                seconds += delta
                if seconds == float('inf'):
                    return
                cls._sched_add(seconds, item)

    @classmethod
    def sched_abs(cls, time, item):
        '''
        Schedule a new task `item` to be evaluated at a `time` point in the
        future relative to `elapsed time`.

        '''

        if not hasattr(item, '__awake__'):
            item = fn.Function(item)
        item._clock = cls
        if time == float('inf'):
            return
        if cls.mode == _libsc3.main.NRT_MODE:
            ClockTask(time, cls, item, _libsc3.main._clock_scheduler)
        else:
            with cls._sched_cond:
                cls._sched_add(time, item)


class Scheduler():
    # This class could work as a nrt scheduler compatible with clocks but
    # their interfaces and behaviours aren't consistent, nrt mode takes care
    # of that. I keep it here to be used by AppClock only but it could also be
    # refactored and embeded within that class.

    def __init__(self, clock, drift=False, recursive=True):
        self._clock = clock
        self._drift = drift
        self.recursive = recursive
        # init
        self._beats = 0.0
        self._seconds = 0.0
        self.queue = tsq.TaskQueue()
        self._expired = []

    def _wakeup(self, item):
        try:
            _libsc3.main._update_logical_time(self._seconds)
            _libsc3.main._in_awake_call = True
            delta = item.__awake__(self._clock)
            if isinstance(delta, (int, float)) and not isinstance(delta, bool):
                self._sched_add(delta, item)
        except stm.StopStream:
            pass
        except Exception:
            _logger.error(
                '%s(%s) scheduled on AppClock',
                type(item).__name__, item.func.__qualname__, exc_info=1)
        finally:
            _libsc3.main._in_awake_call = False

    def play(self, task, quant=None):
        self.sched(0, task)

    def _sched_add(self, delta, item):
        if self._drift:
            from_time = _libsc3.main.elapsed_time()
        else:
            from_time = self.seconds
        self.queue.add(from_time + delta, item)

    def sched(self, delta, item):
        if not hasattr(item, '__awake__'):
            item = fn.Function(item)
        item._clock = self._clock
        if delta is None:
            delta = 0.0
        if delta == float('inf'):
            return
        self._sched_add(delta, item)

    def sched_abs(self, time, item):
        if not hasattr(item, '__awake__'):
            item = fn.Function(item)
        item._clock = self._clock
        if time == float('inf'):
            return
        self.queue.add(time, item)

    def clear(self):
        while not self.queue.empty():
            self.queue.pop()

    def empty(self):
        return self.queue.empty()

    def advance(self, delta):
        self.seconds = self.seconds + delta

    @property
    def seconds(self):
        return self._seconds

    @seconds.setter
    def seconds(self, value):
        if self.queue.empty():
            self._seconds = value
            self._beats = self._clock.secs2beats(value)
            return
        self._seconds = self.queue.peek()[0]
        if self.recursive:
            while self._seconds <= value:
                self._beats = self._clock.secs2beats(self._seconds)
                self._wakeup(self.queue.pop()[1])
                if self.queue.empty():
                    break
                else:
                    self._seconds = self.queue.peek()[0]
        else:
            # // First pop all the expired items and only then wake
            # // them up, in order for control to return to the caller
            # // before any tasks scheduled as a result of this call are
            # // awaken.
            while self._seconds <= value:
                self._expired.append(self.queue.pop())
                if self.queue.empty():
                    break
                else:
                    self._seconds = self.queue.peek()[0]
            for time, item in self._expired:
                self._seconds = time
                self._beats = self._clock.secs2beats(time)
                self._wakeup(item)
            self._expired.clear()
        self._seconds = value
        self._beats = self._clock.secs2beats(value)


class MetaAppClock(MetaClock):
    def __init__(cls, *_):

        def init_func(cls):
            if _libsc3.main is _libsc3.RtMain:
                cls._sched_lock = _libsc3.main._main_lock
                cls._tick_cond = threading.Condition()
                cls._scheduler = Scheduler(cls, drift=True, recursive=False)
                cls._thread = threading.Thread(
                    target=cls._run,
                    name=cls.__name__,
                    daemon=True)
                cls._thread.start()
                _libsc3.main._atexitq.add(
                    _libsc3.main._atexitprio.CLOCKS + 1, cls._stop)
            else:
                cls._pure_nrt = True

        clb.ClassLibrary.add(cls, init_func)


class AppClock(Clock, metaclass=MetaAppClock):
    '''
    Low priority scheduler compatible with SystemClock and TempoClock.
    Singleton class object.

    Note
    ----
    Wait time drifts cumulatively when used for periodic tasks.

    Note
    ----
    This clock is meant to be a low priority scheduling thread, compatible
    with SystemClock and TempoClock, with no support for `logical time`.
    Because Python doesn't supports threading priority it is not actually
    low priority but its still used for deferring non time critical tasks.
    Low level implementation may change in the future.

    '''

    def __new__(cls):
        return cls

    @classmethod
    def _run(cls):
        cls._run_sched = True
        seconds = None
        while cls._run_sched:
            with cls._sched_lock:
                seconds = cls._tick()  # First tick for free, returns None
                if isinstance(seconds, (int, float))\
                and not isinstance(seconds, bool):
                    seconds = seconds - cls._scheduler.seconds  # tick returns abstime (elapsed)
            with cls._tick_cond:  # many notify one wait
                if not cls._run_sched:
                    return
                cls._tick_cond.wait(seconds)  # if seconds is None waits for notify

    @classmethod
    def clear(cls):
        '''Remove all pending tasks from the scheduler queue.'''
        if cls.mode == _libsc3.main.NRT_MODE:
            return
        else:
            with cls._sched_lock:
                cls._scheduler.clear()

    @classmethod
    def sched(cls, delta, item):
        '''
        Schedule a new task `item` to be evaluated after `delta` seconds from
        current `elapsed time`.

        '''

        if cls.mode == _libsc3.main.NRT_MODE:
            if not hasattr(item, '__awake__'):
                item = fn.Function(item)
            item._clock = cls
            if delta == float('inf'):
                return
            ClockTask(delta, cls, item, _libsc3.main._clock_scheduler)
        else:
            with cls._sched_lock:
                cls._scheduler.sched(delta, item)
            with cls._tick_cond:
                cls._tick_cond.notify()

    @classmethod
    def _tick(cls):
        if cls.mode == _libsc3.main.NRT_MODE:
            return None
        cls._scheduler.seconds = _libsc3.main.elapsed_time()
        if cls._scheduler.queue.empty():
            return None  # check value for client::tick to stop calling itself.
        else:
            return cls._scheduler.queue.peek()[0]

    @classmethod
    def _stop(cls):
        if not cls._run_sched:
            return
        with cls._tick_cond:
            cls._run_sched = False
            cls._tick_cond.notify()
        cls._thread.join()


class ClockScheduler():
    def __init__(self):
        self.queue = tsq.TaskQueue()

    def run(self):
        while not self.queue.empty():
            time, clock_task = self.queue.pop()
            clock_task._wakeup(time)

    def add(self, time, clock_task):
        self.queue.add(time, clock_task)

    def reset(self):
        self.queue.clear()


class ClockTask():
    def __init__(self, beats, clock, task, scheduler):
        self.clock = clock
        self.task = task
        self.scheduler = scheduler
        scheduler.add(clock.beats2secs(beats), self)

    def _wakeup(self, time):
        try:
            _libsc3.main._update_logical_time(time)
            beats = self.clock.secs2beats(time)
            delta = self.task.__awake__(self.clock)
            if isinstance(delta, (int, float)) and not isinstance(delta, bool):
                self.scheduler.add(self.clock.beats2secs(beats + delta), self)
        except stm.StopStream:
            pass
        except Exception:
            _logger.error(
                '%s(%s) scheduled on ClockScheduler',
                type(self.task).__name__, self.task.func.__qualname__,
                exc_info=1)


### Quant.sc ###
# // This class is used to encapsulate quantization issues associated
# // with EventStreamPlayer and TempoClock, quant and phase determine the
# // starting time of something scheduled by a TempoClock timingOffset
# // is an additional timing factor that allows an EventStream to compute
# // "ahead of time" enough to allow negative lags for strumming a chord, etc.


class Quant():
    def __init__(self, quant=0, phase=None, timing_offset=None):
        self.quant = quant
        self.phase = phase
        self.timing_offset = timing_offset

    # *default  # NOTE: Not really needed.

    @classmethod
    def as_quant(cls, quant):
        '''Return a Quant object from the value of `quant`.

        The received object can be an int or float representing the `quant`
        paramenter or a collection representing `quant`, `phase` and
        `timing_offset` parameters. If is None an object with default values
        is created.

        This method is used internally to convert the type of valid Quant's
        constructor parameters values.

        '''

        if isinstance(quant, cls):
            pass
        elif isinstance(quant, (int, float)):
            quant = cls(quant)
        elif isinstance(quant, (list, tuple)):
            quant = cls(*quant[:3])
        elif quant is None:
            quant = cls()
        else:
            msg = f'unsuported type conversion to Quant: {type(quant)}'
            raise TypeError(msg)
        return quant

    def next_time_on_grid(self, clock):
        '''Return the time of the next beat for a give `clock` object.'''
        return clock.next_time_on_grid(
            self.quant, (self.phase or 0) - (self.timing_offset or 0))

    def __repr__(self):
        return (
            f'{type(self).__name__}(quant={self.quant}, '
            f'phase={self.phase}, timing_offset={self.timing_offset})')


# /*
# You should only change the tempo 'now'. You can't set the tempo at some beat
# in the future or past, even though you might think so from the methods.
#
# There are several ideas of now:
#     elapsed time, i.e. "real time"
#     logical time in the current time base.
#     logical time in another time base.
#
# Logical time is time that is incremented by exact amounts from the time you
# started. It is not affected by the actual time your task gets scheduled, which
# may shift around somewhat due to system load. By calculating using logical
# time instead of actual time, your process will not drift out of sync over long
# periods. Every thread stores a clock and its current logical time in seconds
# and beats relative to that clock.
#
# Elapsed time is whatever the system clock says it is right now. Elapsed time
# is always advancing. Logical time only advances when your task yields or
# returns.
# */


class MetaTempoClock(MetaClock):
    def __init__(cls, *_):
        cls._all = weakref.WeakSet()

        def init_func(cls):
            # TempoClock.default was removed. Within the library use
            # SystemClock or AppClock, in user code create an instance
            # and use it as default for your script/conding session.
            # Routines set SystemClock as default.
            # cls.default = cls()
            # cls.default.permanent = True
            sac.CmdPeriod.add(cls.__on_cmd_period)

        clb.ClassLibrary.add(cls, init_func)

    @property
    def all(cls):
        return set(cls._all)

    def stop_all(cls):
        for clock in list(cls._all):
            clock.stop()


    ### System Actions ###

    def __on_cmd_period(cls):
        for clock in cls.all:
            clock.clear()
            if not clock.permanent:
                clock.stop()


class TempoClock(Clock, metaclass=MetaTempoClock):
    '''Tempo based scheduler.

    TempoClock is a scheduler like SystemClock, but it schedules
    relative to a tempo in beats per second.

    Parameters
    ----------
    tempo : int | float
        The initial tempo. Defaults to 1.
    beats : int | float
        The time in beats, corresponding to the reference time given
        with the seconds argument. Defaults to 0.
    seconds : int | float
        The reference time in seconds, to which the beats argument
        corresponds. Defaults to the current Thread's `logical time`.

    Notes
    -----
    The TempoClock will be created as if it started counting beats at
    the time given in the seconds argument with the starting amount
    given in the beats argument. The current count of beats will thus
    be equal to that starting amount plus the amount of beats that
    would be counted since the given reference time in seconds,
    according to the given tempo.

    The default arguments create a TempoClock that starts counting
    beats with 0 at the current `logical time`.
    ::

      @routine.run()
      def example(inval):
          _, clock = inval
          print('the example is running in SystemClock:', clock is SystemClock)
          # Starts from zero by default.
          t = TempoClock(1)
          print('current beats:', t.beats)
          # Starts counting beats from 5.
          t = TempoClock(1, 5)
          print('current beats:', t.beats)
          # Counting beats as if it started 5 seconds ago from 0.
          t = TempoClock(1, 0, clock.seconds - 5)
          print('current beats:', t.beats)

      # Use CmdPeriod afterwards to stop all created TempoClocks.
      # CmdPeriod.run()

    If the above example was run without a souronding routine the
    actual `beats` value will not be precise. When running in real
    time, the base time reference is physical time and every call that
    requires current time is relativelly synced to it. The same
    happens in sclang when each instruction is evaluated separatelly,
    the difference is that sclang updates the base time only once per
    intepreter call which is not possible to do in a Python library.

    '''

    def __init__(self, tempo=None, beats=None, seconds=None):
        # prTempoClock_New
        tempo = tempo or 1.0  # tempo=0 is invalid too.
        if tempo < 0.0:
            raise ValueError(f'invalid tempo {tempo}')

        self._tempo = tempo
        self._beat_dur = 1.0 / tempo
        self._base_seconds = seconds or _libsc3.main.current_tt._seconds
        self._base_beats = beats or 0.0
        self._beats = 0.0

        # init
        self._beats_per_bar = 4.0
        self._bars_per_beat = 0.25
        self._base_bar_beat = 0.0
        self._base_bar = 0.0
        self.permanent = False
        type(self)._all.add(self)

        if _libsc3.main is _libsc3.RtMain:
            self._pure_nrt = False
            self._task_queue = tsq.TaskQueue()
            self._sched_cond = threading.Condition(_libsc3.main._main_lock)
            self._thread = threading.Thread(
                target=self._run,
                name=f'{type(self).__name__} id: {id(self)}',
                daemon=True)
            self._thread.start()
            _libsc3.main._atexitq.add(
                _libsc3.main._atexitprio.CLOCKS + 2, self._stop)
        else:
            self._pure_nrt = True

    @property
    def mode(self):
        '''Return the rt/nrt mode flag of the clock.'''
        if self._pure_nrt:
            return _libsc3.main.NRT_MODE
        elif _libsc3.main is _libsc3.RtMain:
            return _libsc3.main.RT_MODE
        else:
            return _libsc3.main.NRT_MODE

    def _run(self):
        self._run_sched = True

        with self._sched_cond:
            while True:
                # // wait until there is something in scheduler
                while self._task_queue.empty():
                    self._sched_cond.wait()
                    if not self._run_sched:
                        return

                # // wait until an event is ready
                elapsed_beats = 0
                while not self._task_queue.empty():
                    elapsed_beats = self.elapsed_beats()
                    qpeek = self._task_queue.peek()
                    if elapsed_beats >= qpeek[0]:
                        break
                    sched_secs = self.beats2secs(qpeek[0])
                    self._sched_cond.wait(
                        sched_secs - _libsc3.main.elapsed_time())
                    if not self._run_sched:
                        return

                # // perform all events that are ready
                while not self._task_queue.empty()\
                and elapsed_beats >= self._task_queue.peek()[0]:
                    item = self._task_queue.pop()
                    self._beats = item[0]
                    task = item[1]
                    try:
                        _libsc3.main._update_logical_time(
                            self.beats2secs(self._beats))
                        _libsc3.main._in_awake_call = True
                        delta = task.__awake__(self)
                        if isinstance(delta, (int, float))\
                        and not isinstance(delta, bool):
                            time = self._beats + delta
                            self._sched_add(time, task)
                    except stm.StopStream:
                        pass
                    except Exception:
                        _logger.error(
                            '%s(%s) scheduled on TempoClock id %s',
                            type(task).__name__, task.func.__qualname__,
                            id(self), exc_info=1)
                    finally:
                        _libsc3.main._in_awake_call = False

    def stop(self):
        '''Stop the clock's scheduling thread.

        Note
        ----
        TempoClock objects need to be stopped in order to be gc collected.

        '''

        if self.mode == _libsc3.main.NRT_MODE:
            return
        if not self.running():
            _logger.debug(f'{self} is not running')
            return
        stop_thread = threading.Thread(
            target=self._stop,
            name=f'{type(self).__name__}.stop_thread id: {id(self)}',
            daemon=True)
        stop_thread.start()
        _libsc3.main._atexitq.remove(self._stop)

    def _stop(self):
        if not self._run_sched:
            return
        with self._sched_cond:
            self._task_queue.clear()
            type(self)._all.remove(self)
            self._run_sched = False
            self._sched_cond.notify_all()
        self._thread.join()
        self._thread = None
        self._sched_cond = None

    # def __del__(self):
    #     # self needs to be stoped to be gc collected because
    #     # is in cyclic reference with target=_run.
    #     self.stop()

    def play(self, task, quant=None):
        '''Schedule a Routine or Function to be evaluated in this clock.

        If the return value of functions or yield value of routines is int
        or float the task will be rescheduled using that value as delta.
        This method shares semantics with other objects `play` methods that
        use clocks to schedule tasks.

        Parameters
        ----------
        task : Routine | Function
            Task to be scheduled. If the argument is a common function it
            will be wrapped into a Function object to be scheduled.
        quant : Quant
            A Quant object or a any value that can be cast into one with
            Quant.as_quant constructor.

        '''

        quant = Quant.as_quant(quant)
        self.sched_abs(quant.next_time_on_grid(self), task)

    def play_next_bar(self, task):
        '''Schedule a Routine or Function to be evaluated at the next bar.'''
        self.sched_abs(self.next_bar(), task)

    @property
    def tempo(self):
        '''Return the tempo in beats per second at the current `logical time`.'''
        # _TempoClock_Tempo
        if not self.running():
            raise ClockNotRunning(self)
        return self._tempo

    @tempo.setter
    def tempo(self, value):
        '''Set the tempo in beats per second at the current `logical time`.'''
        # // For setting the tempo at the current logical time
        # // (even another TempoClock's logical time).
        # setTempoAtBeat(newTempo, this.beats) -> prTempoClock_SetTempoAtBeat
        if not self.running():
            raise ClockNotRunning(self)
        if value == 0.0:
            raise ValueError("tempo can't be zero")
        if self._tempo < 0.0:
            raise ValueError(
                "cannot set tempo from this method. "
                "The method 'etempo()' can be used instead")
        if value < 0.0:
            raise ValueError(
                f"invalid tempo {value}. The method "
                "'etempo()' can be used instead.")
        # TempoClock::SetTempoAtBeat
        beats = self.beats
        self._base_seconds = self.beats2secs(beats)
        self._base_beats = beats
        self._tempo = value
        self._beat_dur = 1.0 / self._tempo
        # en tempo_
        mdl.NotificationCenter.notify(self, 'tempo')
        if self.mode == _libsc3.main.NRT_MODE:
            return
        else:
            with self._sched_cond:
                self._sched_cond.notify()  # NOTE: is notify_one in C++.

    def etempo(self, value):
        '''Set the current tempo at the current `elapsed time`.

        Warning
        -------
        Using this method tempo can be negative and beats will go backguard.
        This behaviour will cause default scheduling mechanisms to fail.

        '''

        # setTempoAtSec(newTempo, Main.elapsedTime) -> _TempoClock_SetTempoAtTime
        if not self.running():
            raise ClockNotRunning(self)
        if value == 0.0:
            raise ValueError("tempo can't be zero")
        # TempoClock::SetTempoAtTime
        seconds = _libsc3.main.elapsed_time()
        self._base_beats = self.secs2beats(seconds)
        self._base_seconds = seconds
        self._tempo = value
        self._beat_dur = 1.0 / self._tempo
        # etempo_
        mdl.NotificationCenter.notify(self, 'tempo')
        if self.mode == _libsc3.main.NRT_MODE:
            return
        else:
            with self._sched_cond:
                self._sched_cond.notify()  # NOTE: is notify_one in C++.

    @property
    def beat_dur(self):
        '''Beat duration in seconds.'''
        if not self.running():
            raise ClockNotRunning(self)
        return self._beat_dur

    def elapsed_beats(self):
        '''Return the beats for this clock relative to main `elapsed time`.'''
        if not self.running():
            raise ClockNotRunning(self)
        return self.secs2beats(_libsc3.main.elapsed_time())

    @property
    def beats(self):
        '''Current time in beats according to this clock.

        When getting beats, if this clock is the current routine's
        `associated clock`, it returns the current `logical time` in beats
        since the clock whas instantiated, when called from another routine
        or the main thread it returns their current time in seconds converted
        to beats according to this clock tempo.

        After changing beats towards the future, the clock will immediately
        perform all tasks scheduled until the new time. Likewise, when changing
        beats towards the past, already scheduled tasks will be postponed, so
        they will still be performed at the scheduled time in beats.

        Note
        ----
        Setting this property only changes the clocks's base time reference
        relative to `physical time`. If called from an already scheduled
        routine the change will only take effect after rescheduling, e.g.,
        after the routine yields.

        The use of the setter is discoraged. Because the clocks's time is
        always updating, either in seconds or beats, if multiple routines are
        scheduled to the same clock it could easily lead to inconsistencies
        or obfuscated code.

        '''

        return self.secs2beats(_libsc3.main.current_tt._seconds)

    @beats.setter
    def beats(self, value):
        if not self.running():
            raise ClockNotRunning(self)
        seconds = _libsc3.main.current_tt._seconds
        self._base_seconds = seconds
        self._base_beats = value
        self._beat_dur = 1.0 / self._tempo
        if self.mode == _libsc3.main.NRT_MODE:
            return
        else:
            with self._sched_cond:
                self._sched_cond.notify()  # NOTE: is notify_one in C++

    @property
    def seconds(self):
        '''Return `elapsed time` as `logical time` from within scheduled routines.'''
        return _libsc3.main.current_tt._seconds

    def _sched_add(self, beats, task):
        # Call with acquired lock.
        if self._task_queue.empty():
            prev_beat = -1e10
        else:
            prev_beat = self._task_queue.peek()[0]
        self._task_queue.add(beats, task)
        if self._task_queue.peek()[0] != prev_beat:
            self._sched_cond.notify()

    def _sched_add_nrt(self, beats, task):
        ClockTask(beats, self, task, _libsc3.main._clock_scheduler)

    def _calc_sched_beats(self, delta):
        seconds = _libsc3.main.current_tt._seconds
        beats = self.secs2beats(seconds)
        return beats + delta

    def sched(self, delta, item):
        '''
        Schedule a new task `item` to be evaluated after `delta` beats from
        current clock's beat.

        '''

        if not self.running():
            raise ClockNotRunning(self)
        if not hasattr(item, '__awake__'):
            item = fn.Function(item)
        item._clock = self
        if self.mode == _libsc3.main.NRT_MODE:
            beats = self._calc_sched_beats(delta)
            if beats == float('inf'):
                return
            self._sched_add_nrt(beats, item)
        else:
            with self._sched_cond:
                beats = self._calc_sched_beats(delta)
                if beats == float('inf'):
                    return
                self._sched_add(beats, item)

    def sched_abs(self, beat, item):
        '''
        Schedule a new task `item` to be evaluated at a `beat` point in the
        future relative this clock's current beat.

        '''

        if not self.running():
            raise ClockNotRunning(self)
        if not hasattr(item, '__awake__'):
            item = fn.Function(item)
        item._clock = self
        if beat == float('inf'):
            return
        if self.mode == _libsc3.main.NRT_MODE:
            self._sched_add_nrt(beat, item)
        else:
            with self._sched_cond:
                self._sched_add(beat, item)

    def clear(self):
        '''Remove all pending tasks from the scheduler queue.'''
        if self.mode == _libsc3.main.NRT_MODE:
            return
        if self.running():  # and self._run_sched:  # NOTE: Was needed?
            with self._sched_cond:
                while not self._task_queue.empty():
                    self._task_queue.pop()
                self._sched_cond.notify()  # NOTE: is notify_one in C++.

    @property
    def beats_per_bar(self):
        '''Number of beats grouped as a measure, default is 4.

        Get or set the beats per bar for quantization. When setting this
        property, the reference `base_bar_beat` value will be set to whatever
        beat fraction is at that time within the scheduled time thread,
        i.e., the new bar will start at that time and may truncate the
        previous one.

        Note
        ----
        This value should only be changed from within the scheduling thread
        of the same clock, otherwise a ClockError will be thrown.

        '''

        return self._beats_per_bar

    @beats_per_bar.setter
    def beats_per_bar(self, value):
        if _libsc3.main.current_tt._clock is not self:
            raise ClockError(
                'TempoClock should only change beats_per_bar '
                'within the scheduling thread')
        # setMeterAtBeat
        beats = self.beats
        self._base_bar = bi.round(
            (beats - self._base_bar_beat) *
            self._bars_per_beat + self._base_bar, 1)
        self._base_bar_beat = beats
        self._beats_per_bar = value
        self._bars_per_beat = 1 / value
        mdl.NotificationCenter.notify(self, 'meter')

    @property
    def base_bar(self):
        '''Return the bar at which `beats_per_bar` was last changed.

        If `beats_per_bar` has not been changed since the clock was created
        return 0.0.

        '''

        return self._base_bar

    @property
    def base_bar_beat(self):
        '''Return the beat at which the `beats_per_bar` was last changed.

        If `beats_per_bar` has not been changed since the clock was created
        it returns 0.0.

        '''

        return self._base_bar_beat

    def beats2secs(self, beats):
        if not self.running():
            raise ClockNotRunning(self)
        return (beats - self._base_beats) * self._beat_dur + self._base_seconds

    def secs2beats(self, seconds):
        if not self.running():
            raise ClockNotRunning(self)
        return (seconds - self._base_seconds) * self._tempo + self._base_beats

    def dump(self):
        '''Print the state of the clock for debugging purposes.'''
        if self.running():
            print(
                f'{self.__repr__()}\n'
                f'    tempo: {self.tempo}\n'
                f'    beats: {self.beats}\n'
                f'    seconds: {self.seconds}\n'
                f'    beat_dur: {self._beat_dur}\n'
                f'    _base_beats: {self._base_beats}\n'
                f'    _base_seconds: {self._base_seconds}')
        else:
            raise ClockNotRunning(self)

    def next_time_on_grid(self, quant=1, phase=0):
        '''Return the next quantized beat.

        With default values for `quant` and `phase` it returns the next whole
        beat. The `quant` parameter is relative to `base_bar_beat`, such that::

            clock = TempoClock()
            clock.next_time_on_grid(clock.beats_per_bar) == clock.next_bar()

        Together `quant` and `phase` are useful for finding the next *n* beat
        in a bar, e.g. `clock.next_time_on_grid(4, 2)` may return the next
        third beat of the current or next bar depending on whether the current
        beat is before or after the third beat of the current bar, whereas
        `clock.next_bar() - 2` may return an elapsed beat and
        `clock.next_bar() + 2` will always return the third beat of the next
        bar only.

        '''

        if quant == 0:
            return self.beats + phase
        if quant < 0:
            quant = self.beats_per_bar * -quant
        if phase < 0:
            phase = bi.mod(phase, quant)
        return bi.roundup(
            self.beats - self._base_bar_beat - bi.mod(phase, quant),
            quant
        ) + self._base_bar_beat + phase

    def time_to_next_beat(self, quant=1):
        '''Return the duration remaining until the next beat in `logical time`.

        The `quant` parameter is relative to `base_bar_beat`.

        '''

        return Quant.as_quant(quant).next_time_on_grid(self) - self.beats

    def beats2bars(self, beats):
        '''Return the bar number relative to `base_bar_beat`.'''
        return (beats - self._base_bar_beat) * self._bars_per_beat\
               + self._base_bar

    def bars2beats(self, bars):
        '''Return the number of beats relative to `base_bar`.'''
        return (bars - self._base_bar) * self._beats_per_bar\
               + self._base_bar_beat

    def bar(self):
        '''Return the current bar number.'''
        return float(bi.floor(self.beats2bars(self.beats)))

    def next_bar(self, beat=None):
        '''Given a `beat` number, return the beat number of the next bar line.

        If `beat` is the start beat of a bar return the same number.

        '''

        if beat is None:
            beat = self.beats
        return self.bars2beats(bi.ceil(self.beats2bars(beat)))

    def beat_in_bar(self):
        '''Return the current beat of the bar as a float.

        Range is from 0 to < `beats_per_bar`.

        '''

        return self.beats - self.bars2beats(self.bar())

    def running(self):
        '''Return True if the clock is running.'''
        if self.mode == _libsc3.main.NRT_MODE:
            return True
        else:
            return self._thread is not None and self._thread.is_alive()


def defer(func, delta=None, clock=None):
    '''
    Convenience function to defer lambda functions on a clock without
    creating a `Routine` or `sched` call. Default value for `delta` is 0.0,
    default `clock` is `AppClock`. Argument `func` can be any callable.

    '''

    if callable(func):
        def df():
            func()  # Wrapped because lambda always return its expression value.
    else:
        raise TypeError('func is not callable')
    clock = clock or AppClock
    clock.sched(delta or 0, df)
