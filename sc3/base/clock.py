"""Clock.sc"""

import logging
import threading
import time as _time
import sys
import traceback
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
    'SystemClock', 'Scheduler', 'AppClock', 'Quant', 'TempoClock', 'defer']


_logger = logging.getLogger(__name__)


class ClockError(RuntimeError):
    pass


class ClockNotRunning(ClockError):
    pass


### Clocks for timing threads ###


class MetaClock(type):
    _pure_nrt = False  # Must be set by sub metaclasses in __init__.

    def play(cls, task, quant=None):
        # Unused quant (needed for tempo clock compatibility).
        cls.sched(0, task)

    @property
    def mode(cls):
        if cls._pure_nrt:
            return _libsc3.main.NRT_MODE
        elif _libsc3.main is _libsc3.RtMain:
            return _libsc3.main.RT_MODE
        else:
            return _libsc3.main.NRT_MODE

    @property
    def seconds(cls):
        return _libsc3.main.current_tt._seconds

    # // tempo clock compatibility

    @property
    def beats(cls):
        return _libsc3.main.current_tt._seconds

    def beats2secs(cls, beats):
        return beats

    def secs2beats(cls, secs):
        return secs

    def beats2bars(cls):
        return 0

    def bars2beats(cls):
        return 0

    def time_to_next_beat(cls, quant=1):
        return 0

    def next_time_on_grid(cls, quant=1, phase=0):
        if quant == 0:
            return cls.beats() + phase
        if phase < 0:
            phase = bi.mod(phase, quant)
        return bi.roundup(cls.beats() - bi.mod(phase, quant), quant) + phase


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
    _SECONDS_FROM_1900_TO_1970 = 2208988800 # (int32)UL # 17 leap years
    _NANOS_TO_OSC = 4.294967296 # PyrSched.h: const double kNanosToOSC  = 4.294967296; // pow(2,32)/1e9
    _MICROS_TO_OSC = 4294.967296 # PyrSched.h: const double kMicrosToOSC = 4294.967296; // pow(2,32)/1e6
    _SECONDS_TO_OSC = 4294967296. # PyrSched.h: const double kSecondsToOSC  = 4294967296.; // pow(2,32)/1
    _OSC_TO_NANOS = 0.2328306436538696# PyrSched.h: const double kOSCtoNanos  = 0.2328306436538696; // 1e9/pow(2,32)
    _OSC_TO_SECONDS = 2.328306436538696e-10 # PyrSched.h: const double kOSCtoSecs = 2.328306436538696e-10;  // 1/pow(2,32)

    def __new__(cls):
        return cls

    @classmethod
    def _sched_init(cls):
        # _time_of_initialization was moved to main because rt/nrt clock switch.
        cls._host_osc_offset = 0 # int64
        cls._sync_osc_offset_with_tod()
        cls._host_start_nanos = int(_libsc3.main._time_of_initialization / 1e-9) # to nanos
        cls._elapsed_osc_offset = int(
            cls._host_start_nanos * cls._NANOS_TO_OSC
        ) + cls._host_osc_offset

        # same every 20 secs
        cls._resync_cond = threading.Condition()
        cls._resync_thread = threading.Thread(
            target=cls._resync_thread_func,
            name=f'{cls.__name__}.resync',
            daemon=True)
        cls._resync_thread.start()

    @classmethod
    def _sync_osc_offset_with_tod(cls): # L314, esto se hace en _rsync_thread
        # // generate a value gHostOSCoffset such that
        # // (gHostOSCoffset + systemTimeInOSCunits)
        # // is equal to gettimeofday time in OSCunits.
        # // Then if this machine is synced via NTP, we are synced with the world.
        # // more accurate way to do this??
        number_of_tries = 8
        diff = 0 # int64
        min_diff = 0x7fffFFFFffffFFFF # int64
        new_offset = cls._host_osc_offset

        for i in range(0, number_of_tries):
            system_time_before = _time.time()  # must be the same epoch
            time_of_day = _time.time()  # must be gmt time
            system_time_after = _time.time()

            system_time_before = int(system_time_before / 1e-9)
            system_time_after = int(system_time_after / 1e-9)
            diff = system_time_after - system_time_before

            if diff < min_diff:
                min_diff = diff

                system_time_between = system_time_before + diff // 2
                system_time_in_osc_units = int(
                    system_time_between * cls._NANOS_TO_OSC)

                # mimics
                tv_sec = int(time_of_day)
                tv_usec = int((time_of_day % 1) / 1e-6)
                time_of_day_in_osc_units = (
                    (int(tv_sec + cls._SECONDS_FROM_1900_TO_1970) << 32)
                    + int(tv_usec * cls._MICROS_TO_OSC))

                new_offset = time_of_day_in_osc_units - system_time_in_osc_units

        # This function seems to add only the jitter between clock calls here
        # and in sclang. Running every 20 seconds or 1 minute would be the same
        # if the date clock wasn't adjusted by ntp. Based on the logged numbers
        # osc time may jump up to ~700 nanoseconds, far from ~238 picoseconds.
        # NOTE: Without this bundles will be late.
        # print('new offset diff:', cls._host_osc_offset - new_offset)
        cls._host_osc_offset = new_offset

    @classmethod
    def _resync_thread_func(cls):  # L408
        cls._run_resync = True

        with cls._resync_cond:
            while cls._run_resync:
                cls._resync_cond.wait(20)
                if not cls._run_resync:
                    return

                cls._sync_osc_offset_with_tod()
                cls._elapsed_osc_offset = int(
                    cls._host_start_nanos * cls._NANOS_TO_OSC
                ) + cls._host_osc_offset

    @classmethod
    def elapsed_time_to_osc(cls, elapsed: float) -> int:  # int64
        return int(
            elapsed * cls._SECONDS_TO_OSC
        ) + cls._elapsed_osc_offset

    @classmethod
    def osc_to_elapsed_time(cls, osctime: int) -> float:  # L286
        return float(
            osctime - cls._elapsed_osc_offset
        ) * cls._OSC_TO_SECONDS

    @classmethod
    def osc_time(cls) -> int:  # L309
        return cls.elapsed_time_to_osc(_libsc3.main.elapsed_time())

    @classmethod
    def _sched_add(cls, secs, task):  # L353
        if cls._task_queue.empty():
            prev_time = -1e10
        else:
            prev_time = cls._task_queue.peek()[0]
        cls._task_queue.add(secs, task)
        # if isinstance(task, pst.PauseStream):
        #     task._next_beat = secs
        if cls._task_queue.peek()[0] != prev_time:
            cls._sched_cond.notify_all()  # Call with acquired lock.

    @classmethod
    def _sched_stop(cls):
        if not cls._run_sched:
            return
        with cls._sched_cond:
            with cls._resync_cond:
                if cls._run_resync:
                    cls._run_resync = False
                    cls._resync_cond.notify()
            cls._task_queue.clear()
            cls._run_sched = False
            cls._sched_cond.notify_all()
        cls._resync_thread.join()
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
                    # NOTE: I think there is no need for this clock to be
                    # monotonic and sclang may or may not be working this way,
                    # is less complicated here to use just elapsed_time.
                    # I leave previous code commented for now (this should be the same).
                    # now = _time.time()
                    now = _libsc3.main.elapsed_time()
                    sched_secs = cls._task_queue.peek()[0]
                    # sched_point = (_libsc3.main._time_of_initialization
                    #                + sched_secs)
                    # if now >= sched_point:
                    if now >= sched_secs:
                        break
                    # cls._sched_cond.wait(sched_point - now)
                    cls._sched_cond.wait(sched_secs - now)
                    if not cls._run_sched:
                        return

                # // perform all events that are ready
                # while not cls._task_queue.empty()\
                # and now >= (_libsc3.main._time_of_initialization
                #             + cls._task_queue.peek()[0]):
                while not cls._task_queue.empty()\
                and now >= cls._task_queue.peek()[0]:
                    item = cls._task_queue.pop()
                    sched_time = item[0]
                    task = item[1]
                    # if isinstance(task, pst.PauseStream):
                    #     task._next_beat = None
                    try:
                        _libsc3.main.update_logical_time(sched_time)
                        delta = task.__awake__(sched_time, sched_time, cls)
                        if isinstance(delta, (int, float))\
                        and not isinstance(delta, bool):
                            time = sched_time + delta
                            cls._sched_add(time, task)
                    except stm.StopStream:
                        pass
                    except Exception:
                        # Always recover.
                        _logger.error(
                            'from %s (%s) scheduled on SystemClock',
                            task, task.func.__qualname__, exc_info=1)

    # sclang methods

    @classmethod
    def clear(cls):
        if cls.mode == _libsc3.main.NRT_MODE:
            return
        with cls._sched_cond:
            item = None
            # BUG: NO SÉ QUE ESTABA PENSANDO CUANOD HICE ESTE, FALTA:
            # BUG: queue es thisProcess.prSchedulerQueue, VER!
            while not cls._task_queue.empty():
                item = cls._task_queue.pop()[1]
            cls._sched_cond.notify_all()
            # BUG: llama a prClear, VER!

    @classmethod
    def sched(cls, delta, item):
        if not hasattr(item, '__awake__'):
            item = fn.Function(item)
        item._clock = cls
        if cls.mode == _libsc3.main.NRT_MODE:
            # See note in TempoClock sched.
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

    # L542 y L588 setea las prioridades 'rt' para mac o linux, es un parámetro de los objetos Thread
    # ver qué hace std::move(thread)
    # def sched_run(cls): # L609, crea el thread de SystemClock
    #     # esto es simplemente start (sched_run_func es run) con prioridad rt
    #     # iría en el constructor/inicializador
    #     ...
    # L651, comentario importante sobre qué maneja cada reloj
    # luego ver también las funciones que exporta a sclang al final de todo


class Scheduler():
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
            delta = item.__awake__(self._beats, self._seconds, self._clock)
            if isinstance(delta, (int, float)) and not isinstance(delta, bool):
                self._sched_add(delta, item)
        except stm.StopStream:
            pass
        except Exception:
            _logger.error(
                'from %s (%s) scheduled on AppClock',
                item, item.func.__qualname__, exc_info=1)

    def play(self, task):
        self.sched(0, task)

    def _sched_add(self, delta, item):
        if self._drift:
            from_time = _libsc3.main.elapsed_time()
        else:
            from_time = self.seconds = _libsc3.main.current_tt._seconds
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
        item = None
        while not self.queue.empty():
            item = self.queue.pop()

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
                cls._sched_cond = threading.Condition(_libsc3.main._main_lock)
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
    def __new__(cls):
        return cls

    @classmethod
    def _run(cls):
        cls._run_sched = True
        seconds = None
        while True:
            with cls._sched_cond:
                seconds = cls._tick()  # First tick for free, returns None
                if isinstance(seconds, (int, float))\
                and not isinstance(seconds, bool):
                    seconds = seconds - cls._scheduler.seconds  # tick returns abstime (elapsed)
            with cls._tick_cond:  # many notify one wait
                cls._tick_cond.wait(seconds)  # if seconds is None waits for notify
            if not cls._run_sched: return

    @classmethod
    def clear(cls):
        if cls.mode == _libsc3.main.NRT_MODE:
            return
        else:
            cls._scheduler.clear()

    @classmethod
    def sched(cls, delta, item):
        if cls.mode == _libsc3.main.NRT_MODE:
            if not hasattr(item, '__awake__'):
                item = fn.Function(item)
            item._clock = cls
            if delta == float('inf'):
                return
            ClockTask(delta, cls, item, _libsc3.main._clock_scheduler)
        else:
            with cls._sched_cond:
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

    # NOTE: Este comentario es un recordatorio.
    # def _sched_notify(cls):
    # _AppClock_SchedNotify
    # En SC_TerminalClient _AppClock_SchedNotify es SC_TerminalClient::prScheduleChanged
    # que llama a la instancia del cliente (de sclang), que llama a su método
    # sendSignal(sig_sched) con la opción sig_sched que llama a SC_TerminalClient::tick
    # Acá podría ir todo dentro de sched(), ergo sum chin pum: cls._tick()


class ClockScheduler(threading.Thread):
    def __init__(self):
        self._sched_cond = threading.Condition(_libsc3.main._main_lock)
        self.queue = tsq.TaskQueue()
        threading.Thread.__init__(self)
        self.daemon = True
        self.start()
        _libsc3.main._atexitq.add(
            _libsc3.main._atexitprio.CLOCKS + 3, self.stop)

    def run(self):
        self._run_sched = True
        with self._sched_cond:
            while True:
                while self.queue.empty():
                    self._sched_cond.wait()
                    if not self._run_sched:
                        return
                while not self.queue.empty():
                    time, clock_task = self.queue.pop()
                    clock_task._wakeup(time)

    def add(self, time, clock_task):
        with self._sched_cond:
            self.queue.add(time, clock_task)
            self._sched_cond.notify()

    def stop(self):
        if not self._run_sched:
            return
        with self._sched_cond:
            self.queue.clear()
            self._run_sched = False
            self._sched_cond.notify()
        # self.join() # Who calls???
        _libsc3.main._atexitq.remove(self.stop)


class ClockTask():
    def __init__(self, beats, clock, task, scheduler):
        self.clock = clock
        self.task = task
        self.scheduler = scheduler
        if scheduler.is_alive():
            scheduler.add(clock.beats2secs(beats), self)
        else:
            RuntimeError('ClockScheduler is not running')

    def _wakeup(self, time):
        try:
            # if isinstance(self.task, pst.PauseStream):
            #     self.task._next_beat = None
            _libsc3.main.update_logical_time(time)
            beats = self.clock.secs2beats(time)
            delta = self.task.__awake__(beats, time, self.clock)
            if isinstance(delta, (int, float)) and not isinstance(delta, bool):
                self.scheduler.add(self.clock.beats2secs(beats + delta), self)
        except stm.StopStream:
            pass
        except Exception:
            _logger.error(
                'from %s (%s) scheduled on ClockScheduler',
                self.task, self.task.func.__qualname__, exc_info=1)


### Quant.sc ###
# // This class is used to encapsulate quantization issues associated with EventStreamPlayer and TempoClock
# // quant and phase determine the starting time of something scheduled by a TempoClock
# // timingOffset is an additional timing factor that allows an EventStream to compute "ahead of time" enough to allow
# // negative lags for strumming a chord, etc


class Quant():
    def __init__(self, quant=0, phase=None, timing_offset=None):
        self.quant = quant
        self.phase = phase
        self.timing_offset = timing_offset

    # *default # NOTE: no se usa acá, no tiene mucho valor, se pasa como responsabilidad del usuario, si alguna clase lo necesita define su propio default.

    # NOTE: Quant se usa en TempoClock.play y Event.sync_with_quant (hasta donde vi)
    # NOTE: Para asQuant los valores válidos son None, int, list, tuple y Quant.
    # NOTE: Otra opción es que quant pueda ser solo un entero o una tupla y hacer
    # NOTE: la lógica de Quant.next_time_on_grid en el método play de TempoClock.
    # NOTE: asQuant { ^this.copy() } lo implementan SimpleNumber { ^Quant(this) }, SequenceableCollection { ^Quant(*this) }, Nil { ^Quant.default } y IdentityDictionary { ^this.copy() }
    # NOTE: asQuant se usa en EventStreamPlayer.play, Quant.default, PauseStream.play,
    # NOTE: Routine.play y Stream.play.
    @classmethod
    def as_quant(cls, quant):
        if isinstance(quant, cls):
            pass
        elif isinstance(quant, int):
            quant = cls(quant)
        elif isinstance(quant, (list, tuple)):
            quant = cls(*quant[:3])
        elif quant is None:
            quant = cls()
        else:
            msg = f'unsuported type conversion to Quant: {type(quant)}'
            raise TypeError(msg)
        return quant

    # NOTE: Este método es un método de Clock y TempoClock y reciben quant como escalar (!)
    # NOTE: De los objetos que implementan next_time_on_grid Clock y TempoClock
    # NOTE: reciben quant como valór numérico. Los demás objetos reciben un
    # NOTE: reloj y llama al método next_time_on_grid del reloj. Es muy rebuscada
    # NOTE: la implementación, tal vez algo cambió y esos métodos quedaron
    # NOTE: confusos. Acá solo lo implemento en Quant, Clock y TempoClock.
    def next_time_on_grid(self, clock):
        return clock.next_time_on_grid(
            self.quant, (self.phase or 0) - (self.timing_offset or 0))

    # printOn
    # storeArgs


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
# NOTE: Elapsed time, tiempo transcurrido, es el tiempo físico, en
# NOTE: contraposición al tiempo lógico. La base temporal es el tempo.


class MetaTempoClock(MetaClock):
    def __init__(cls, *_):
        cls._all = weakref.WeakSet()

        def init_func(cls):
            cls.default = cls()
            cls.default.permanent = True
            sac.CmdPeriod.add(cls.__on_cmd_period)

        clb.ClassLibrary.add(cls, init_func)

    def __on_cmd_period(cls):
        for clock in cls.all:
            clock.clear()
            if not clock.permanent:
                clock.stop()

    @property
    def all(cls):
        return set(cls._all)


class TempoClock(Clock, metaclass=MetaTempoClock):
    # BUG: C++ TempoClock_stopAll se usa en ./lang/LangSource/PyrLexer.cpp
    # BUG: shutdownLibrary(), no importa si hay permanentes, va para Main, VER.

    # BUG: A LOS TEMPOCLOCK SE LOS TIENE QUE PODER LLEVAR EL COLECTOR DE BASURA LLAMANDO A STOP().

    def __init__(self, tempo=None, beats=None, seconds=None):
        # prTempoClock_New
        tempo = tempo or 1.0  # tempo=0 is invalid too.
        if tempo < 0.0:
            raise ValueError(f'invalid tempo {tempo}')

        # TempoClock::TempoClock()
        self._tempo = tempo
        self._beat_dur = 1.0 / tempo
        self._base_seconds = seconds or _libsc3.main.current_tt._seconds
        self._base_beats = beats or 0.0
        self._beats = 0.0

        # init luego de prStart
        self._beats_per_bar = 4.0
        self._bars_per_beat = 0.25
        self._base_bar_beat = 0
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
                    # NOTE: I think there is no need for this clock to be
                    # monotonic and sclang may or may not be working this way,
                    # is less complicated here to use just elapsed_time.
                    # I leave previous code commented by now (this should be
                    # the same).
                    # sched_point = _libsc3.main._time_of_initialization + sched_secs
                    # self._sched_cond.wait(sched_point - _time.time())
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
                    # if isinstance(task, pst.PauseStream):
                    #     task._next_beat = None
                    try:
                        _libsc3.main.update_logical_time(
                            self.beats2secs(self._beats))
                        delta = task.__awake__(
                            self._beats, self.beats2secs(self._beats), self)
                        if isinstance(delta, (int, float))\
                        and not isinstance(delta, bool):
                            time = self._beats + delta
                            self._sched_add(time, task)
                    except stm.StopStream:
                        pass
                    except Exception:
                        _logger.error(
                            'from %s (%s) scheduled on TempoClock id: %s',
                            task, task.func.__qualname__, id(self), exc_info=1)

    def stop(self):
        # prStop -> prTempoClock_Free -> StopReq -> StopAndDelete -> Stop
        if self.mode == _libsc3.main.NRT_MODE:
            return
        # prTempoClock_Free
        if not self.running():
            _logger.debug(f'{self} is not running')
            return
        # StopReq
        stop_thread = threading.Thread(
            target=self._stop,
            name=f'{type(self).__name__}.stop_thread id: {id(self)}',
            daemon=True)
        stop_thread.start()
        _libsc3.main._atexitq.remove(self._stop)

    def _stop(self):
        # StopAndDelete
        # Stop
        if not self._run_sched:
            return
        with self._sched_cond:
            self._task_queue.clear()
            type(self)._all.remove(self)
            self._run_sched = False
            self._sched_cond.notify_all()  # In TempoClock::Stop is notify_all
        self._thread.join()
        self._thread = None
        self._sched_cond = None

    # def __del__(self):
    #     # BUG: self needs to be stoped to be gc collected because is in
    #     # BUG: cyclic reference with target=_run.
    #     self.stop()

    def play(self, task, quant=None):
        quant = Quant.as_quant(quant)
        self.sched_abs(quant.next_time_on_grid(self), task)

    def play_next_bar(self, task):
        self.sched_abs(self.next_bar(), task)

    @property
    def tempo(self):
        # _TempoClock_Tempo
        if not self.running():
            raise ClockNotRunning(self)
        return self._tempo

    # // for setting the tempo at the current logical time
    # // (even another TempoClock's logical time).
    @tempo.setter
    def tempo(self, value):
        # NOTE: tempo_ llama a setTempoAtBeat (_TempoClock_SetTempoAtBeat)
        # NOTE: que es privado según la nota. Lo debe hacer porque no puede
        # NOTE: llamar directamente a la primitiva porque notifica a las
        # NOTE: dependacy o porque difiere la lógica del objeto en C++.
        # NOTE: Paso la lógica de setTempoAtBeat y TempoClock::SetTempoAtBeat a este setter.
        # setTempoAtBeat(newTempo, this.beats) -> prTempoClock_SetTempoAtBeat
        if not self.running():
            raise ClockNotRunning(self)
        if value == 0.0:
            raise ValueError("tempo can't be zero")
        if self._tempo < 0.0: # BUG: NO ES CLARO: usa _tempo (mTempo), que puede ser negativo mediante etempo y en ese caso no deja setear acá, ES RARO.
            raise ValueError(
                "cannot set tempo from this method. "
                "The method 'etempo()' can be used instead")
        if value < 0.0:
            raise ValueError(
                f"invalid tempo {value}. The method "
                "'etempo()' can be used instead.")
        # TempoClock::SetTempoAtBeat
        beats = self.beats # NOTE: hay obtenerlo solo una vez porque el getter cambia al setear las variables, en C++ es el argumento de una función.
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
                self._sched_cond.notify() # NOTE: es notify_one en C++

    # // for setting the tempo at the current elapsed time.
    def etempo(self, value):
        # TODO: this.setTempoAtSec(newTempo, Main.elapsedTime);
        # _TempoClock_SetTempoAtTime
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
                self._sched_cond.notify() # NOTE: es notify_one en C++

    def beat_dur(self):
        # _TempoClock_BeatDur
        if not self.running():
            raise ClockNotRunning(self)
        return self._beat_dur

    def elapsed_beats(self):
        # _TempoClock_ElapsedBeats
        if not self.running():
            raise ClockNotRunning(self)
        return self.secs2beats(_libsc3.main.elapsed_time())

    @property
    def beats(self):
        # _TempoClock_Beats
        # // returns the appropriate beats for this clock from any thread
        return self.secs2beats(_libsc3.main.current_tt._seconds)

    @beats.setter
    def beats(self, value):
        # _TempoClock_SetBeats
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
                self._sched_cond.notify() # NOTE: es notify_one en C++

    @property
    def seconds(self):
        return _libsc3.main.current_tt._seconds

    def _sched_add(self, beats, task):
        # TempoClock::Add
        if self._task_queue.empty():
            prev_beat = -1e10
        else:
            prev_beat = self._task_queue.peek()[0]
        self._task_queue.add(beats, task)
        # if isinstance(task, pst.PauseStream):
        #     task._next_beat = beats
        if self._task_queue.peek()[0] != prev_beat:
            self._sched_cond.notify()  # *** BUG: usa notify poruqe se llama anidado, cambiar.

    def _sched_add_nrt(self, beats, task):
        # if isinstance(task, pst.PauseStream):
        #     task._next_beat = beats
        ClockTask(beats, self, task, _libsc3.main._clock_scheduler)

    def _calc_sched_beats(self, delta):
        seconds = _libsc3.main.current_tt._seconds
        beats = self.secs2beats(seconds)
        return beats + delta

    def sched(self, delta, item):
        # _TempoClock_Sched
        if not self.running():
            raise ClockNotRunning(self)
        if not hasattr(item, '__awake__'):
            item = fn.Function(item)
        item._clock = self
        # NOTE: Code is complicated because the lock. In RT the lock prevents
        # to calculate a time here and then, because threading, to excecute
        # a greater time element from the queue before this one is added. To
        # leave a real lock as dummy is not an option because is a system
        # resource, if was a fake lock wouldn't be clear. Also, _sched_add
        # needs to be called already locked because is used from outside and
        # within the _run loop.
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
        # _TempoClock_SchedAbs
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
        # clear -> prClear -> _TempoClock_Clear -> TempoClock::Clear
        if self.mode == _libsc3.main.NRT_MODE:
            return
        if self.running():  # and self._run_sched:  # NOTE: _run_sched check was needed?
            item = None
            with self._sched_cond:
                while not self._task_queue.empty():
                    item = self._task_queue.pop()[1] # de por sí PriorityQueue es thread safe, la implementación de SuperCollider es distinta, ver SystemClock*clear.
                self._sched_cond.notify() # NOTE: es notify_one en C++

    @property
    def beats_per_bar(self):
        return self._beats_per_bar

    @beats_per_bar.setter
    def beats_per_bar(self, value):
        if _libsc3.main.current_tt is not self:
            raise ClockError(
                'TempoClock should only change beats_per_bar'
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

    @property # TODO: no parece tener setter.
    def base_bar_beat(self):
        return self._base_bar_beat

    @property # TODO: no parece tener setter.
    def base_bar(self):
        return self._base_bar

    def beats2secs(self, beats):
        # _TempoClock_BeatsToSecs
        if not self.running():
            raise ClockNotRunning(self)
        return (beats - self._base_beats) * self._beat_dur + self._base_seconds

    def secs2beats(self, seconds):
        # _TempoClock_SecsToBeats
        if not self.running():
            raise ClockNotRunning(self)
        return (seconds - self._base_seconds) * self._tempo + self._base_beats

    def dump(self):
        # _(pr)TempoClock_Dump -> TepmoClock::Dump
        # BUG: Pero no usa este método sclang, usa dump de Object (_ObjectDump)
        if self.running():
            msg = self.__repr__()
            msg += (f'\n    tempo: {self.tempo}'
                    f'\n    beats: {self.beats}'
                    f'\n    seconds: {self.seconds}'
                    f'\n    _beat_dur: {self._beat_dur}'
                    f'\n    _base_seconds: {self._base_seconds}'
                    f'\n    _base_beats: {self._base_beats}')
            print(msg)
        else:
            raise ClockNotRunning(self)

    def next_time_on_grid(self, quant=1, phase=0):
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

    # // logical time to next beat
    def time_to_next_beat(self, quant=1):
        return Quant.as_quant(quant).next_time_on_grid(self) - self.beats

    def beats2bars(self, beats):
        return (beats - self._base_bar_beat) * self._bars_per_beat\
               + self._base_bar

    def bars2beats(self, bars):
        return (bars - self._base_bar) * self._beats_per_bar\
               + self._base_bar_beat

    # // return the current bar.
    def bar(self): # NOTE: bar podría ser propiedad de solo lectura
        return bi.floor(self.beats2bars(self.beats))

    # // given a number of beats, determine number beats at the next bar line.
    def next_bar(self, beat=None):
        if beat is None:
            beat = self.beats
        return self.bars2beats(bi.ceil(self.beats2bars(beat)))

    # // return the beat of the bar, range is 0 to < t.beatsPerBar
    def beat_in_bar(self):
        return self.beats - self.bars2beats(self.bar())

    def running(self):
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
