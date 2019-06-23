"""Clock.sc"""

import threading as _threading
import time as _time
import sys as _sys
import inspect as _inspect
import traceback as _traceback
import math as _math
from queue import PriorityQueue as _PriorityQueue
import types as _types

#import sched tal vez sirva para AppClock (ver scd)
#Event = collections.namedtuple('Event', []) podría servir pero no se pueden agregar campos dinámicamente, creo, VER

from . import utils as utl
from . import main as _main
from . import builtins as bi
from . import stream as stm
from . import systemactions as sac
from . import model as mdl


# // clocks for timing threads.

class Clock(_threading.Thread): # ver std::copy y std::bind
    # def __new__(cls): # BUG: necesito hacer super().__new__(cls) para SystemClock... ver cómo es esto en Python.
    #     raise NotImplementedError('Clock is an abstract class')

    @classmethod
    def play(cls, task):
        cls.sched(0, task)
    @classmethod
    def seconds(cls): # seconds es el *tiempo lógico* de cada thread
        if _main.Main.current_TimeThread is _main.Main.main_TimeThread:
            _main.Main.update_logical_time() # NOTE: Esto actualiza cada vez que SystemClock y AppClock se consultan fuera de una Routine.
        return _main.Main.current_TimeThread.seconds

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


@utl.initclass
class SystemClock(Clock): # TODO: creo que esta sí podría ser una ABC singletona
    _SECONDS_FROM_1900_TO_1970 = 2208988800 # (int32)UL # 17 leap years
    _NANOS_TO_OSC = 4.294967296 # PyrSched.h: const double kNanosToOSC  = 4.294967296; // pow(2,32)/1e9
    _MICROS_TO_OSC = 4294.967296 # PyrSched.h: const double kMicrosToOSC = 4294.967296; // pow(2,32)/1e6
    _SECONDS_TO_OSC = 4294967296. # PyrSched.h: const double kSecondsToOSC  = 4294967296.; // pow(2,32)/1
    _OSC_TO_NANOS = 0.2328306436538696# PyrSched.h: const double kOSCtoNanos  = 0.2328306436538696; // 1e9/pow(2,32)
    _OSC_TO_SECONDS = 2.328306436538696e-10 # PyrSched.h: const double kOSCtoSecs = 2.328306436538696e-10;  // 1/pow(2,32)

    _instance = None # singleton instance of Thread

    @classmethod
    def __init_class__(cls):
        cls()

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
            obj._task_queue = _PriorityQueue() # BUG, TODO: PriorityQueue intenta comparar el siguiente valor de la tupla si dos son iguales y falla al querer comparar tasks, hacer que '<' devuelva el id del objeto
            obj._sched_cond = _main.Main._main_lock
            obj.daemon = True # TODO: tengo que ver si siendo demonios se pueden terminar
            obj.start()
            obj._sched_init()
            cls._instance = obj
        return cls

    def _sched_init(self): # L253 inicia los atributos e.g. _time_of_initialization
        #time.gmtime(0).tm_year # must be unix time
        self._time_of_initialization = _main.Main._time_of_initialization # NOTE: es hrTimeOfInitialization que se usa en la primitiva _ElapsedTime, lo pasé a Process.
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
        # // generate a value gHostOSCoffset such that
        # // (gHostOSCoffset + systemTimeInOSCunits)
        # // is equal to gettimeofday time in OSCunits.
        # // Then if this machine is synced via NTP, we are synced with the world.
        # // more accurate way to do this??
        number_of_tries = 1
        diff = 0 # int64
        min_diff = 0x7fffFFFFffffFFFF # int64, a big number to miss
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

    # NOTE: se llama en OSCData.cpp makeSynthBundle y otras funciones de PyrSched.cpp
    def elapsed_time_to_osc(self, elapsed: float) -> int: # retorna int64
        return int(elapsed * SystemClock._SECONDS_TO_OSC) + self._elapsed_osc_offset

    # NOTE: se llama en OSCData.cpp también en funciones relacionadas a bundles/osc
    def osc_to_elapsed_time(self, osctime: int) -> float: # L286
        return float(osctime - self._elapsed_osc_offset) * SystemClock._OSC_TO_SECONDS

    # NOTE: se llama en las funciones de los servidores a bajo nivel
    def osc_time(self) -> int: # L309, devuleve elapsed_time_to_osc(elapsed_time())
        return self.elapsed_time_to_osc(_main.Main.elapsed_time()) # BUG: REVER qué elapsedTime llama (self.elapsed_time())

    def _sched_add(self, secs, task): # L353
        item = (secs, task)
        if self._task_queue.empty():
            prev_time = -1e10
        else:
            prev_time = self._task_queue.queue[0][0]
        # BUG, TODO: PriorityQueue intenta comparar el siguiente valor de la tupla si dos son iguales y falla al querer comparar tasks, hacer que '<' devuelva el id del objeto
        self._task_queue.put(item) #, block=False) Full exception, put de PriorityQueue es infinita por defecto, pero put(block=False) solo agrega si hay espacio libre inmediatamente o tira Full.
        self._task_queue.task_done() # se puede llamar concurrentemente o con _sched_cond ya está?
        if isinstance(task, stm.TimeThread):
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
            if self._run_sched:
                del self._task_queue # BUG: en realidad tiene un tamaño que reusa y no borra, pero no sé dónde se usa esta función, desde sclang usa *clear
                self._task_queue = _PriorityQueue()
                self._sched_cond.notify_all()

    # NOTE: def sched_run_func(self): # L422, es la función de este hilo, es una función estática, es run acá (salvo que no subclasee)
    def run(self):
        self._run_sched = True
        now = sched_secs = sched_point = None
        item = sched_time = task = delta = None

        while True:
            # // wait until there is something in scheduler
            while self._task_queue.empty():
                with self._sched_cond:
                    self._sched_cond.wait() # BUG: es Main._main_lock, tal vez asignar al crear el reloj
                if not self._run_sched: return

            # // wait until an event is ready
            now = 0
            while not self._task_queue.empty():
                now = _time.time()
                sched_secs = self._task_queue.queue[0][0]
                sched_point = self._time_of_initialization + sched_secs # NOTE: sched_secs (el retorno del generador) se tiene que setear desde afuera con + elapsed_time()
                if now > sched_point: break # NOTE: va directo al loop siguiente
                with self._sched_cond:
                    self._sched_cond.wait(sched_point - now)
                if not self._run_sched: return

            # // perform all events that are ready
            while not self._task_queue.empty()\
            and now >= self._time_of_initialization + self._task_queue.queue[0][0]:
                item = self._task_queue.get()
                sched_time = item[0]
                task = item[1]
                if isinstance(task, stm.TimeThread): # BUG: esto lo hace para todas las Routines o solo TimeThread? la implementación puede ser distinta acá...
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
                        # NOTE: otra cosa que se puede hacer es usar sched_cond en esta llamada
                        # para que sí sean atómicas las ejecuciones de cada rutina. Lo que
                        # puede pasar es que si dos funciones iguales se ejecutan al mismo tiempo, en
                        # vez de distribuir el tiempo entre ambas, pj. que lleguen tarde al mismo tiempo,
                        # va a pasar que una va a llegar seguro más tarde que la otra, pj. perdiendo sincronía,
                        # pero p3 sys.getswitchinterval() / sys.setswitchinterval(n) (default es 5ms,
                        # un montón). Posible BUG, si sclang llama con gLangMutex a next las rutinas
                        # ya de por sí aplican esta lógica y tendría que aplicar main_lock acá,
                        # main_lock sería simplemente un lock del cual no se esperan notificaciones.
                        # NOTE: otra cosa que se puede hacer es probar esto mismo pero con
                        # relojes (opcionales) que sean procesos python, habrá que sincronizar
                        # elapsed_time entre procesos, supongo.
                        # NOTE: deshabilitar y rehabilitar gc podría ayudar o la operación es
                        # costosa de por sí? gc.isenabled() gc.disable() gc.enable().

                        _main.Main.update_logical_time(sched_time) # NOTE: TEST, es menos eficiente pero más claro.
                        #_main.Main.main_TimeThread.seconds = sched_time # NOTE: cada vez que algo es programado se actualiza el tiempo lógico de mainThread.

                        if isinstance(task, _types.FunctionType):
                            n = len(_inspect.signature(task).parameters)
                            if n > 3:
                                msg = f'SystemClock scheduled function takes between 0 and 3 positional arguments but {n} were given'
                                raise TypeError(msg)
                            args = [sched_time, sched_time, self][:n]
                            delta = task(*args)
                        elif isinstance(task, (stm.Routine, stm.PauseStream)):
                            delta = task.awake(sched_time, sched_time, self) # NOTE: la implementan solo Routine y PauseStream, pero VER: # NOTE: awake la implementan Function, Nil, Object, PauseStream y Routine, y se llama desde C/C++ también, tal vez por eso wakeup está implementada como una función en vez de un método (pasar a método).
                        else:
                            raise TypeError(f"type '{type(item)}' is not supported by SystemClock scheduler")

                        if isinstance(delta, (int, float)) and not isinstance(delta, bool):
                            time = sched_time + delta # BUG, TODO: sclang usa wait until que espera en tiempo absoluto y no en offset como acá, no hay esa función en Python
                            self._sched_add(time, task)
                    except stm.StopStream: # NOTE: Routine arroja StopStream en vez de StopIteration
                        pass
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
        _main.Main.update_logical_time() # NOTE: TODAS LAS ACCIONES QUE PUEDAN DEPENDER DEL TIEMPO DE LAS ROUTINAS TIENEN QUE ACTUALIZAR ANTES DE EVALUAR.
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


class Scheduler():
    def __init__(self, clock, drift=False, recursive=True):
        self._clock = clock
        self._drift = drift
        self.recursive = recursive
        # init
        self._beats = _main.Main.current_TimeThread.beats
        self._seconds = 0.0
        # BUG, TODO: PriorityQueue intenta comparar el siguiente valor de la tupla si dos son iguales y falla al querer comparar tasks, hacer que '<' devuelva el id del objeto
        self.queue = _PriorityQueue()
        self._expired = []

    def _wakeup(self, item):
        try:
            try:
                _main.Main.update_logical_time(self._seconds) # NOTE: Parece correcto el comportamiento, se debe actualizar en wakeup o en awake, acá los estoy haciendo antes pero el tiempo lógico es el mismo que se le pasa a awake.

                if isinstance(item, _types.FunctionType):
                    n = len(_inspect.signature(item).parameters)
                    if n > 3:
                        msg = f'Scheduler wakeup function takes between 0 and 3 positional arguments but {n} were given'
                        raise TypeError(msg)
                    args = [self._beats, self._seconds, self._clock][:n]
                    delta = item(*args)
                elif isinstance(item, (stm.Routine, stm.PauseStream)):
                    delta = item.awake(self._beats, self._seconds, self._clock) # NOTE: la implementan solo Routine y PauseStream, pero VER: # NOTE: awake la implementan Function, Nil, Object, PauseStream y Routine, y se llama desde C/C++ también, tal vez por eso wakeup está implementada como una función en vez de un método (pasar a método).
                else:
                    raise TypeError(f"type '{type(item)}' is not supported by Scheduler")

                if isinstance(delta, (int, float))\
                and not isinstance(delta, bool):
                    self.sched(delta, item)
            except stm.StopStream:
                pass
        except Exception:
            _traceback.print_exception(*_sys.exc_info())

    def play(self, task):
        self.sched(0, task)

    def sched(self, delta, item): # delta no puede ser None
        if self._drift:
            from_time = _main.Main.elapsed_time()
        else:
            _main.Main.update_logical_time() # BUG: ASÍ FUNCIONA IGUAL DE MAL QUE SCLANG (es drift=False)
            from_time = self.seconds = _main.Main.current_TimeThread.seconds # BUG: SINCORNIZANDO CON CURRENT_THREAD FUNCIONA BIEN (AGREGADO), PERO NO LE VEO SENTIDO.
        self.queue.put((from_time + delta, item))
        #self.queue.task_done() # es una anotación por si es útil luego

    def sched_abs(self, time, item):
        self.queue.put((time, item))
        #self.queue.task_done() # es una anotación por si es útil luego

    def clear(self):
        item = None
        while not self.queue.empty():
            item = self.queue.get() # NOTE: vacía la cola sacando las Routine, PauseStream o Function
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
        self._seconds = self.queue.queue[0][0] # topPriority(), usa los atributos por el cierre de wakeup
        if self.recursive:
            while self._seconds <= value: # seconds no puede ser None, sí la primera iteración es igual valor.
                self._beats = self._clock.secs2beats(self._seconds)
                self._wakeup(self.queue.get())
                if self.queue.empty():
                    break
                else:
                    self._seconds = self.queue.queue[0][0]
        else:
            # // First pop all the expired items and only then wake
            # // them up, in order for control to return to the caller
            # // before any tasks scheduled as a result of this call are
            # // awaken.
            while self._seconds <= value:
                self._expired.append(self.queue.get())
                if self.queue.empty():
                    break
                else:
                    self._seconds = self.queue.queue[0][0]
            for time, item in self._expired:
                self._seconds = time
                self._beats = self._clock.secs2beats(time)
                # import inspect
                # if isinstance(item, stm.Routine):
                #     print('******* sched _wakeup item *** ***', inspect.getsource(item.func))
                self._wakeup(item)
            self._expired.clear()
        self._seconds = value
        self._beats = self._clock.secs2beats(value)


@utl.initclass
class AppClock(Clock): # ?
    _instance = None # singleton instance of Thread

    @classmethod
    def __init_class__(cls):
        cls()

    def __new__(cls):
        if cls._instance is None:
            obj = super().__new__(cls)
            _threading.Thread.__init__(obj)
            obj._sched_cond = _main.Main._main_lock
            obj._tick_cond = _threading.Condition()
            obj._scheduler = Scheduler(cls, drift=True, recursive=False)
            cls._instance = obj # tiene que estar antes de start porque hace un tick de gracia
            obj.daemon = True # TODO: tengo que ver si siendo demonios se pueden terminar, no recuerdo.
            obj.start()
        return cls # no llama a __init__

    def run(self): # TODO: queda un poco desprolijo el método de instancia en la clase teniendo en cuenta que se puede evitar pero si no se hereda de threading.Thread
        self._run_sched = True
        seconds = None
        while True:
            with self._sched_cond: # es Main._main_lock
                seconds = type(self).tick() # el primer tick es gratis y retorna None
                if isinstance(seconds, (int, float))\
                and not isinstance(seconds, bool):
                    seconds = seconds - self._scheduler.seconds # tick retorna abstime (elapsed)
                else:
                    seconds = None
            with self._tick_cond: # la relación es muchas notifican una espera, tal vez no sea Condition el objeto adecuado, VER threading
                self._tick_cond.wait(seconds) # si seconds es None espera indefinidamente a notify
            if not self._run_sched: return

    @classmethod
    def clear(cls):
        cls._instance._scheduler.clear()

    @classmethod
    def sched(cls, delta, item):
        with cls._instance._sched_cond:
            cls._instance._scheduler.sched(delta, item)
        with cls._instance._tick_cond:
            cls._instance._tick_cond.notify() # cls.tick() pasada a run

    @classmethod
    def tick(cls):
        tmp = _main.Main.current_TimeThread.clock
        _main.Main.current_TimeThread.clock = cls # BUG: supongo que porque puede que scheduler evalue una Routine con play/run? Debe ser para defer. Igual no me cierra del todo, pero también porque sclang tiene un bug con los relojes heredados.
        cls._instance._scheduler.seconds = _main.Main.elapsed_time()
        _main.Main.current_TimeThread.clock = tmp
        if cls._instance._scheduler.queue.empty():
            return None # BUG: es un valor que se comprueba para saber si client::tick deja de llamarse a sí mismo.
        else:
            return cls._instance._scheduler.queue.queue[0][0] # topPriority()

    # NOTE: Este comentario es un recordatorio.
    # def _sched_notify(cls):
    # _AppClock_SchedNotify
    # En SC_TerminalClient _AppClock_SchedNotify es SC_TerminalClient::prScheduleChanged
    # que llama a la instancia del cliente (de sclang), que llama a su método
    # sendSignal(sig_sched) con la opción sig_sched que llama a SC_TerminalClient::tick
    # Acá podría ir todo dentro de sched(), ergo sum chin pum: cls.tick()


# NOTE: Nota original en TempoClock.
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


# *** BUG: IMPORTANTE: CON METACLASES SE PUEDE TENER EL MISMO NOMBRE PARA UNA
# *** BUG: PROPIEDAD DE CLASE Y DE INSTANCIA. REVISAR PORQUE HABÍAN CASOS QUE
# *** BUG: NO RECUERDO SI NO DECIDÍ CAMBIAR ALGO PORQUE NO SABÍA ESTO.
# *** BUG: IGUALMENTE NO SE PUEDE HACER CON MÉTODOS, SOLO CON PROPERTY.


class MetaTempoClock(type):
    _all = []
    default = None # NOTE: si se define acá no pertenece al diccionario de TempoClock, así está en Server aunque como @property

    @property
    def all(cls):
        return cls._all


@utl.initclass
class TempoClock(Clock, metaclass=MetaTempoClock):
    @classmethod
    def __init_class__(cls):
        cls.default = cls()
        cls.default.permanent = True
        sac.CmdPeriod(cls)

    @classmethod
    def cmd_period(cls):
        for item in cls.all:
            item.clear(False)
        # // copy is important: You must never iterate over the same
        # // collection from which you're removing items
        for item in cls.all[:]:
            if not item.permanent:
                item.stop() # BUG: supongo que stop quita de all, llama a _TempoClock_Free

    def __init__(self, tempo=None, beats=None, seconds=None):
        # NOTE: en init
        # queue = Array.new(queueSize); # NOTE: no hay cola acá.
        # this.prStart(tempo, beats, seconds) _TempoClock_New

        # prTempoClock_New
        tempo = tempo or 1.0
        if tempo < 0.0:
            raise ValueError(f'invalid tempo {tempo}')
        beats = beats or 0.0
        if seconds is None:
            seconds = _main.Main.current_TimeThread.seconds # BUG: revisar, creo que está bien.

        # TempoClock::TempoClock()
        self._tempo = tempo
        self._beat_dur = 1.0 / tempo
        self._base_seconds = seconds
        self._base_beats = beats
        # self._beats = 0.0 # NOTE: no lo setea el constructor

        # NOTE: mRun(true) setea el contstructor, es la condición del loop del hilo.
        # NOTE: acá es self._run_sched como en las clases de arriba, se crea e inicia en python Thread.run().

        self._prev = None
        self._next = sAll # BUG: sAll es una lista ligada, acá _all lo vengo suponiendo array.
        if sAll is not None:
            sAll._prev = self
        sAll = self

        _threading.Thread.__init__(self)
        self._task_queue = _PriorityQueue() # BUG, TODO: PriorityQueue intenta comparar el siguiente valor de la tupla si dos son iguales y falla al querer comparar tasks, hacer que '<' devuelva el id del objeto
        self._sched_cond = _main.Main._main_lock # NOTE: igual que SystemClock, pero revisar TempoClock::Run
        self.daemon = True # TODO: tengo que ver si siendo demonios se pueden terminar
        self.start()

        # init luego de prStart
        # type(self)._all.append(self)

        # NOTE: atributos definidos en sclang como var
        self._beats_per_bar = 4.0
        self._bars_per_beat = 0.25
        self._base_bar_beat = 0
        self._base_bar = 0.0
        self.permanent = False

    def run(self):
        self._run_sched = True
        # TODO

    def stop(self):
        # TODO: prStop -> TempoClock_Free

    def play(self, task, quant=1):
        quant = Quant.as_quant(quant)
        self.sched_abs(quant.next_time_on_grid(self), task)

    def play_next_bar(self, task):
        self.sched_abs(self.next_bar(), task)

    @property
    def tempo(self):
        # _TempoClock_Tempo
        if not self.is_alive():
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
        if not self.is_alive():
            raise RuntimeError(f'{self} is not running')
        if self._tempo < 0.0: # BUG: NO ES CLARO: usa _tempo (mTempo), que puede ser negativo mediante etempo y en ese caso no deja setear acá, ES RARO.
            raise ValueError(
                "cannot set tempo from this method. "
                "The method 'etempo' can be used instead")
        if value < 0.0:
            raise ValueError(
                f"invalid tempo {value}. The method "
                "'etempo' can be used instead.")
        # TempoClock::SetTempoAtBeat
        self._base_seconds = self.beats2secs(self.beats) # BUG: revisar es mBaseSeconds
        self._base_beats = self.beats # BUG: supongo que no cambia entre llamadas, es argumento en C++.
        self._tempo = value
        self._beat_dur = 1.0 / value
        self._sched_cond.notify() # BUG: es notify_one en C++, comprobar que TempoClock no use otra condición, aún no la definí.
        # en tempo_
        mdl.NotificationCenter.notify(self, 'tempo')

    def beat_dur(self):
        # TODO: _TempoClock_BeatDur

    def elapsed_beats(self):
        # TODO: _TempoClock_ElapsedBeats
        # // primitive does this: ^this.secs2beats(Main.elapsedTime).

    @property
    def beats(self):
        # TODO: _TempoClock_Beats
        # // returns the appropriate beats for this clock from any thread
        # // primitive does this:
        # if (thisThread.clock == this) { ^thisThread.beats }
        # ^this.secs2beats(thisThread.seconds)

    @beats.setter
    def beats(self, value):
        # TODO: _TempoClock_SetBeats

    @property
    def seconds(self): # NOTE: definido solo como getter es thisThread.seconds, en TimeThread es property, acá también por consistencia?
        return _main.Main.current_TimeThread.seconds

    def sched(self, delta, item):
        # TODO: _TempoClock_Sched

    def sched_abs(self, beat, item):
        # TODO: _TempoClock_SchedAbs

    def clear(self, release_nodes=True):
        # // flag tells EventStreamPlayers that CmdPeriod is removing them, so
        # // nodes are already freed
        # // NOTE: queue is an Array, not a PriorityQueue, but it's used as such internally. That's why each item uses 3 slots.
        # TODO: llama a prClear -> _TempoClock_Clear

    @property
    def beats_per_bar(self):
        return self._beats_per_bar

    @beats_per_bar.setter
    def beats_per_bar(self, value):
        # TODO

    @property # TODO: no parece tener setter.
    def base_bar_beat(self):
        return self._base_bar_beat

    @property # TODO: no parece tener setter.
    def base_bar(self):
        return self._base_bar

    # // for setting the tempo at the current elapsed time.
    def etempo(self, value):
        # TODO: this.setTempoAtSec(newTempo, Main.elapsedTime);
        #mdl.NotificationCenter.notify(self, 'tempo')

    def beats2secs(self, beats):
        # TODO: _TempoClock_BeatsToSecs

    def secs2beats(self, seconds):
        # TODO: _TempoClock_SecsToBeats

    def dump(self): # NOTE: es prDump, como privado, parece método para debug.
        # _(pr)TempoClock_Dump -> TepmoClock::Dump
        # if self.is_alive(): # NOTE de lo contrario no hace nada.
        # post("mTempo %g\n", mTempo);
        # post("mBeatDur %g\n", mBeatDur);
        # post("mBeats %g\n", mBeats);
        # post("seconds %g\n", BeatsToSecs(mBeats));
        # post("mBaseSeconds %g\n", mBaseSeconds);
        # post("mBaseBeats %g\n", mBaseBeats);

    def next_time_on_grid(self, quant=1.0, phase=0):
        # TODO

    # // logical time to next beat
    def time_to_next_beat(self, quant=1.0):
        # TODO

    def beats2bars(self, beats):
        # TODO

    def bars2beats(self, bars):
        # TODO

    def bar(self):
        # TODO

    def next_bar(self, beat):
        # TODO

    def beat_in_bar(self):
        # TODO

    # isRunning { ^ptr.notNil } # NOTE: es is_alive() de Thread acá.

    # // PRIVATE
    # prStart # pasada adentro de __init__
    # prStop # seguro pase a stop
    # prClear # seguro pase a clear

    # setTempoAtBeat # lógica pasada a al setter de tempo.

    # setTempoAtSec
    # // meter should only be changed in the TempoClock's thread.
    # setMeterAtBeat

    # // these methods allow TempoClock to act as TempoClock.default
    # TODO: VER SI VAN O NO


class NRTClock(Clock):
    # Los patterns temporales tienen que generar una rutina que
    # corra en el mismo reloj. El probleam es que el tiempo no
    # avanza si no se llama a yield/wait. El reloj de Jonathan
    # captura la cola y usa un servidor dummy, pero si el pattern
    # usa el reloj en 'tiempo real' eso no queda registrado.
    # Además, en nrt todas las acciones son sincrónicas.
    # NOTE: Se puede crear un hilo que emule elapsed_time a una
    # NOTE: determinada frecuencia de muestreo/control.
    # NOTE: que se puedan segmentar los render y que se pueda usar transport.
    pass


def defer(item, delta=None):
    # BUG: creo que canCallOS no va a ser necesario en Python, pero tengo que ver
    # BUG: esta función tal vez haya que implementarla en AbstractFunction por completitud, pero tengo que ver.
    if callable(item):
        def df():
            item()
            # NOTE: se envuelve porque lambda retorna el valor de la sentencia que contiene
    else:
        raise TypeError('item is not callable')
    AppClock.sched(delta or 0, df)
