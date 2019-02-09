"""Thread.sc"""

# TODO: ver https://www.python.org/dev/peps/pep-0492/
# TODO: ver https://www.python.org/dev/peps/pep-0342/
# TODO: ver https://www.python.org/dev/peps/pep-0380/
# TODO: ver https://www.python.org/dev/peps/pep-0550/
# TODO: ver https://www.python.org/dev/peps/pep-0567/
# aunque son para Python 3.7 en relación a asyncio
# TODO: ver https://stackoverflow.com/questions/750702/retrieving-printing-execution-context
# ^ CREO QUE NINGUNO DE ESOS RECURSOS ME SIRVE ^

# TODO: Process y Main (juntas o por separado, o solo Process) serían
# TODO: el entorno de ejecusión de SuperCollider dentro de Python.
# TODO: Probablemente sea lo mejor usar Process/Main para el manejo
# TODO: de los Threads como controlador global. No sé si no lo mismo
# TODO: con las cosas de synthdef en _global.py. Process es un nombre
# TODO: acertado para esto, en vez de Client, que sería oscclient o
# TODO: parte de la implementación de Process. SCLang hace muchas cosas
# TODO: distintas específicas del lenguaje que acá no son necesarias.

import enum
import inspect
import threading
import random

from . import clock as clk
from . import main as _main
import supercollie.stream as stm

class TimeThread(): #(Stream): # BUG: hereda de Stream por Routine y no la usa, pero acá puede haber herencia múltiple. Además, me puse poético con el nombre.
    # ./lang/LangSource/PyrKernel.h: enum { tInit, tStart, tReady, tRunning, tSleeping, tSuspended, tDone };
    # ./lang/LangSource/PyrKernel.h: struct PyrThread : public PyrObjectHdr

    State = enum.Enum('State', [
        'Init', 'Start', 'Ready', 'Running',
        'Sleeping', 'Suspended', 'Done'
    ])
    _instance = None

    @classmethod
    def singleton(cls):
        if cls._instance is not None:
            return cls._instance
        obj = cls.__new__(cls)
        obj.parent = None # BUG: o será mejor main._Main?
        obj.func = None # BUG, TODO: esta función se tiene que encargar de evaluar el código cuando los relojes lo dispongan y volver a poner las Routinas en la cola cuando corresponda
        # BUG, TODO: PriorityQueue intenta comparar el siguiente valor de la tupla si dos son iguales y falla al quere comparar tasks.
        obj.state = cls.State.Init # ver qué estado tiene, sclang thisThread.isPlaying devuelve false desde arriba de todo
        obj._beats = 0 # ver dónde setea en sclang
        obj._seconds = 0
        obj._clock = clk.SystemClock
        obj._thread_player = None
        obj._rand_state = random.getstate()
        return obj

    def __init__(self, func):
        # _Thread_Init -> prThreadInit -> initPyrThread
        if not inspect.isfunction(func):
            raise TypeError('Thread func arg is not a function')

        # TODO: Python tiene threading._MainThread, que es el thread del intérprete o como se llame,
        # TODO: se accede mediante threading.main_thread(), también tiene threading.current_thread()
        # TODO: Tengo que estudiarlo un poco más y ver Process de nuevo, pero lo más probable es que
        # TODO: cree SystemClock como el thread base de todos los tempoclock. El thread principal
        # TODO: de sclang mainThread es thisThread at top y tiene SystemClock como singleton.
        # TODO: Ojo, igual, que los thread reales son los relojes, por eso tengo que ver
        # TODO: cómo cambia y quién guarda current_TimeThread, que es un corutina temporal,
        # TODO: con threading.current_thread() se accede al reloj. Lo que me pregunto es
        # TODO: qué pasa si se ejecuta todo en un proceso distinto al repl original, en
        # TODO: Conclusión: no importa, toda esta lógica tiene que funcionar para un solo
        # TODO: proceso y luego puede ser escalada, tal vez sin iniciar el servidor osc o midi, etc.

        # BUG: ver test_clock_thread.scd, estos valores no tienen efecto porque
        # se sobreescribe el reloj por TempoClock.default en Stream:play
        # y Routine:run vuelve a escribir SystemClock (cuando ya lo hizo en
        # PyrPrimitive). La única manera de usar el reloj heredado es llamando a next.
        self._beats = _main.Main.current_TimeThread.beats
        self._seconds = _main.Main.current_TimeThread.seconds # ojo que tienen setters porque son dependientes...

        # BUG: ver qué pasa con terminalValue <nextBeat, <>endBeat, <>endValue;
        # se usan en la implementación a bajo nivel de los relojes.

        self.func = func
        self.state = self.State.Init

        if _main.Main.current_TimeThread.clock is None:
            self._clock = clk.SystemClock
        else:
            self._clock = _main.Main.current_TimeThread.clock # hace slotCopy y lo registra en GC, puede que solo esté marcando una referencia más, más arriba a GCWriteNew con el array de la pila que es nuevo

        # NOTA: No guarda la propiedad <parent cuando crea el thread, es
        # &g->thread que la usa para setear beats y seconds pero no la guarda,
        # la setea luego en algún lugar, con el cambio de contexto, supongo,
        # y tiene valor solo mientras la rutina está en ejecusión. Ver test_clock_thread.scd
        self.parent = None
        self._thread_player = None
        self._rand_state = random.getstate()

        # TODO: No vamos a usar entornos como en sclang, a lo sumo se podrían pasar diccionarios
        #self.environment = current_Environment # acá llama al slot currentEnvironment de Object y lo setea al del hilo

        # BUG: acá setea nowExecutingPath de la instancia de Process (Main) si es que no la estamos creando con este hilo.
        # if(g->process) { // check we're not just starting up
    	# 	slotCopy(&thread->executingPath,&g->process->nowExecutingPath);

    def __copy__(self):
        return self
    def __deepcopy__(self, memo):
        return self

    @property
    def clock(self):
        return self._clock
    @clock.setter
    def clock(self, clock):
        self._clock = clock
        self._beats = clock.secs2beats(self.seconds) # no llama al setter de beats, convierte los valores en sesgundos de este thread según el nuevo clock

    @property
    def seconds(self):
        return self._seconds
    @seconds.setter
    def seconds(self, seconds):
        self._seconds = seconds
        self._beats = self.clock.secs2beats(seconds)

    @property
    def beats(self):
        return self._beats
    @beats.setter
    def beats(self, beats):
        self._beats = beats
        self._seconds = self.clock.beats2secs(beats)

    def is_playing(self):
        return self.state == State.Suspended

    @property
    def thread_player(self):
        if self._thread_player is not None:
            return self._thread_player
        else:
            if self.parent is not None\
            and self.parent is not _main.Main.main_TimeThread:
                return self.parent.thread_player()
            else:
                return self
    @thread_player.setter
    def thread_player(self, player): # BUG: se usa en Stream.sc que no está implementada
        self._thread_player = player

    def rand_seed(self, seed):
        # TODO: el siguiente comentario no es válido para Python usando el algoritmo de random.
        # // You supply an integer seed.
        # // This method creates a new state vector and stores it in randData.
        # // A state vector is an Int32Array of three 32 bit words.
        # // SuperCollider uses the taus88 random number generator which has a
        # // period of 2**88, and passes all standard statistical tests.
        # // Normally Threads inherit the randData state vector from the Thread that created it.
        if _main.Main.current_TimeThread is self:
            random.seed(seed) # BUG solo hay un generador random por intancia del intérprete, setear la semilla es lo mismo que setear el estado, no?
        else:
            tmp = random.getstate()
            random.seed(seed)
            self._rand_state = random.getstate()
            random.setstate(tmp)
    @property
    def rand_state(self):
        if _main.Main.current_TimeThread is self:
            return random.getstate()
        else:
            return self._rand_state
    @rand_state.setter
    def rand_state(self, data):
        self._rand_state = data
        #random.setstate(data) # BUG: esto hay que hacerlo desde fuera??

    # TODO: ver el manejo de excpeiones, se implementa junto con los relojes
    # failedPrimitiveName
    # handleError
    # *primitiveError
    # *primitiveErrorString

    # Estos métodos no son necesarios porque no estamos herendando de Stream
    # // these make Thread act like an Object not like Stream.
    # next { ^this }
    # value { ^this }
    # valueArray { ^this }

    # TODO: ver pickling
    # storeOn { arg stream; stream << "nil"; }
    # archiveAsCompileString { ^true }
    # checkCanArchive { "cannot archive Threads".warn }


class Routine(TimeThread, stm.Stream): # BUG: ver qué se pisa entre Stream y TimeThread y mro.
    # TODO: como Routine es un envoltorio tengo que ver qué haga con
    # la relación entre generador e iterador y cuándo es una función normal.

    @classmethod
    def run(cls, func, clock, quant):
        pass # TODO

    def __iter__(self):
        return self
    def __next__(self): # BUG: ver cómo sería la variante pitónica, luego.
        pass # TODO: es _RoutineResume

    # TODO: es _RoutineResume
    def next(self, inval=None):
        # Si el estado de self es Init
        # prRoutineResume
        # TODO: setea nowExecutingPath, creo que no lo voy a hacer.
        previous_rand_state = random.getstate()
        random.setstate(self._rand_state) # hay que llamarlo ANTES de setear current_TimeThread o usar el atributo privado _rand_state
        self.parent = _main.Main.current_TimeThread
        _main.Main.current_TimeThread = self
        # TODO: le asigna los valores de parent a beats, seconds, clock de este hilo.
        # switchToThread(g, parent, tSuspended, &numArgsPushed);
        # TODO: switchea rand data, pasado acá ARRIBA
        # TODO: setea el entorno de este hilo, eso no lo voy a hacer.
        # prRoutineResume
        # TODO: hace esto que no sé qué es: sendMessage(g, s_prstart, 2);
        # Luego hace para state == tSuspended, y breve para Done (creo que devuelve terminalValue), Running (error), else error.
        try:
            return self._iterator.send(inval) # BUG: _iterator.send es solo para iteradores generadores
        except AttributeError as e:
            # Todo esto es para imitar la funcionalidad/comportamiento de las
            # corrutinas en sclang. Pero se vuelve poco pitónico, por ejemplo,
            # no se pueden usar next() y for, e implica un poco más de carga.
            if len(inspect.trace()) > 1: # sigue solo si la excepción es del frame actual
                raise e
            if len(inspect.signature(self.func).parameters) == 0: # esto funciona porque es solo para la primera llamada, cuando tampoco existe _iterator, luego no importa si la función tenía argumentos.
                self._iterator = self.func()
            else:
                self._iterator = self.func(inval)
            return next(self._iterator)
        finally:
            # prRoutineYield # BUG: ver qué pasa con las otras excepciones dentro de send, si afectan este comportamiento
            self._rand_state = random.getstate()
            random.setstate(previous_rand_state)
            _main.Main.current_TimeThread = self.parent
            self.parent = None
            # TODO: setea nowExecutingPath, creo que no lo voy a hacer: slotCopy(&g->process->nowExecutingPath, &g->thread->oldExecutingPath);
            # switchToThread(g, parent, tSuspended, &numArgsPushed);
            # TODO: switchea rand data, pasado acá ARRIBA
            # TODO: setea el entorno de este hilo, eso no lo voy a hacer.

    # TODO:
    # prRoutineAlwaysYield además setea terminalValue y hace switchToThread(g, parent, tDone, &numArgsPushed);
    # prRoutineReset
    # prRoutineStop
    # prRoutineYieldAndReset simplifica cosas que no son necesarias cuando yield va a reset

    # reset # _RoutineReset
    # stop # _RoutineStop con otros detalles

    # // resume, next, value, run are synonyms
    # next, ver arriba
    # value
    # resume
    # run (de instancia, no se puede)

    # valueArray se define como ^this.value(inval), opuesto a Stream valueArray que no recibe inval... BUG del tipo desprolijidad? o hay una razón?

    # p ^Prout(func)
    # storeArgs
    # storeOn

    # // PRIVATE
    # awake, llama a next(inBeats)
    # prStart
