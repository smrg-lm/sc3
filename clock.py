"""Clock.sc"""

import threading as _threading
import time as _time
import sys as _sys
import inspect as _inspect
import traceback as _traceback
import math as _math
from queue import PriorityQueue as _PriorityQueue
from queue import Full as _Full

#import sched tal vez sirva para AppClock (ver scd)
#Event = collections.namedtuple('Event', []) podría servir pero no se pueden agregar campos dinámicamente, creo, VER

from . import main as _main
from . import thread as thr
import supercollie.builtins as bi
import supercollie.utils as ut


# // clocks for timing threads.

class Clock(_threading.Thread): # ver std::copy y std::bind
    # def __new__(cls): # BUG: necesito hacer super().__new__(cls) para SystemClock... ver cómo es esto en Python.
    #     raise NotImplementedError('Clock is an abstract class')

    @classmethod
    def play(cls, task):
        cls.sched(0, task)
    @classmethod
    def seconds(cls): # seconds es el tiempo lógico de cada thread
        return _main.Main.current_TimeThread.seconds # BUG: no me quedan claras las explicaciones dispersas en al documentación Process, Thread, Clock(s)

    # // tempo clock compatibility
    @classmethod
    def beats(cls):
        return _main.Main.current_TimeThread.seconds
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


# TODO: Usar init class para hacer singletons
class SystemClock(Clock): # TODO: creo que esta sí podría ser una ABC singletona
    _SECONDS_FROM_1900_TO_1970 = 2208988800 # (int32)UL # 17 leap years
    _NANOS_TO_OSC = 4.294967296 # PyrSched.h: const double kNanosToOSC  = 4.294967296; // pow(2,32)/1e9
    _MICROS_TO_OSC = 4294.967296 # PyrSched.h: const double kMicrosToOSC = 4294.967296; // pow(2,32)/1e6
    _SECONDS_TO_OSC = 4294967296. # PyrSched.h: const double kSecondsToOSC  = 4294967296.; // pow(2,32)/1
    _OSC_TO_NANOS = 0.2328306436538696# PyrSched.h: const double kOSCtoNanos  = 0.2328306436538696; // 1e9/pow(2,32)
    _OSC_TO_SECONDS =  2.328306436538696e-10 # PyrSched.h: const double kOSCtoSecs = 2.328306436538696e-10;  // 1/pow(2,32)

    _instance = None # singleton instance

    def __new__(cls):
        #_host_osc_offset = 0 # int64
        #_host_start_nanos = 0 # int64
        #_elapsed_osc_offset = 0 # int64
        #_rsync_thread # syncOSCOffsetWithTimeOfDay resyncThread
        #_time_of_initialization # original es std::chrono::high_resolution_clock::time_point
        #monotonic_clock es _time.monotonic()? usa el de mayor resolución
        #def dur_to_float, ver
        #_run_sched # gRunSched es condición para el loop de run
        if cls._instance is None:
            obj = super().__new__(cls)
            _threading.Thread.__init__(obj)
            # BUG, TODO: PriorityQueue intenta comparar el siguiente valor de la tupla si dos son iguales y falla al querer comparar tasks, hacer que '<' devuelva el id del objeto
            obj._task_queue = _PriorityQueue()
            obj._sched_cond = _main.Main._main_lock
            obj.start()
            obj._sched_init()
            cls._instance = obj
            return obj
        else:
            raise Exception('there is one SystemClock instance already') # BUG: sclang devuelve otras instancias lo que es confuso, no tiene sentido

    def _sched_init(self): # L253 inicia los atributos e.g. _time_of_initialization
        #time.gmtime(0).tm_year # must be unix time
        self._time_of_initialization = _time.time()
        self._host_osc_offset = 0 # int64

        self._sync_osc_offset_with_tod()
        self._host_start_nanos = int(self._time_of_initialization / 1e9) # time.time_ns() -> int v3.7
        self._elapsed_osc_offset = int(
            self._host_start_nanos * SystemClock._NANOS_TO_OSC) + self._host_osc_offset

        #print('SystemClock _sched_init fork thread')

        # same every 20 secs
        self._resync_cond = _threading.Condition() # VER, aunque el uso es muy simple (gResyncThreadSemaphore)
        self._run_resync = False # test es true en el loop igual que la otra
        self._resync_thread = _threading.Thread( # AUNQUE NO INICIA EL THREAD EN ESTA FUNCIÓN
            target=self._resync_thread_func, daemon=True)
        self._resync_thread.start()

    def _sync_osc_offset_with_tod(self): # L314, esto se hace en _rsync_thread
    	# Original comment:
        # generate a value gHostOSCoffset such that
    	# (gHostOSCoffset + systemTimeInOSCunits)
    	# is equal to gettimeofday time in OSCunits.
    	# Then if this machine is synced via NTP, we are synced with the world.
    	# more accurate way to do this??
        number_of_tries = 1
        diff = 0 # int64
        min_diff = 0x7fffFFFFffffFFFF; # int64, a big number to miss
        new_offset = self._host_osc_offset

        for i in range(0, number_of_tries):
            system_time_before = _time.perf_counter()
            time_of_day = _time.time()
            system_time_after = _time.perf_counter()

            system_time_before = int(system_time_before / 1e6) # to usecs
            system_time_after = int(system_time_after / 1e6)
            diff = system_time_after - system_time_before

            if diff < min_diff:
                min_diff = diff

                system_time_between = system_time_before + diff // 2
                system_time_in_osc_units = int(
                    system_time_between * SystemClock._NANOS_TO_OSC)
                time_of_day_in_osc_units = (int(
                    time_of_day + SystemClock._SECONDS_FROM_1900_TO_1970) << 32) + int(time_of_day / 1e6 * SystemClock._MICROS_TO_OSC)

                new_offset = time_of_day_in_osc_units - system_time_in_osc_units
        # end for
        self._host_osc_offset = new_offset
        #print('new offset:', self._host_osc_offset)

    def _resync_thread_func(self): # L408, es la función de _rsync_thread
        self._run_resync = True
        while self._run_resync:
            with self._resync_cond:
                self._resync_cond.wait(20)
            if not self._run_resync: return

            self._sync_osc_offset_with_tod()
            self._elapsed_osc_offset = int(
                self._host_start_nanos * SystemClock._NANOS_TO_OSC) + self._host_osc_offset

    def _sched_cleanup(self): # L265 es para rsync_thread join, la exporta como interfaz, pero no sé si no está mal llamada 'sched'
        with self._resync_cond:
            self._run_resync = False
            self._resync_cond.notify() # tiene que interrumpir el wait
        self._resync_thread.join()

    # PASADAS A PROCESS, van ahí
    # ver si estas funciones no serían globales y cuales no usa en esta clase, ver PyrSched.h
    # def elapsed_time(self) -> float: # devuelve el tiempo del reloj de mayor precisión menos _time_of_initialization
    #     return _time.time() - self._time_of_initialization
    # def monotonic_clock_time(self) -> float: # monotonic_clock::now().time_since_epoch(), no sé dónde usa esto
    #     return _time.monotonic() # en linux es hdclock es time.perf_counter(), no se usa la variable que declara

    # se llama en OSCData.cpp makeSynthBundle y otras funciones de PyrSched.cpp
    def elapsed_time_to_osc(self, elapsed: float) -> int: # retorna int64
        return int(elapsed * SystemClock._SECONDS_TO_OSC) + self._elapsed_osc_offset

    # se llama en OSCData.cpp también en funciones relacionadas a bundles/osc
    def osc_to_elapsed_time(self, osctime: int) -> float: # L286
        return float(osctime - self._elapsed_osc_offset) * SystemClock._OSC_TO_SECONDS

    # se llama en las funciones de los servidores a bajo nivel
    def osc_time(self) -> int: # L309, devuleve elapsed_time_to_osc(elapsed_time())
        return self.elapsed_time_to_osc(self.elapsed_time())

    def _sched_add(self, secs, task): # L353
        item = (secs, task)
        if self._task_queue.empty():
            prev_time = -1e10
        else:
            prev_time = self._task_queue.queue[0][0]
        # BUG, TODO: PriorityQueue intenta comparar el siguiente valor de la tupla si dos son iguales y falla al querer comparar tasks, hacer que '<' devuelva el id del objeto
        self._task_queue.put(item) #, block=False) Full exception, put de PriorityQueue es infinita por defecto, pero put(block=False) solo agrega si hay espacio libre inmediatamente o tira Full.
        self._task_queue.task_done() # se puede llamar concurrentemente o con _sched_cond ya está?
        if isinstance(task, thr.TimeThread):
            task.next_beat = secs
        if self._task_queue.queue[0][0] != prev_time:
            with self._sched_cond:
                #print('_sched_add llama a notify_all')
                self._sched_cond.notify_all()

    # TODO: se llama en PyrLexer shutdownLibrary
    def sched_stop(self):
        # usa gLangMutex locks
        with self._sched_cond:
            if self._run_sched:
                self._run_sched = False
                self._sched_cond.notify_all()
        self.join() # VER esto, la función sched_stop se llama desde otro hilo y es sincrónica allí
        # tal vez debería juntar con _resync_thread

    # TODO: se declara como sclang export en SCBase.h pero no se usa en ninguna parte
    def sched_clear(self): # L387, llama a schedClearUnsafe() con gLangMutex locks, esta función la exporta con SCLANG_DLLEXPORT_C
        with self._sched_cond:
            if _self._run_sched:
                del self._task_queue # BUG: en realidad tiene un tamaño que reusa y no borra, pero no sé dónde se usa esta función, desde sclang usa *clear
                self._task_queue = _PriorityQueue()
                self._sched_cond.notify_all()

    #def sched_run_func(self): # L422, es la función de este hilo, es una función estática, es run acá (salvo que no subclasee)
    def run(self):
        self._run_sched = True
        now = sched_secs = sched_point = None
        item = sched_time = task = delta = None

        while True:
            # // wait until there is something in scheduler
            while self._task_queue.empty():
                with self._sched_cond:
                    #print('clock empty wait')
                    self._sched_cond.wait() # BUG: es Main._main_lock, tal vez asignar al crear el reloj
                if not self._run_sched: return

            # // wait until an event is ready
            now = 0
            while not self._task_queue.empty():
                now = _time.time()
                sched_secs = self._task_queue.queue[0][0]
                sched_point = self._time_of_initialization + sched_secs # sched_secs (el retorno del generador) se tiene que setear desde afuera con + elapsed_time()
                #print('now: {}, sched_point: {}'.format(now, sched_point))
                if now > sched_point: break # va directo al loop siguiente
                with self._sched_cond:
                    #print('clock no empty wait sched_secs:', sched_secs)
                    self._sched_cond.wait(sched_point - now) # (sched_secs) # sclang usa wait until que espera en tiempo absoluto y no deltas, Python no tiene esa funcion que yo sepa # ver por qué usa wait_until en c++ que usa tod (probable drift)
                if not self._run_sched: return

            # // perform all events that are ready
            while not self._task_queue.empty()\
            and now >= self._time_of_initialization + self._task_queue.queue[0][0]:
                item = self._task_queue.get()
                sched_time = item[0]
                task = item[1]
                if isinstance(task, thr.TimeThread): # BUG: esto lo hace para todas las Routines o solo TimeThread? la implementación puede ser distinta acá...
                    task.next_beat = None
                try:
                    try:
                        # BUG: VER: es next estilo sclang y qué pasa cuando se programan otros objetos
                        # BUG: interesante que se puede SystemClock.sched(0, 0) para clavar sclang
                        # BUG: Entiendo que la llamada a next se produce en este mismo hilo, no veo que
                        # Interpret tenga un lock. Ver si esto salva de que se ejecuten cambios
                        # entre hilos usando distintos relojes. También está loa posibilidad de implementar
                        # esta parte en el hilo de TimeThread enviando la función a una cola y esta
                        # lógica al loop de allá, sería mejor de por sí? todo corre en el mismo
                        # procesador, pero los hilos se pueden interrumpir en el medio?
                        # TODO: Reproducir test_concurrente.scd cuando implemente TempoClock,
                        # y puede que usando una cola en otro proceso afecte menos el timming,
                        # el único problema en realidad es no crashear el intérprete Python, entonces:
                        # NOTE: Ahora pienso, si el código de las rutinas que se programan en distintos
                        # relojes se corren distintos hilos del os se puede considerar que es
                        # responsabilidad del músico-programador coordinar su ejecución y no del
                        # lenguaje/librería. Igualmente, proveer un mecanismo que facilite
                        # las cosas sin tener que acceder a constructos de programación demasiado
                        # alejados del dominio musical puede ser más productivo para el usuario
                        # común, siempre está ese tire y afloje. Reveer el módulo threading nativo
                        # y pensar en mainThread como el punto de ingreso de la librería, será quién
                        # llama a tick. Luego osc/midi y otras cosas tal vez puedan correr en otros hilos
                        # aunque en sclang no estoy seguro de cómo se maneja eso.
                        #delta = task.next()
                        delta = getattr(task, 'next', task)() # routine y callable
                        if isinstance(delta, (int, float)) and not isinstance(delta, bool):
                            time = sched_time + delta # BUG, TODO: sclang usa wait until que espera en tiempo absoluto y no en offset como acá, no hay esa función en Python
                            self._sched_add(time, task)
                    except StopIteration as e:
                        # BUG: ver los anidamietnos válidos...
                        if len(_inspect.trace()) > 1: # Volvió a 1 porque Routine devuelve None ahora.
                            raise e
                except Exception:
                    _traceback.print_exception(*_sys.exc_info()) # hay que poder recuperar el loop ante cualquier otra excepción

    # sclang methods

    @classmethod
    def clear(cls): # la diferencia con sched_clear es que aquel libera y crea un nuevo objeto # método de SystemClock en sclang, llama a schedClearUnsafe() mediante prClear/_SystemClock_Clear después de vaciar la cola prSchedulerQueue que es &g->process->sysSchedulerQueue
        with cls._instance._sched_cond: # BUG: VER SI USA COND!
            item = None
            # BUG: NO SÉ QUE ESTABA PENSANDO CUANOD HICE ESTE, FALTA:
            # BUG: queue es thisProcess.prSchedulerQueue, VER!
            while not cls._instance._task_queue.empty():
                item = cls._instance._task_queue.get()[1] # de por sí PriorityQueue es thread safe, la implementación de SuperCollider es distinta
                if isinstance(item, (xxx.EventStreamPlayer, xxx.PauseStream)):
                    item.removed_from_scheduler()
            cls._instance._sched_cond.notify_all()
            # BUG: llama a prClear, VER!

    @classmethod
    def sched(cls, delta, item): # Process.elapsedTime es el tiempo físico (desde que se inició la aplicación), que también es elapsedTime de SystemClock (elapsed_time acá) [Process.elapsedTime, SystemClock.seconds, thisThread.seconds] thisThread sería mainThread si se llama desde fuera de una rutina, thisThread.clock === SystemClock, es la clase singleton
        # BUG: Los segundos de Thread en sclang avanzan constantemente, no encuentro cómo está definido eso
        # BUG: En Routine se queda con los valores de inicialización en __init__
        # BUG: El problema es que no funicona para SystemClock que usa main_TimeThread
        # BUG: y si tiene un tiempo que no es el actual los eventos se atoran.
        seconds = _main.Main.current_TimeThread.seconds
        seconds += delta
        if seconds == _math.inf: return # // return nil OK, just don't schedule
        with cls._instance._sched_cond:
            cls._instance._sched_add(seconds, item)

    @classmethod
    def sched_abs(cls, time, item):
        if time == _math.inf:
            msg = "sched_abs won't schedule {} to infinity"
            raise Exception(msg.format(item)) # BUG: para test, sclang no programa el evento y ya
        with cls._instance._sched_cond:
            cls._instance._sched_add(time, item)

    # L542 y L588 setea las prioridades 'rt' para mac o linux, es un parámetro de los objetos Thread
    # ver qué hace std::move(thread)
    # def sched_run(self): # L609, crea el thread de SystemClock
    #     # esto es simplemente start (sched_run_func es run) con prioridad rt
    #     # iría en el constructor/inicializador
    #     pass
    # L651, comentario importante sobre qué maneja cada reloj
    # luego ver también las funciones que exporta a sclang al final de todo


class TempoClock(Clock): # se crean desde SystemClock?
    pass


class Scheduler():
    def __init__(self, clock, drift=False, recursive=True):
        self._clock = clock
        self._drift = drift
        self.recursive = recursive
        # init
        self._beats = _main.Main.current_TimeThread.beats
        self._seconds = 0.0
        # BUG, TODO: PriorityQueue intenta comparar el siguiente valor de la tupla si dos son iguales y falla al querer comparar tasks, hacer que '<' devuelva el id del objeto
        self.queue = PriorityQueue()
        self._expired = []
        def wakeup(item):
            try:
                delta = item.awake(self._beats, self._seconds, self._clock) # BUG: awake la implementan Function, Nil, Object, PauseStream y Routine,
                if isinstance(delta, (int, float))\
                and not isinstance(delta, bool):
                    self.sched(delta, item) # BUG: ver awake
            except Exception:
                _traceback.print_exception(*_sys.exc_info())
        self._wakeup = wakeup

    def play(self, task):
        self.sched(0, task)

    def sched(self, delta, item): # delta no puede ser None
        if self._drift:
            from_time = _main.Main.elapsed_time()
        else:
            from_time = self.seconds
        self._queue.put((from_time + delta, item))

    def sched_abs(self, time, item):
        self._queue.put((time, item))
        #self._queue.task_done() # es una anotación por si es útil luego

    def clear(self):
        item = None
        while not self._queue.empty():
            item = self._queue.get()
            if isinstance(item, (xxx.EventStreamPlayer, xxx.PauseStream)):
                item.removed_from_scheduler() # NOTE: cambié el orden, en sclang primero se llama a este método y luego se vacía la cola.

    def empty(self): # pythonique
        return self._queue.empty()

    def advance(self, delta):
        self.seconds = self.seconds + delta

    @property
    def seconds(self):
        return self._seconds
    @seconds.setter
    def seconds(self, value):
        self._seconds = self._queue.queue[0][0] # topPriority(), usa los atributos por el cierre de wakeup
        if self.recursive:
            while self._seconds <= value: # seconds no puede ser None, sí la primera iteración es igual valor.
                self._beats = self._clock.secs2beats(self._seconds)
                self._wakeup(self._queue.get())
                if self._queue.empty():
                    break
                else:
                    self._seconds = self._queue.queue[0][0]
        else:
            # // First pop all the expired items and only then wake
            # // them up, in order for control to return to the caller
            # // before any tasks scheduled as a result of this call are
            # // awaken.
            while self._seconds <= value:
                self._expired.append(self._seconds)
                self._expired.append(self._queue.get())
                if self._queue.empty():
                    break
                else:
                    self._seconds = self._queue.queue[0][0]
            for time, item in ut.gen_cclumps(self._expired):
                self._seconds = time
                self._beats = self._clock.secs2beats(self._seconds)
                self._wakeup(self._queue.get())
            self._expired.clear()
        self._seconds = value
        self._beats = self._clock.secs2beats(value)

@ut.initclass
class AppClock(Clock): # ?
    def __init_class__(cls):
        cls._scheduler = Scheduler(cls, drift=True, recursive=False)

    @classmethod
    def clear(cls):
        cls._scheduler.clear()

    @classmethod
    def sched(cls, delta, item):
        cls._scheduler.sched(delta, item):
        cls._sched_notify()

    @classmethod
    def tick(cls):
        tmp = _main.Main.current_TimeThread.clock
        _main.Main.current_TimeThread.clock = cls # BUG: supongo que porque puede que scheduler evalue una Routine con play/run? Igual no me cierra del todo, pero también porque sclang tiene un bug con los relojes heredados.
        cls._scheduler.seconds = _main.Main.elapsed_time()
        _main.Main.current_TimeThread.clock = tmp
        return cls._scheduler.queue.queue[0][0] # topPriority()

    @classmethod
    def _sched_notify(cls):
        # _AppClock_SchedNotify
        # En PyrPrimitive.cpp -> prAppClockSchedNotify
        # // NOTE: the _AppClock_SchedNotify primitive shall be redefined by language clients
        # // if they wish to respond to AppClock scheduling notifications
        # return errNone;
        return NotImplemented # BUG: pero el mecanismo tampoco está implementado acá porque creo que llama en terminal_client, por ejemplo, hay que ver dónde se llama a tick


class NRTClock(Clock):
    # Los patterns temporales tienen que generar una rutina que
    # corra en el mismo reloj. El probleam es que el tiempo no
    # avanza si no se llama a yield/wait. El reloj de Jonathan
    # captura la cola y usa un servidor dummy, pero si el pattern
    # usa el reloj en 'tiempo real' eso no queda registrado.
    # Además, en nrt todas las acciones son sincrónicas.
    pass
