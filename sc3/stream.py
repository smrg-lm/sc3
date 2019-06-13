"""Stream.sc"""

import inspect
import enum
import random

from . import main as _main
from . import clock as clk
from . import functions as fn
from . import model as mdl
from . import systemactions as sac
from . import event as evt


class StopStream(StopIteration):
    pass


# NOTE: para _RoutineYieldAndReset, ver método de Routine
class YieldAndReset(Exception):
    def __init__(self, value=None):
        super().__init__()
        self.value = value


# NOTE: para _RoutineAlwaysYield, ver método de Routine
class AlwaysYield(Exception):
    def __init__(self, terminal_value=None):
        super().__init__()
        self.terminal_value = terminal_value


class Stream(fn.AbstractFunction): #, ABC):
    ### iterator protocol ###

    def __iter__(self):
        return self

    def __stream__(self):
        return self

    def __embed__(self, inval=None):
        while True:
            yield self.next(inval)

    def __next__(self):
        return self.next() # TODO: en Python no son infinitos por defecto

    def __call__(self, inval=None):
        return self.next(inval)

    def yield_and_reset(self, value=None):
        if self is _main.Main.current_TimeThread:
            raise YieldAndReset(value)
        else:
            raise Exception('yield_and_reset only works if self is main.Main.current_TimeThread')

    def always_yield(self, value=None):
        if self is _main.Main.current_TimeThread:
            raise AlwaysYield(value) # BUG: ver como afecta a StopIteration
        else:
            raise Exception('always_yield only works if self is main.Main.current_TimeThread')

    #@abstractmethod # NOTE: la clase que se usa como Stream por defecto es Routine (hay otras)
    def next(self, inval=None): # se define en Object y se sobreescribe con subclassResponsibility en Stream
        raise NotImplementedError('Stream is an abstract class') # BUG: ver abc, ver que pasa lo mismo en Clock (__new__ o irá en __init__?)

    # @property # BUG: ver si es realmente necesario definir esta propiedad
    # def parent(self): # TODO: entiendo que esta propiedad, que no se puede declarar como atributo, es por parent de Thread
    #     return None

    # def stream_arg(self): # BUG: se usa para Pcollect, Pselect, Preject, el método lo definen Object y Pattern también.
    #     return self

    def all(self, inval=None):
        self.reset()
        item = None
        lst = []
        while True:
            try:
                item = self.next(inval)
                lst.append(item)
            except StopIteration:
                break
        return lst

    # put
    # putN
    # putAll
    # do
    # subSample # es un tanto específico, evalúa a partir de offset una cantidad skipSize
    # generate # método interno para list comprehensions, documentado en Object

    # Estos métodos acá se podrían dejar para generator list comprehensions
    # collect
    # reject
    # select

    # dot # // combine item by item with another stream # NOTE: usa FuncStream
    # interlace # // interlace with another stream # NOTE: usa FuncStream
    # ++ (appendStream)
    # append_stream # NOTE: usa Routine con embedInStream
    # collate # // ascending order merge of two streams # NOTE: usa interlace
    # <> # Pchain

    def compose_unop(self, selector):
        return UnaryOpStream(selector, self)

    def compose_binop(self, selector, other):
        return BinaryOpStream(selector, self, stream(other)) # BUG: BUG: en sclang usa el adverbio y si es nil la operación binaria retorna nil, tal vez porque sin él no hace la operación elemento a elemento de los streams.

    def compose_narop(self, selector, *args):
        args = [stream(x) for x in args]
        return NAryOpStream(selector, self, *args)

    # asEventStreamPlayer
    # play
    # trace
    # repeat

    # reset # NOTE: la docuemntación dice que está pero no todos los streams lo implementan.


### BasicOpStream.sc ###


class UnaryOpStream(Stream):
    def __init__(self, selector, a):
        self.selector = selector
        self.a = a

    def next(self, inval=None):
        a = self.a.next(inval) # NOTE: tira StopIteration
        if hasattr(self.selector, '__scbuiltin__'):
            return self.selector(a)
        else:
            return getattr(a, self.selector)()

    def reset(self):
        self.a.reset()

    # storeOn # TODO


class BinaryOpStream(Stream):
    def __init__(self, selector, a, b):
        self.selector = selector
        self.a = a
        self.b = b

    def next(self, inval=None):
        a = self.a.next(inval) # NOTE: tira StopIteration
        b = self.b.next(inval)
        if hasattr(self.selector, '__scbuiltin__'):
            return self.selector(a, b)
        else:
            ret = getattr(a, self.selector)(b)
            if ret is NotImplemented and type(a) is int and type(b) is float: # BUG: ver cuál era el caso de este problema
                return getattr(float(a), self.selector)(b)
            return ret

    def reset(self):
        self.a.reset()
        self.b.reset()

    # storeOn # TODO


class NAryOpStream(Stream):
    def __init__(self, selector, a, *args):
        self.selector = selector
        self.a = a
        self.args = args # BUG: cambié el nombres arglist, no uso la optimización isNumeric, todos los args son stream (convertidos en la llamada)

    def next(self, inval=None):
        a = self.a.next(inval) # NOTE: tira StopIteration
        args = []
        res = None
        for item in self.args:
            res = item.next(inval) # NOTE: tira StopIteration
            args.append(res)
        if hasattr(self.selector, '__scbuiltin__'):
            return self.selector(a, *args)
        else:
            return getattr(a, self.selector)(*args)

    def reset(self):
        self.a.reset()
        for item in self.args:
            item.reset()

    # storeOn # TODO


### Thread.sc ###


# TODO: TimeThread podría implementar __new__ como singleton y se
# pasa la implementación de __init__ a Routine, pero ver qué pasa
# con AppClock y el posbile NRTClock (NrtClock?)
class TimeThread(): #(Stream): # BUG: hereda de Stream por Routine y no la usa, pero acá puede haber herencia múltiple. Además, me puse poético con el nombre.
    # ./lang/LangSource/PyrKernel.h: enum { tInit, tStart, tReady, tRunning, tSleeping, tSuspended, tDone };
    # ./lang/LangSource/PyrKernel.h: struct PyrThread : public PyrObjectHdr

    State = enum.Enum('State', [
        'Init', 'Running', 'Suspended', 'Done' # NOTE: tStart, tReady y tSleeping no se usan en ninguna parte
    ])
    _instance = None

    @classmethod
    def singleton(cls):
        if cls._instance is not None:
            return cls._instance
        obj = cls.__new__(cls)
        obj.parent = None
        obj.func = None
        # BUG, TODO: PriorityQueue intenta comparar el siguiente valor de la tupla si dos son iguales y falla al quere comparar tasks.
        obj.state = cls.State.Init # ver qué estado tiene, sclang thisThread.isPlaying devuelve false desde arriba de todo
        obj._thread_player = None
        obj._rand_state = random.getstate() # Esto es para que funcione el getter pero creoq que no es necesario para TimeThread
        return obj

    def __init__(self, func):
        # _Thread_Init -> prThreadInit -> initPyrThread
        if not inspect.isfunction(func):
            raise TypeError('Thread func arg is not a function')

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
        # y tiene valor solo mientras la rutina está en ejecución. Ver test_clock_thread.scd
        self.parent = None

        self.state = self.State.Init
        self._thread_player = None
        self._previous_rand_state = None
        self._rand_state = random.getstate()

        # para Routine
        self._iterator = None # se inicializa luego de la excepción
        self._last_value = None
        self._terminal_value = None

        # TODO: No vamos a usar entornos como en sclang, a lo sumo se podrían pasar diccionarios
        # self.environment = current_Environment # acá llama al slot currentEnvironment de Object y lo setea al del hilo

        # BUG: acá setea nowExecutingPath de la instancia de Process (Main) si es que no la estamos creando con este hilo.
        # if(g->process) { // check we're not just starting up
        #     slotCopy(&thread->executingPath,&g->process->nowExecutingPath);

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    @property
    def clock(self): # mainThread clock (SystemClock) no se puede setear y siempre devuelve elapsedTime en seconds
        # Ídem seconds
        return clk.SystemClock

    @clock.setter
    def clock(self, value): # definido por compatibilidad, se comporta igual y no hace nada
        pass

    @property
    def seconds(self):
        # Los segundos de Thread (NO DE ROUTINE) en sclang avanzan constantemente, no encuentro cómo está definido eso
        # En Routine se queda con los valores de inicialización en __init__
        # Esta propiedad se sebreescribe y tiene setter
        return _main.Main.elapsed_time()

    @seconds.setter
    def seconds(self, value): # definido por compatibilidad, se comporta igual y no hace nada
        pass

    @property
    def beats(self):
        # Ídem seconds.
        return _main.Main.elapsed_time()

    @beats.setter
    def beats(self, value): # definido por compatibilidad, se comporta igual y no hace nada
        pass

    def playing(self): # BUG: era is_playing, está pitonizado
        return self.state == self.State.Suspended

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
        # random.setstate(data) # BUG: esto hay que hacerlo desde fuera??

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


class Routine(TimeThread, Stream): # BUG: ver qué se pisa entre Stream y TimeThread y mro. Creo que el úlitmo que se agrega sobreescribe y en sclang thread es subclase de stream, pero Python llama a __init__ del primero en la lista.
    # TODO: como Routine es un envoltorio tengo que ver qué haga con
    # la relación entre generador e iterador y cuándo es una función normal.

    @classmethod
    def run(cls, func, clock=None, quant=None):
        obj = cls(func)
        obj.play(clock, quant)
        return obj

    def play(self, clock=None, quant=None): # BUG: quant no está implementado ni la lógica acá
        '''el argumento clock pordía soportar un string además de un objeto
        clock, 'clojure', para el reloj en que se creó el objeto Routine,
        'parent' para el reloj de la rutina desde la que se llama a play y
        'default' para TempoClock.default (global), pero hay que comprobar
        que en la creación o antes de llamar a play no se haya seteado
        un reloj 'custom'. El reloj no se puede cambiar una vez que se llamó
        a run o play.'''
        clock = clock or _main.Main.current_TimeThread.clock # BUG: perooooooo! esto no es así en sclang! es self.clock que el el reloj de la creación del objeto
        self.clock = clock
        clock.sched(0, self)

    @property
    def clock(self):
        return self._clock

    @clock.setter
    def clock(self, clock):
        self._clock = clock
        self._beats = clock.secs2beats(self.seconds) # no llama al setter de beats, convierte los valores en sesgundos de este thread según el nuevo clock

    @property
    def seconds(self):
        # En Routine se queda con los valores de inicialización en __init__
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

    # Se definen en Stream
    # def __iter__(self):
    #     return self
    #
    # # // resume, next, value, run are synonyms
    # def __next__(self): # BUG: ver cómo sería la variante pitónica, luego, por lo pronto creo que no debe declarar inval opcional.
    #     return self.next()
    #
    # def __call__(self, inval=None):
    #     return self.next(inval)

    # TODO: volver a revisar todo, se puede implementar como generador/iterador?
    # TODO: es _RoutineResume
    def next(self, inval=None):
        # _RoutineAlwaysYield (y Done)
        if self.state == self.State.Done:
            #print('*** StopStream from State.Done')
            raise StopStream()

        # prRoutineResume
        # TODO: setea nowExecutingPath, creo que no lo voy a hacer.
        self._previous_rand_state = random.getstate() # NOTE: se podría guardar el estado como un descriptor u otro objeto que implemente un protocolo?
        random.setstate(self._rand_state) # hay que llamarlo ANTES de setear current_TimeThread o usar el atributo privado _rand_state
        self.parent = _main.Main.current_TimeThread
        _main.Main.current_TimeThread = self
        # BUG: le asigna los valores de parent a beats, seconds, clock de este hilo.
        # si el estado del thread es tInit o tSuspended. Es correcto que le pase
        # el reloj? no me doy cuenta cómo, pero en sclang el reloj no se lo cambia
        # cuando con/next/play/value. Realmente no lo entiendo, además ya se están
        # ejecutando en un reloj y no va a cambiar por esto pero si me cambiaría
        # el dato en la estructura, pero en sclang no cambia... (!) en: prRoutineResume
        # hace slotCopy(&thread->clock,&g->thread->clock); L3315. Me faltan cosas.
        # self._clock = self.parent.clock
        self.seconds = self.parent.seconds # seconds setea beats también
        self.state = self.State.Running # lo define en switchToThread al final
        # prRoutineResume
        #     Llama a sendMessage(g, s_prstart, 2), creo que simplemente es una llamada al intérprete que ejecuta prStart definido de Routine
        # TODO: Luego hace para state == tSuspended, y breve para Done (creo que devuelve terminalValue), Running (error), else error.
        try:
            # NOTE: entiendo que esta llamada se ejecuta en el hilo del reloj,
            # no veo que el uso del intérprete tenga un lock. Pero tengo
            # que estar seguro y probar qué pasa con el acceso a los datos.
            # NOTE: que tenga lock cambia la granularidad de la concurrencia
            # lo cuál puede ser útil, ver nota en clock.py.
            # TODO: Reproducir test_concurrente.scd cuando implemente TempoClock.
            if self._iterator is None: # NOTE: esto lo paso acá porque next puede tirar yield exceptions
                if len(inspect.signature(self.func).parameters) == 0: # esto funciona porque es solo para la primera llamada, cuando tampoco existe _iterator, luego no importa si la función tenía argumentos.
                    self._iterator = self.func()
                else:
                    self._iterator = self.func(inval)
                if inspect.isgenerator(self._iterator):
                    self._last_value = next(self._iterator) # NOTE: Igual no anda si este next puede tirar YieldException, por eso quité reset=false, después de tirar esa excepción volvía con StopIteration.
                else:
                    raise StopStream() # NOTE: puede que func sea una función común, esto ignora el valor de retorno que tiene que ser siempre None
            else:
                self._last_value = self._iterator.send(inval) # NOTE: _iterator.send es solo para iteradores generadores, pero en clock está puesto para que evalúe como función lo que no tenga el método next()
            self.state = self.State.Suspended
        # except AttributeError as e:
        #     # Todo esto es para imitar la funcionalidad/comportamiento de las
        #     # corrutinas en sclang. Pero se vuelve poco pitónico, por ejemplo,
        #     # no se pueden usar next() con for, e implica un poco más de carga.
        #     if len(inspect.trace()) > 1: # TODO: sigue solo si la excepción es del frame actual, este patrón se repite en responsedefs y Clock
        #         raise e
        #     if len(inspect.signature(self.func).parameters) == 0: # esto funciona porque es solo para la primera llamada, cuando tampoco existe _iterator, luego no importa si la función tenía argumentos.
        #         self._iterator = self.func()
        #     else:
        #         self._iterator = self.func(inval)
        #     self._last_value = next(self._iterator) # BUG: puede volver a tirar YieldAndReset
        #     self.state = self.State.Suspended
        except StopIteration as e: # NOTE: Las Routine envuelven generadores para evaluarlas con relojes, se puede usar cualquier generador/iterador en el try por eso hay que filtrar esta excepción.
            #print('*** StopIteration')
            # NOTE: compara el nivel de anidamiento a partir del cual el error es de usuario y no de las llamadas de esta implementación.
            if len(inspect.trace()) > 1: # BUG: si no es su propia excepción la tiene que pasar para arriba
                raise StopIteration() from e # BUG: tengo que ver qué pasa con el estado de la rutina en este caso. Si se puede dejar "mentiroso" se elimina este if y terminal_value
            self._iterator = None
            self._terminal_value = None
            self.state = self.State.Done # BUG: esto no sería necesario con StopIteration?
            self._last_value = self._terminal_value
            #print('*** StopStream from except StopIteration')
            raise StopStream # NOTE: *** PARA YIELD FROM
        except YieldAndReset as e:
            #print('*** YieldAndReset')
            self._iterator = None
            self.state = self.State.Init
            self._last_value = e.value
        except AlwaysYield as e:
            #print('*** AlwaysYield')
            self._iterator = None
            self._terminal_value = e.terminal_value
            self.state = self.State.Done
            self._last_value = self._terminal_value
        finally:
            # prRoutineYield # BUG: ver qué pasa con las otras excepciones dentro de send, si afectan este comportamiento
            self._rand_state = random.getstate()
            random.setstate(self._previous_rand_state)
            _main.Main.current_TimeThread = self.parent
            self.parent = None
            # Setea nowExecutingPath, creo que no lo voy a hacer: slotCopy(&g->process->nowExecutingPath, &g->thread->oldExecutingPath);
            # switchToThread(g, parent, tSuspended, &numArgsPushed);
            #     Switchea rand data, pasado acá ARRIBA
            #     Setea el entorno de este hilo, eso no lo voy a hacer.

        #print('return _last_value', self._last_value)
        return self._last_value # BUG: ***************** si se retorna None no funciona yield from en State.Done.

    def reset(self):
        if self is _main.Main.current_TimeThread: # Running
            raise YieldAndReset() # BUG: o tirar otra excpeción? Running es un error en sclang (se llama con yieldAndReset)
        elif self.state == self.State.Init:
            return
        else: #if self.state == self.State.Suspended or self.state == self.State.Done:
            self._iterator = None # BUG: es el único caso que manejo fuera de las excepciones, es el que mejor anda...
            self.state = self.State.Init

    # // the _RoutineStop primitive can't stop the currently running Routine
    # // but a user should be able to use .stop anywhere
    # stop # prStop ->_RoutineStop con otros detalles
    def stop(self):
        if self is _main.Main.current_TimeThread: # Running
            raise AlwaysYield()
        elif self.state == self.State.Done:
            return
        else:
            self._terminal_value = None
            self.state = self.State.Done

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

    def awake(self, beats, seconds, clock): # NOTE: esta función se llama desde C/C++ y tiene la nota "prevent optimization" en cada clase: Function, Nil, Object y Routine pero no en PauseStream que usa beats.
        return self.next(beats)

    # prStart


# decorator syntax
def routine(gen):
    return Routine(gen)


### Condition.sc ###


# NOTE: hay que usar yield from que delega a en un
# subgenerador (factoriza el código a otra función),
# o simplemente hacer return de la función a un yield,
# pero creo que 'yield from' va a ser más explícito.
class Condition():
    def __init__(self, test=False):
        self._test = test
        self._waiting_threads = []

    @property
    def test(self):
        if callable(self._test):
            return self._test()
        else:
            return self._test

    @test.setter
    def test(self, value):
        self._test = value

    def wait(self):
        if not self.test:
            self._waiting_threads.append(
                _main.Main.current_TimeThread.thread_player) # NOTE: problema en realidad, thread_player es callable, si se confunde con un método... no es que me haya pasado.
            yield 'hang'
            #return 'hang'
        else:
            yield 0 # BUG: sclang retorna self (no hace yield), supongo que 0 es como decir que sigua aunque reprograma, pero funciona, ver sync
            #return 0

    def hang(self, value='hang'):
        # // ignore the test, just wait
        self._waiting_threads.append(
            _main.Main.current_TimeThread.thread_player)
        yield value
        #return 'hang'

    def signal(self):
        if self.test:
            time = _main.Main.current_TimeThread.seconds
            tmp_wtt = self._waiting_threads
            self._waiting_threads = []
            for tt in tmp_wtt:
                tt.clock.sched(0, tt)

    def unhang(self):
        # // ignore the test, just resume all waiting threads
        time = _main.Main.current_TimeThread.seconds
        tmp_wtt = self._waiting_threads
        self._waiting_threads = []
        for tt in tmp_wtt:
            tt.clock.sched(0, tt)


class FlowVar():
    def __init__(self, compare='unbound'):
        self._compare = compare
        self._value = compare
        self.condition = Condition(lambda: self._value != self._compare) # BUG: 'unbound') creo que es así en vez de como está, no le veo sentido al argumento inicial más que elegir un valor el cuál seguro no se va a asignar.

    @property
    def value(self):
        yield from self.condition.wait() # BUG: hace yield a la nada
        return self._value

    @value.setter
    def value(self, inval):
        if self._value != self._compare:
            raise Exception('cannot rebind a FlowVar')
        self._value = inval
        self.condition.signal()


### higher level abstractions ###


class FuncStream(Stream):
    pass # TODO


# class OneShotStream(Stream): pass # TODO: ver para qué sirve, la única referencia está en Object:iter, no está documentada.
# class EmbedOnce(Stream): pass # TODO, ver, solo se usa en JITLib, no está documentada.
# class StreamClutch(Stream): pass # TODO: no se usa en la librería de clases, actúa como un filtro, sí está documentada.
# class CleanupStream(Stream): pass # TODO: no se usa en la librería de clases, creo, ver bien, no tiene documentación.


# // PauseStream is a stream wrapper that can be started and stopped.
class PauseStream(Stream):
    def __init__(self, stream, clock=None):
        self._stream = None
        self.original_stream = stream
        self.clock = clock or clk.TempoClock.default # BUG: implementar TempoClock
        self.next_beat = None
        self.stream_has_ended = False
        self.waiting = False # NOTE: era isWaiting, así es más pytónico.
        self.era = 0

    def playing(self): # NOTE: era isPlaying, así es más pytónico.
        return self._stream is not None

    def play(self, clock=None, reset=False, quant=None):
        if self._stream is not None:
            print('already playing')
            return # NOTE: sclang retorna self, esto es un comportamiento global de la librería que habría que ver, pero creo que no es muy Python.
        if reset:
            self.reset()
        self.clock = clock or self.clock or clk.TempoClock.default
        self.stream_has_ended = False
        self.refresh() # //_stream = originalStream;
        self._stream.clock = self.clock
        self.waiting = True # // make sure that accidental play/stop/play sequences don't cause memory leaks
        self.era = sac.CmdPeriod.era

        def pause_stream_play():
            if self.waiting and self.next_beat is None:
                self.clock.sched(0, self)
                self.waiting = False
                mdl.NotificationCenter.notify(self, 'playing')

        if isinstance(self.clock, clk.TempoClock):
            self.clock.play(pause_stream_play, quant) # NOTE: usaba asQuant, la lógica está en el método play de TempoClock.
        else:
            self.clock.play(pause_stream_play)
        mdl.NotificationCenter.notify(self, 'user_played')

    def reset(self):
        self.original_stream.reset()

    def stop(self):
        save_stream = self.stream # NOTE: usa el getter
        self._stop()
        mdl.NotificationCenter.notify(self, 'user_stopped')
        if save_stream is _main.Main.current_TimeThread:
            self.always_yield()

    def _stop(self):
        self._stream = None
        self.waiting = False

    def removed_from_scheduler(self): # NOTE: removeD?
        self.next_beat = None
        self._stop()
        mdl.NotificationCenter.notify(self, 'stopped')

    def stream_error(self):
        self.removed_from_scheduler()
        self.stream_has_ended = True

    def was_stopped(self):
        return ((self.stream_has_ended and self._stream is None) # // stopped by clock or stop-message
               or sac.CmdPeriod.era != self.era) # // stopped by cmd-period, after stream has ended

    def can_pause(self):
        return not self.stream_has_ended

    def pause(self):
        self.stop()

    def resume(self, clock=None, quant=None):
        self.play(clock or self.clock, False, quant) # BUG: en sclang está al revés el or y no tiene lógica porque puede pasar nil

    def refresh(self):
        self.original_stream.thread_player = self # NOTE: threadPlayer en sclang lo definen Object (siempre es this, no se puede setear, esta clase redunda en lo mismo) y Thread (que cambia), acá lo define TimeThread como property y agrego la propiedad acá, es problema esto.
        self._stream = self.original_stream # NOTE: va por separado porque en sclang method_(lala) devuelve this

    def start(self, clock=None, quant=None):
        self.play(clock, True, quant)

    def next(self, inval=None):
        try:
            if self._stream is None: # NOTE: self._stream puede ser nil por el check de abajo o tirar la excepción si finalizó, por eso se necesita esta comprobación, acá los stream no retornan None, tiran excepción.
                raise StopStream('_stream is None')
            next_time = self._stream.next(inval)
            self.next_beat = inval + next_time # // inval is current logical beat
            return next_time
        except StopStream as e:
            self.stream_has_ended = self._stream is not None
            self.removed_from_scheduler()
            raise StopStream('stream finished') from e # BUG: tal vez deba descartar e? (no hacer raise from o poner raise fuera de try/except)

    def awake(self, beats, seconds, clock): # *** NOTE: llama Scheduler wakeup, único caso acá, existe para esto y también se llama desde la implementación en C/C++.
        self._stream.beats = beats
        return self.next(beats)

    @property
    def stream(self):
        return self._stream

    @stream.setter
    def stream(self, value): # NOTE: OJO: No usa este setter en la implementación interna
        self.original_stream.thread_player = None # // not owned any more
        value.thread_player = self
        self.original_stream = value.thread_player
        if self._stream is not None:
            self._stream = value
            self.stream_has_ended = value is not None

    @property
    def thread_player(self):
        return self

    @thread_player.setter
    def thread_player(self, value):
        pass # NOTE: siempre es this para esta clase en sclang, el método se hereda de object y no se puede setear.


# // Task is a PauseStream for wrapping a Routine
class Task(PauseStream):
    def __init__(self, func, clock=None):
        super().__init__(Routine(func), clock) # BUG: qué pasa si func llega a ser una rutina? qué error tira?

    # storeArgs # TODO: ver en general para la librería


# decorator syntax
def task(func):
    return Task(func)


### EventStreamCleanup.sc ###
# // Cleanup functions are passed a flag.
# // The flag is set false if nodes have already been freed by CmdPeriod
# // This caused a minor change to TempoClock:clear and TempoClock:cmdPeriod
class EventStreamCleanup():
    pass # TODO


class EventStreamPlayer(PauseStream):
    def __init__(self, stream, event=None):
        super().__init__(stream)
        self.event = event or evt.Event.default
        self.mute_count = 0
        self.cleanup = EventStreamCleanup()

        def stream_player_generator(in_time):
            while True:
                in_time = yield self._next(in_time) # BUG: creo que es solo yield, falta _next

        self.routine = Routine(stream_player_generator)

    # TODO: todo...


def stream(obj):
    if hasattr(obj, '__stream__'):
        return obj.__stream__()
    if hasattr(obj, '__iter__'):
        def _(inval=None):
            yield from obj
        return Routine(_)

    def _(inval=None):
        while True: # BUG: los Object son streams infinitos el problema es que no se comportan lo mismo con embedInStream, ahí son finitos, valores únicos.
            yield obj
    return Routine(_)


def embed(obj, inval=None):
    if hasattr(obj, '__embed__'):
        return obj.__embed__(inval)
    if hasattr(obj, '__stream__') or hasattr(obj, '__iter__'):
        return  stream(obj).__embed__(inval)

    def _(inval=None):
        yield obj
    return Routine(_).__embed__()
