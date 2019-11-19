"""Clock.sc"""

import logging
import heapq as _heapq
import itertools as _itertools
import threading as _threading
import time as _time
import sys as _sys
import inspect as _inspect
import traceback as _traceback
import math as _math
import types as _types
import weakref as _weakref

from ..base import utils as utl
from ..base import main as _libsc3
from ..base import builtins as bi
from ..base import functions as fn
from ..base import systemactions as sac
from ..base import model as mdl
from . import stream as stm


_logger = logging.getLogger(__name__)


# // Clocks for timing threads.

class TaskQueue():
    """
    This class is an encapsulation of the algorithm found in heapq
    documentation. heapq module in itself use the same principles as
    SuperCollider's clocks implementation. TaskQueue is not thread safe.
    """

    _REMOVED = '<removed-task>'

    def __init__(self):
        self._init()

    def _init(self):
        self._queue = []
        self._entry_finder = {}
        self._counter = _itertools.count()
        self._removed_counter = 0

    def add(self, time, task):
        'Add a new task or update the time of an existing task.'
        if task in self._entry_finder:
            self.remove(task)
        count = next(self._counter)
        entry = [time, count, task]
        self._entry_finder[task] = entry
        _heapq.heappush(self._queue, entry)

    def remove(self, task):
        'Remove an existing task. Raise KeyError if not found.'
        entry = self._entry_finder.pop(task)
        entry[-1] = type(self)._REMOVED
        self._removed_counter += 1

    def pop(self):
        '''Remove and return the lowest time entry as a tuple (time, task).
        Raise KeyError if empty.'''
        while self._queue:
            time, count, task = _heapq.heappop(self._queue)
            if task is not type(self)._REMOVED:
                del self._entry_finder[task]
                return (time, task)
            else:
                self._removed_counter -= 1
        raise KeyError('pop from an empty task queue')

    def peek(self):
        '''Return the lowest time entry as a tuple (time, task) without
        removing it.'''
        for i in range(len(self._queue)):  # Can have <removed-task>s first.
            time, count, task = self._queue[i]
            if task is not type(self)._REMOVED:
                return (time, task)
        raise KeyError('peek from an empty task queue')

    def empty(self):
        'Return True if queue is empty.'
        return (len(self._queue) - self._removed_counter) == 0

    def clear(self):
        'Reset the queue to initial state (remove all tasks).'
        self._init()

    # NOTE: implementar __iter__ y copy()


class Clock():
    @classmethod
    def play(cls, task):
        cls.sched(0, task)

    @classmethod
    def seconds(cls): # seconds es el *tiempo lógico* de cada thread
        return _libsc3.main.current_tt.seconds

    # // tempo clock compatibility
    @classmethod
    def beats(cls):
        return _libsc3.main.current_tt.seconds

    @classmethod
    def beats2secs(cls, beats):
        return beats

    @classmethod
    def secs2beats(cls, secs):
        return secs

    @classmethod
    def beats2bars(cls):
        return 0

    @classmethod
    def bars2beats(cls):
        return 0

    @classmethod
    def time_to_next_beat(cls):
        return 0

    @classmethod
    def next_time_on_grid(cls, quant=1, phase=0):
        if quant == 0:
            return cls.beats() + phase
        if phase < 0:
            phase = bi.mod(phase, quant)
        return bi.roundup(cls.beats() - bi.mod(phase, quant), quant) + phase


class MetaSystemClock(type):
    def __init__(cls, *_):

        def init_func(cls):
            cls._task_queue = TaskQueue()
            cls._sched_cond = _threading.Condition(_libsc3.main._main_lock)
            cls._thread = _threading.Thread(
                target=cls._run,
                name=cls.__name__,
                daemon=True)
            cls._thread.start()
            cls._sched_init()

        utl.ClassLibrary.add(cls, init_func)


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
        cls._resync_cond = _threading.Condition()
        cls._resync_thread = _threading.Thread(
            target=cls._resync_thread_func,
            name=f'{cls.__name__}.resync')
        cls._resync_thread.daemon = True
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
    def _sched_cleanup(cls): # L265
        with cls._resync_cond:
            cls._run_resync = False
            cls._resync_cond.notify()

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
        if isinstance(task, stm.TimeThread):
            task.next_beat = secs
        if cls._task_queue.peek()[0] != prev_time:
            cls._sched_cond.notify_all()  # Call with acquired lock.

    @classmethod
    def _sched_stop(cls):  # Shouldn't be stopped.
        with cls._sched_cond:
            cls._sched_cleanup()
            if cls._run_sched:
                cls._run_sched = False
                cls._sched_cond.notify_all()

    @classmethod
    def sched_clear(cls):  # L387, called by schedClearUnsafe() with gLangMutex
        with cls._sched_cond:
            if cls._run_sched:
                cls._task_queue.clear()
                cls._sched_cond.notify_all()

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
                    if isinstance(task, stm.TimeThread):
                        task.next_beat = None
                    try:
                        _libsc3.main.update_logical_time(sched_time) # NOTE: cada vez que algo es programado se actualiza el tiempo lógico de mainThread al tiempo programado.
                        delta = task.__awake__(sched_time, sched_time, cls)
                        if isinstance(delta, (int, float))\
                        and not isinstance(delta, bool):
                            time = sched_time + delta
                            cls._sched_add(time, task)
                    except stm.StopStream:
                        pass
                    except Exception:
                        _traceback.print_exception(*_sys.exc_info())  # Always recover.

    # sclang methods

    @classmethod
    def clear(cls):
        with cls._sched_cond: # BUG: VER SI USA COND!
            item = None
            # BUG: NO SÉ QUE ESTABA PENSANDO CUANOD HICE ESTE, FALTA:
            # BUG: queue es thisProcess.prSchedulerQueue, VER!
            while not cls._task_queue.empty():
                item = cls._task_queue.pop()[1]
                if isinstance(item, (stm.EventStreamPlayer, stm.PauseStream)):
                    item.removed_from_scheduler()
            cls._sched_cond.notify_all()
            # BUG: llama a prClear, VER!

    @classmethod
    def sched(cls, delta, item):
        if not hasattr(item, '__awake__'):
            item = fn.Function(item)
        with cls._sched_cond:
            seconds = _libsc3.main.current_tt.seconds
            seconds += delta
            if seconds == _math.inf:
                return
            cls._sched_add(seconds, item)

    @classmethod
    def sched_abs(cls, time, item):
        if not hasattr(item, '__awake__'):
            item = fn.Function(item)
        if time == _math.inf:
            return
        with cls._sched_cond:
            cls._sched_add(time, item)

    # L542 y L588 setea las prioridades 'rt' para mac o linux, es un parámetro de los objetos Thread
    # ver qué hace std::move(thread)
    # def sched_run(cls): # L609, crea el thread de SystemClock
    #     # esto es simplemente start (sched_run_func es run) con prioridad rt
    #     # iría en el constructor/inicializador
    #     pass
    # L651, comentario importante sobre qué maneja cada reloj
    # luego ver también las funciones que exporta a sclang al final de todo


class Scheduler():
    def __init__(self, clock, drift=False, recursive=True):
        self._clock = clock
        self._drift = drift
        self.recursive = recursive
        # init
        self._beats = _libsc3.main.current_tt.beats
        self._seconds = 0.0
        # BUG, TODO: PriorityQueue intenta comparar el siguiente valor de la tupla si dos son iguales y falla al querer comparar tasks, hacer que '<' devuelva el id del objeto
        self.queue = TaskQueue()
        self._expired = []

    def _wakeup(self, item):
        try:
            # NOTE: Parece correcto el comportamiento, se debe actualizar en wakeup o en awake, acá los estoy haciendo antes pero el tiempo lógico es el mismo que se le pasa a awake.
            _libsc3.main.update_logical_time(self._seconds) # NOTE: cada vez que algo es programado se actualiza el tiempo lógico de mainThread al tiempo programado.
            delta = item.__awake__(self._beats, self._seconds, self._clock)
            if isinstance(delta, (int, float)) and not isinstance(delta, bool):
                self._sched_add(delta, item)
        except stm.StopStream:
            pass
        except Exception:
            _traceback.print_exception(*_sys.exc_info())

    def play(self, task):
        self.sched(0, task)

    def _sched_add(self, delta, item): # delta no puede ser None
        if self._drift:
            from_time = _libsc3.main.elapsed_time()
        else:
            from_time = self.seconds = _libsc3.main.current_tt.seconds # BUG: SINCORNIZANDO CON CURRENT_THREAD FUNCIONA BIEN (AGREGADO), PERO NO LE VEO SENTIDO.
        self.queue.add(from_time + delta, item)

    def sched(self, delta, item):
        if not hasattr(item, '__awake__'):
            item = fn.Function(item)
        self._sched_add(delta, item)

    def sched_abs(self, time, item):
        self.queue.add(time, item)

    def clear(self):
        item = None
        while not self.queue.empty():
            item = self.queue.pop() # NOTE: vacía la cola sacando las Routine, PauseStream o Function
            if isinstance(item, stm.PauseStream): # NOTE: (PauseStream, stm.EventStreamPlayer)): son los único que definen el método siguiente.
                item.removed_from_scheduler() # NOTE: cambié el orden, en sclang primero se llama a este método y luego se vacía la cola.

    def empty(self): # pythonique
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
        self._seconds = self.queue.peek()[0] # NOTE: usa los atributos por el cierre de wakeup
        if self.recursive:
            while self._seconds <= value: # seconds no puede ser None, sí la primera iteración es igual valor.
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


class MetaAppClock(type):
    def __init__(cls, *_):

        def init_func(cls):
            cls._sched_cond = _threading.Condition(_libsc3.main._main_lock)
            cls._tick_cond = _threading.Condition()
            cls._scheduler = Scheduler(cls, drift=True, recursive=False)
            cls._thread = _threading.Thread(
                target=cls._run,
                name=cls.__name__,
                daemon=True)
            cls._thread.start()

        utl.ClassLibrary.add(cls, init_func)


class AppClock(Clock, metaclass=MetaAppClock):
    def __new__(cls):
        return cls

    @classmethod
    def _run(cls):
        cls._run_sched = True
        seconds = None
        while True:
            with cls._sched_cond:
                seconds = cls.tick()  # First tick for free, returns None
                if isinstance(seconds, (int, float))\
                and not isinstance(seconds, bool):
                    seconds = seconds - cls._scheduler.seconds  # tick returns abstime (elapsed)
                else:
                    seconds = None
            with cls._tick_cond:  # many notify one wait
                cls._tick_cond.wait(seconds)  # if seconds is None waits for notify
            if not cls._run_sched: return

    @classmethod
    def clear(cls):
        cls._scheduler.clear()

    @classmethod
    def sched(cls, delta, item):
        with cls._sched_cond:
            cls._scheduler.sched(delta, item)
        with cls._tick_cond:
            cls._tick_cond.notify() # cls.tick() pasada a run

    @classmethod
    def tick(cls):
        tmp = _libsc3.main.current_tt.clock
        _libsc3.main.current_tt.clock = cls # BUG: supongo que porque puede que scheduler evalue una Routine con play/run? Debe ser para defer. Igual no me cierra del todo, pero también porque sclang tiene un bug con los relojes heredados.
        cls._scheduler.seconds = _libsc3.main.elapsed_time()
        _libsc3.main.current_tt.clock = tmp
        if cls._scheduler.queue.empty():
            return None # BUG: es un valor que se comprueba para saber si client::tick deja de llamarse a sí mismo.
        else:
            return cls._scheduler.queue.peek()[0]

    @classmethod
    def _stop(cls):  # Shouldn't be stopped.
        with cls._tick_cond:
            cls._run_sched = False
            cls._tick_cond.notify()

    # NOTE: Este comentario es un recordatorio.
    # def _sched_notify(cls):
    # _AppClock_SchedNotify
    # En SC_TerminalClient _AppClock_SchedNotify es SC_TerminalClient::prScheduleChanged
    # que llama a la instancia del cliente (de sclang), que llama a su método
    # sendSignal(sig_sched) con la opción sig_sched que llama a SC_TerminalClient::tick
    # Acá podría ir todo dentro de sched(), ergo sum chin pum: cls.tick()


class ClockScheduler(_threading.Thread):
    def __init__(self):
        self._sched_cond = _threading.Condition(_libsc3.main._main_lock)
        self.queue = TaskQueue()
        self.prev_elapsed_time = 0.0 # NOTE: para volver en tiempo atrás en StopStream con el tiempo previo del scheduler (no de la rutina como en rt!), ver abajo.
        _threading.Thread.__init__(self)
        self.daemon = True
        self.start()

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
                    if not self.queue.empty():
                        next_time = self.queue.peek()[0]
                    else:
                        next_time = _math.inf
                    clock_task.run(time, next_time)
                    self._sched_cond.wait()
                    if not self._run_sched:
                        return

    def add(self, time, clock_task):
        with self._sched_cond:
            self.queue.add(time, clock_task)
            self._sched_cond.notify()

    def stop(self):
        with self._sched_cond:
            self._run_sched = False
            self._sched_cond.notify()


class ClockTask():
    def __init__(self, beats, clock, task, scheduler):
        self.clock = clock
        self.task = task
        self.scheduler = scheduler
        if scheduler.is_alive():
            scheduler.add(clock.beats2secs(beats), self)
        else:
            RuntimeError('ClockScheduler is not running')

    def run(self, time, next_time): # NOTE: se llama desde el loop de scheduler
        with self.clock._sched_cond:
            self.time = time
            self.next_time = next_time
            self.clock._clock_task = self
            self.clock._sched_cond.notify()

    def wakeup(self): # NOTE: se llama desde el loop de clock, con el lock
        try:
            _libsc3.main.update_logical_time(self.time)
            delta = self.task.__awake__(self.clock.secs2beats(self.time),
                                        self.time, self.clock)
            if isinstance(delta, (int, float)) and not isinstance(delta, bool):
                self.scheduler.prev_elapsed_time = self.time # NOTE: tiene que ir acá, si la rutina devuelve una valor que no hace avanzar el tiempo (p.e. 'hang') no cambia el tiempo previo.
                self.time = self.time + self.clock.beats2secs(delta)
                self.scheduler.add(self.time, self)
        except stm.StopStream:
            _libsc3.main.update_logical_time(self.scheduler.prev_elapsed_time) # NOTE: No es el tiempo de la rutina sino del scheduler en este caso, prev_time podía ser el tiempo previo de otra rutina!
        except Exception:
            _traceback.print_exception(*_sys.exc_info())

    def notify_scheduler(self):
        with self.scheduler._sched_cond:
            self.scheduler._sched_cond.notify()


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
            msg = f'unsuported type convertion to Quant: {type(quant)}'
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
            self.quant,
            (self.phase or 0) - (self.timing_offset or 0)
        )

    # printOn
    # storeArgs


# /*
# You should only change the tempo 'now'. You can't set the tempo at some beat
# in the future or past, even though you might think so from the methods.
#
# There are several ideas of now:
# 	elapsed time, i.e. "real time"
# 	logical time in the current time base.
# 	logical time in another time base.
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


class MetaTempoClock(type):
    def __init__(cls, *_):
        cls._all = _weakref.WeakSet()

        def init_func(cls):
            cls.default = cls()
            cls.default.permanent = True
            sac.CmdPeriod.add(cls)

        utl.ClassLibrary.add(cls, init_func)

    @property
    def all(cls):
        return set(cls._all)


class TempoClock(Clock, metaclass=MetaTempoClock):
    @classmethod
    def cmd_period(cls):
        for clock in cls.all:
            clock.clear(False)
            if not clock.permanent:
                clock.stop()

    # BUG: C++ TempoClock_stopAll se usa en ./lang/LangSource/PyrLexer.cpp
    # BUG: shutdownLibrary(), no importa si hay permanentes, va para Main, VER.

    # BUG: A LOS TEMPOCLOCK SE LOS TIENE QUE PODER LLEVAR EL COLECTOR DE BASURA LLAMANDO A STOP().

    def __init__(self, tempo=None, beats=None, seconds=None):
        # prTempoClock_New
        tempo = tempo or 1.0
        if tempo < 0.0:
            raise ValueError(f'invalid tempo {tempo}')
        beats = beats or 0.0
        if _libsc3.main.mode == _libsc3.main.RT:
            if seconds is None:
                seconds = _libsc3.main.current_tt.seconds # *** BUG: revisar, puede estar mal, en los test nrt no funciona.
        else:
            seconds = 0.0 # *** BUG: NO ENTIENDO SI ESTO ESTÁ ES ASÍ PARA NRT POR QUÉ FUNCIONA EN RT (SI ES QUE FUNCIONA).

        # TempoClock::TempoClock()
        self._tempo = tempo
        self._beat_dur = 1.0 / tempo
        self._base_seconds = seconds
        self._base_beats = beats
        self._beats = 0.0 # NOTE: Se necesita inicializado para prev_beat (el tiempo previo de la rutina en caso de StopIteration)

        # init luego de prStart
        self._beats_per_bar = 4.0
        self._bars_per_beat = 0.25
        self._base_bar_beat = 0
        self._base_bar = 0.0
        self.permanent = False
        type(self)._all.add(self)

        if _libsc3.main.mode == _libsc3.main.RT:
            self._task_queue = TaskQueue()
        else:
            self._clock_task = None
        self._sched_cond = _threading.Condition(_libsc3.main._main_lock)

        self._thread = _threading.Thread(
            target=self._run,
            name=f'{type(self).__name__} id: {id(self)}',
            daemon=True)
        self._thread.start()

    def _run(self):
        with self._sched_cond:
            if _libsc3.main.mode == _libsc3.main.RT:
                self._rt_run()
            else:
                self._nrt_run()

    def _nrt_run(self):
        self._run_sched = True

        while True:
            while self._clock_task is None:
                self._sched_cond.wait()
                if not self._run_sched:
                    return
            self._clock_task.wakeup()
            self._clock_task.notify_scheduler() # NOTE: Siempre noficia, aunque no reprograme.
            self._sched_cond.wait()
            if not self._run_sched:
                return

    def _rt_run(self):
        self._run_sched = True

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
                # I leave previous code commented for now (this should be the same).
                # sched_point = _libsc3.main._time_of_initialization + sched_secs
                # self._sched_cond.wait(sched_point - _time.time())
                self._sched_cond.wait(sched_secs - _libsc3.main.elapsed_time())
                if not self._run_sched:
                    return

            # // perform all events that are ready
            while not self._task_queue.empty()\
            and elapsed_beats >= self._task_queue.peek()[0]:
                item = self._task_queue.pop()
                prev_beat = self._beats
                self._beats = item[0] # NOTE: setea mBeats, la propiedad de la clase, SystemClock usa la variable sched_time
                task = item[1]
                if isinstance(task, stm.TimeThread):
                    task.next_beat = None
                try:
                    _libsc3.main.update_logical_time(
                        self.beats2secs(self._beats)) # NOTE: cada vez que algo es programado se actualiza el tiempo lógico de mainThread al tiempo programado.
                    # runAwakeMessage NOTE: que se llama con la preparación previa de la pila del intérprete
                    delta = task.__awake__(self._beats,
                                           self.beats2secs(self._beats),
                                           self)
                    if isinstance(delta, (int, float))\
                    and not isinstance(delta, bool):
                        time = self._beats + delta
                        self._sched_add(time, task)
                except stm.StopStream:
                    _libsc3.main.update_logical_time(
                        self.beats2secs(prev_beat))
                except Exception:
                    _traceback.print_exception(*_sys.exc_info())

    def stop(self):
        # prStop -> prTempoClock_Free -> StopReq -> StopAndDelete -> Stop
        # prTempoClock_Free
        if self._thread is None or not self._thread.is_alive():
            _logger.debug(f'{self} is not running')
            return

        # StopAndDelete
        def stop_func(clock):
            # Stop
            with clock._sched_cond: # lock_guard
                clock._run_sched = False # NOTE: son daemon y se liberan solas cuando terminan sin join.
                type(clock)._all.remove(clock)
                clock._sched_cond.notify_all() # NOTE: en TempoClock::Stop, es notify_all
            # *** BUG: No estoy seguro de si en C++ notify_all notifica a todas
            # *** BUG: las condiciones sobre el mismo lock. En Python no funciona
            # *** BUG: así y clock._sched_cond trabaja sobre un solo hilo.
            # *** BUG: Pero también puede ser que notifique varias veces a
            # *** BUG: la misma condición por los distintos wait? Desconocimiento.
            clock._thread = None
            clock._sched_cond = None

        # StopReq
        stop_thread = _threading.Thread(
            target=stop_func,
            args=(self,),
            name=f'{type(self).__name__}.stop_thread id: {id(self)}',
            daemon=True)
        stop_thread.start()

    # def __del__(self):
    #     # BUG: self needs to be stoped to be gc collected because is in
    #     # BUG: cyclic reference with target=_run.
    #     self.stop()

    def play(self, task, quant=1):
        quant = Quant.as_quant(quant)
        self.sched_abs(quant.next_time_on_grid(self), task)

    def play_next_bar(self, task):
        self.sched_abs(self.next_bar(), task)

    @property
    def tempo(self):
        # _TempoClock_Tempo
        if not self._thread.is_alive():
            raise RuntimeError(f'{self} is not running')
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
        if not self._thread.is_alive():
            raise RuntimeError(f'{self} is not running')
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
        self._beat_dur = 1.0 / value
        with self._sched_cond:
            self._sched_cond.notify() # NOTE: es notify_one en C++
        # en tempo_
        mdl.NotificationCenter.notify(self, 'tempo')

    # // for setting the tempo at the current elapsed time.
    def etempo(self, value):
        # TODO: this.setTempoAtSec(newTempo, Main.elapsedTime);
        # _TempoClock_SetTempoAtTime
        if not self._thread.is_alive():
            raise RuntimeError(f'{self} is not running')
        # TempoClock::SetTempoAtTime
        seconds = _libsc3.main.elapsed_time()
        self._base_beats = self.secs2beats(seconds)
        self._base_seconds = seconds
        self._tempo = value
        self._beat_dur = 1 / value
        with self._sched_cond:
            self._sched_cond.notify() # NOTE: es notify_one en C++
        # etempo_
        mdl.NotificationCenter.notify(self, 'tempo')

    def beat_dur(self):
        # _TempoClock_BeatDur
        if not self._thread.is_alive():
            raise RuntimeError(f'{self} is not running')
        return self._beat_dur

    def elapsed_beats(self):
        # _TempoClock_ElapsedBeats
        if not self._thread.is_alive():
            raise RuntimeError(f'{self} is not running')
        return self.secs2beats(_libsc3.main.elapsed_time())

    @property
    def beats(self):
        # _TempoClock_Beats
        # // returns the appropriate beats for this clock from any thread
        if not self._thread.is_alive():
            raise RuntimeError(f'{self} is not running')
        if _libsc3.main.current_tt.clock is self:
            return _libsc3.main.current_tt.beats
        else:
            return self.secs2beats(_libsc3.main.current_tt.seconds)

    @beats.setter
    def beats(self, value):
        # _TempoClock_SetBeats
        if not self._thread.is_alive():
            raise RuntimeError(f'{self} is not running')
        with self._sched_cond:
            seconds = _libsc3.main.current_tt.seconds # BUG: revisar en C++ las veces que obtiene beats o seconds de &g->thread que es current_tt
            # TempoClock::SetAll # NOTE: _TempoClock_SetAll no se usa en sclang, creo que no están bien nombrasdos SetAll (para setea beats), SetTempoAtTime (para setea etempo) y SetTempoAtBeat (para setear tempo)
            self._base_seconds = seconds
            self._base_beats = value
            #self._tempo = self._tempo # NOTE: la llamada a SetAll es clock->SetAll(clock->mTempo, beats, seconds)
            self._beat_dur = 1.0 / self._tempo
            with self._sched_cond:
                self._sched_cond.notify() # NOTE: es notify_one en C++

    @property
    def seconds(self): # NOTE: definido solo como getter es thisThread.seconds, en TimeThread es property, acá también por consistencia?
        return _libsc3.main.current_tt.seconds

    def _sched_add(self, beats, task):
        # TempoClock::Add
        if _libsc3.main.mode == _libsc3.main.RT:
            if self._task_queue.empty():
                prev_beat = -1e10
            else:
                prev_beat = self._task_queue.peek()[0]
            self._task_queue.add(beats, task)
            if isinstance(task, stm.TimeThread):
                task.next_beat = beats
            if self._task_queue.peek()[0] != prev_beat:
                self._sched_cond.notify()
        else:
            if isinstance(task, stm.TimeThread):
                task.next_beat = beats
            ClockTask(beats, self, task, _libsc3.main._clock_scheduler)

    def sched(self, delta, item):
        # _TempoClock_Sched
        if not self._thread.is_alive():
            raise RuntimeError(f'{self} is not running')
        if not hasattr(item, '__awake__'):
            item = fn.Function(item)
        with self._sched_cond:
            if _libsc3.main.current_tt.clock is self:
                beats = _libsc3.main.current_tt.beats
            else:
                seconds = _libsc3.main.current_tt.seconds
                beats = self.secs2beats(seconds)
            beats += delta
            if beats == _math.inf:
                return
            self._sched_add(beats, item)

    def sched_abs(self, beat, item):
        # _TempoClock_SchedAbs
        if not self._thread.is_alive():
            raise RuntimeError(f'{self} is not running')
        if not hasattr(item, '__awake__'):
            item = fn.Function(item)
        if beat == _math.inf:
            return
        with self._sched_cond:
            self._sched_add(beat, item)

    def clear(self, release_nodes=True):
        # // flag tells EventStreamPlayers that CmdPeriod
        # // is removing them, so nodes are already freed
        # clear -> prClear -> _TempoClock_Clear -> TempoClock::Clear
        if self._thread.is_alive() and self._run_sched:
            item = None
            with self._sched_cond:
                while not self._task_queue.empty():
                    item = self._task_queue.get()[1] # de por sí PriorityQueue es thread safe, la implementación de SuperCollider es distinta, ver SystemClock*clear.
                    if isinstance(item, (stm.EventStreamPlayer, stm.PauseStream)):
                        item.removed_from_scheduler(release_nodes)
                self._sched_cond.notify() # NOTE: es notify_one en C++

    @property
    def beats_per_bar(self):
        return self._beats_per_bar

    @beats_per_bar.setter
    def beats_per_bar(self, value):
        if _libsc3.main.current_tt is not self:
            RuntimeError('should only change beats_per_bar'
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
        if not self._thread.is_alive():
            raise RuntimeError(f'{self} is not running')
        return (beats - self._base_beats) * self._beat_dur + self._base_seconds

    def secs2beats(self, seconds):
        # _TempoClock_SecsToBeats
        if not self._thread.is_alive():
            raise RuntimeError(f'{self} is not running')
        return (seconds - self._base_seconds) * self._tempo + self._base_beats

    def dump(self):
        # _(pr)TempoClock_Dump -> TepmoClock::Dump
        # BUG: Pero no usa este método sclang, usa dump de Object (_ObjectDump)
        if self._thread.is_alive():
            msg = self.__repr__()
            msg += (f'\n    tempo: {self.tempo}'
                    f'\n    beats: {self.beats}'
                    f'\n    seconds: {self.seconds}'
                    f'\n    _beat_dur: {self._beat_dur}'
                    f'\n    _base_seconds: {self._base_seconds}'
                    f'\n    _base_beats: {self._base_beats}')
            print(msg)
        else:
            raise RuntimeError(f'{self} is not running')

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
    def time_to_next_beat(self, quant=1.0):
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
    def next_bar(self, beat):
        beat = beat or self.beats
        return self.bars2beats(bi.ceil(self.beats2bars(beat)))

    # // return the beat of the bar, range is 0 to < t.beatsPerBar
    def beat_in_bar(self):
        return self.beats - self.bars2beats(self.bar())

    def running(self):
        return self._thread is not None and self._thread.is_alive()


def defer(item, delta=None):
    if callable(item):
        def df():
            item()  # Wrapped because lambda always return its expression value.
    else:
        raise TypeError('item is not callable')
    AppClock.sched(delta or 0, df)
