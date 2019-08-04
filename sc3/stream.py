"""Stream.sc"""

import inspect
import enum
import random

from . import main as _libsc3
from . import clock as clk
from . import functions as fn
from . import model as mdl
from . import systemactions as sac
from . import event as evt


class StopStream(StopIteration):
    pass


class YieldAndReset(Exception):
    def __init__(self, value=None):
        super().__init__()
        self.value = value


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
        return self.next()


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

    def rcompose_binop(self, selector, other):
        return BinaryOpStream(selector, stream(other), self)

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
        a = self.a.next(inval)  # raises StopStream
        return self.selector(a)

    def reset(self):
        self.a.reset()

    # storeOn # TODO


class BinaryOpStream(Stream):
    def __init__(self, selector, a, b):
        self.selector = selector
        self.a = a
        self.b = b

    def next(self, inval=None):
        a = self.a.next(inval)  # raises StopStream
        b = self.b.next(inval)
        return self.selector(a, b)

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
        a = self.a.next(inval)  # raises StopStream
        args = []
        res = None
        for item in self.args:
            res = item.next(inval)  # raises StopStream
            args.append(res)
        return self.selector(a, *args)

    def reset(self):
        self.a.reset()
        for item in self.args:
            item.reset()

    # storeOn # TODO


### Thread.sc ###


class TimeThread(): #(Stream): # BUG: hereda de Stream por Routine y no la usa, pero acá puede haber herencia múltiple. Además, me puse poético con el nombre.
    # ./lang/LangSource/PyrKernel.h: enum { tInit, tStart, tReady, tRunning, tSleeping, tSuspended, tDone };
    # ./lang/LangSource/PyrKernel.h: struct PyrThread : public PyrObjectHdr
    State = enum.Enum('State', ['Init', 'Running', 'Suspended', 'Done']) # NOTE: tStart, tReady y tSleeping no se usan en ninguna parte

    def __init__(self, func):
        # _Thread_Init -> prThreadInit -> initPyrThread
        if not inspect.isfunction(func):
            raise TypeError('Thread func arg is not a function')

        # BUG: ver test_clock_thread.scd, estos valores no tienen efecto porque
        # se sobreescribe el reloj por TempoClock.default en Stream:play
        # y Routine:run vuelve a escribir SystemClock (cuando ya lo hizo en
        # PyrPrimitive). La única manera de usar el reloj heredado es llamando a next.
        self._beats = _libsc3.main.current_tt.beats
        self._seconds = _libsc3.main.current_tt.seconds # ojo que tienen setters porque son dependientes...

        # BUG: ver qué pasa con terminalValue <nextBeat, <>endBeat, <>endValue;
        # se usan en la implementación a bajo nivel de los relojes.

        self.func = func
        self.state = self.State.Init
        if _libsc3.main.current_tt.clock is None: # BUG: si mainThread siempre devuelve SystemClock y siempre es curThread por defecto, esta comprobación es necesaria?
            self._clock = clk.SystemClock
        else:
            self._clock = _libsc3.main.current_tt.clock

        # NOTA: No guarda la propiedad <parent cuando crea el thread, es
        # &g->thread que la usa para setear beats y seconds pero no la guarda,
        # la setea luego en algún lugar, con el cambio de contexto, supongo,
        # y tiene valor solo mientras la rutina está en ejecución. Ver test_clock_thread.scd
        self.parent = None
        self.state = self.State.Init
        self._thread_player = None
        self._rgen = _libsc3.main.current_tt.rgen

        # para Routine
        self._iterator = None # se inicializa luego de la excepción
        self._last_value = None
        self._sentinel = object()
        self._terminal_value = self._sentinel

        # NOTE: No se usan entornos como en sclang, a lo sumo se podrían pasar diccionarios.
        # self.environment = current_Environment # acá llama al slot currentEnvironment de Object y lo setea al del hilo
        # NOTE: acá setea nowExecutingPath de la instancia de Process (Main), no va acá.
        # if(g->process) { // check we're not just starting up
        #     slotCopy(&thread->executingPath,&g->process->nowExecutingPath);

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    @property
    def clock(self): # NOTE: mainThread clock (SystemClock) no se puede cambiar. Esto es distinto en sclang que define el setter en esta clase pero solo lo usa Routine.
        return clk.SystemClock

    @clock.setter
    def clock(self, value): # NOTE: se necesita por compatibilidad/generalidad para no checkear qué reloj es. Routine sobreescribe.
        pass

    @property
    def seconds(self):
        # NOTE: En la documentación de Thread:
        # // When code is run from the code editor, the command line, or in
        # // response to OSC and MIDI messages, the main Thread's logical
        # // time is set to the current physical time (see Process: *elapsedTime).
        # NOTE: En Python es cada vez que se requiere el tiempo de una ruitna.
        if self is _libsc3.main.main_tt:
            _libsc3.main.update_logical_time()
        return self._seconds

    @seconds.setter
    def seconds(self, seconds):
        self._seconds = seconds
        self._beats = self.clock.secs2beats(seconds)

    @property
    def beats(self):
        # NOTE: Ver seconds arriba.
        if self is _libsc3.main.main_tt:
            _libsc3.main.update_logical_time()
        return self._beats

    @beats.setter
    def beats(self, beats):
        self._beats = beats
        self._seconds = self.clock.beats2secs(beats)

    def playing(self): # BUG: era is_playing, está pitonizado
        return self.state == self.State.Suspended

    @property
    def thread_player(self):
        if self._thread_player is not None:
            return self._thread_player
        else:
            if self.parent is not None\
            and self.parent is not _libsc3.main.main_tt:
                return self.parent.thread_player()
            else:
                return self

    @thread_player.setter
    def thread_player(self, player): # BUG: se usa en Stream.sc que no está implementada
        self._thread_player = player

    @property
    def rgen(self):
        return self._rgen

    def rand_seed(self, x):
        # NOTE: La rutinas heredan el generador de parent y solo lo cambian si
        # NOTE: se siembra. Así se comporta sclang. Hay que usar sc3.random.
        self._rgen = random.Random(x)

    @property
    def rand_state(self):
        return self._rgen.getstate()

    @rand_state.setter
    def rand_state(self, data):
        self._rgen.setstate(data)

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


class Routine(TimeThread, Stream):
    @classmethod
    def run(cls, func, clock=None, quant=None):
        obj = cls(func)
        obj.play(clock, quant)
        return obj

    def play(self, clock=None, quant=None):
        '''el argumento clock pordía soportar un string además de un objeto
        clock, 'clojure', para el reloj en que se creó el objeto Routine,
        'parent' para el reloj de la rutina desde la que se llama a play y
        'default' para TempoClock.default (global), pero hay que comprobar
        que en la creación o antes de llamar a play no se haya seteado
        un reloj 'custom'. El reloj no se puede cambiar una vez que se llamó
        a run o play.'''
        clock = clock or _libsc3.main.current_tt.clock # BUG: perooooooo! esto no es así en sclang! es self.clock que el el reloj de la creación del objeto
        self.clock = clock
        if isinstance(self.clock, clk.TempoClock):
            self.clock.play(self, quant) # clk.Quant.as_quant(quant)) # NOTE: no se necesita porque lo crea TempoClock.play
        else:
            self.clock.play(self)
        # NOTE: no estoy retornando self a propósito, ver si conviene que
        # NOTE: solor retornen self los métodos play que devuelven una rutina
        # NOTE: creada a partir de otro objeto, por ejemplo, Pattern.

    @property
    def clock(self):
        return self._clock

    @clock.setter
    def clock(self, clock):
        self._clock = clock
        self._beats = clock.secs2beats(self.seconds)

    def next(self, inval=None):
        # _RoutineAlwaysYield (y Done)
        if self.state == self.State.Done:
            if self._terminal_value is self._sentinel:
                raise StopStream('Routine stopped')
            else:
                return self._terminal_value

        # prRoutineResume
        self.parent = _libsc3.main.current_tt
        _libsc3.main.current_tt = self
        self.seconds = self.parent.seconds
        self.state = self.State.Running

        try:
            # TODO: Reproducir test_concurrente.scd cuando implemente TempoClock.
            if self._iterator is None:
                if len(inspect.signature(self.func).parameters) == 0:
                    self._iterator = self.func()
                else:
                    self._iterator = self.func(inval)
                if inspect.isgenerator(self._iterator):
                    self._last_value = next(self._iterator)
                else:
                    raise AlwaysYield()
            else:
                self._last_value = self._iterator.send(inval)
            self.state = self.State.Suspended
        except StopStream as e:
            self._iterator = None
            self._last_value = None
            self.state = self.State.Done
            return self._last_value
        except StopIteration as e:
            self._iterator = None
            self._last_value = None
            self.state = self.State.Done
            raise StopStream from e
        except YieldAndReset as e:
            self._iterator = None
            self.state = self.State.Init
            self._last_value = e.value
        except AlwaysYield as e:
            self._iterator = None
            self._terminal_value = e.terminal_value
            self.state = self.State.Done
            self._last_value = self._terminal_value
        finally:
            _libsc3.main.current_tt = self.parent
            self.parent = None

        return self._last_value

    def reset(self):
        if self is _libsc3.main.current_tt: # Running
            raise YieldAndReset()
        else:
            self._iterator = None
            self.state = self.State.Init

    # stop -> prStop -> _RoutineStop
    def stop(self):
        if self is _libsc3.main.current_tt: # Running
            raise StopStream()
        else:
            self.state = self.State.Done

    # // resume, next, value, run are synonyms
    # next, ver arriba
    # value
    # resume
    # run (de instancia, no va)

    # valueArray se define como ^this.value(inval), opuesto a Stream valueArray que no recibe inval... BUG del tipo desprolijidad? o hay una razón?

    # p ^Prout(func)
    # storeArgs
    # storeOn

    # // PRIVATE

    def __awake__(self, beats, seconds, clock):
        return self.next(beats)

    # prStart


# decorator syntax
class routine():
    def __new__(cls, func):
        return Routine(func)

    @staticmethod
    def run(clock=None, quant=None):
        def make_routine(func):
            obj = Routine(func)
            obj.play(clock, quant)
            return obj
        return make_routine


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
                _libsc3.main.current_tt.thread_player) # NOTE: problema en realidad, thread_player es callable, si se confunde con un método... no es que me haya pasado.
            yield 'hang'
            #return 'hang'
        else:
            yield 0 # BUG: sclang retorna self (no hace yield), supongo que 0 es como decir que sigua aunque reprograma, pero funciona, ver sync
            #return 0

    def hang(self, value='hang'):
        # // ignore the test, just wait
        self._waiting_threads.append(
            _libsc3.main.current_tt.thread_player)
        yield value
        #return 'hang'

    def signal(self):
        if self.test:
            time = _libsc3.main.current_tt.seconds
            tmp_wtt = self._waiting_threads
            self._waiting_threads = []
            for tt in tmp_wtt:
                tt.clock.sched(0, tt)

    def unhang(self):
        # // ignore the test, just resume all waiting threads
        time = _libsc3.main.current_tt.seconds
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
            return self # NOTE: sclang retorna self porque los Patterns devuelven la Routine que genéra este método.
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
            self.clock.play(pause_stream_play, quant) # clk.Quant.as_quant(quant)) NOTE: no se necesita porque lo crea TempoClock.play
        else:
            self.clock.play(pause_stream_play)
        mdl.NotificationCenter.notify(self, 'user_played')
        return self

    def reset(self):
        self.original_stream.reset()

    def stop(self):
        save_stream = self.stream # NOTE: usa el getter
        self._stop()
        mdl.NotificationCenter.notify(self, 'user_stopped')
        if save_stream is _libsc3.main.current_tt:
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
        return ((not self.stream_has_ended and self._stream is None) # // stopped by clock or stop-message
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
            next_time = self._stream.next(inval) # NOTE: tira StopStream
            self.next_beat = inval + next_time # // inval is current logical beat
            return next_time
        except StopStream as e:
            self.stream_has_ended = self._stream is not None
            self.removed_from_scheduler()
            raise StopStream('stream finished') from e # BUG: tal vez deba descartar e? (no hacer raise from o poner raise fuera de try/except)

    def __awake__(self, beats, seconds, clock):
        if self._stream: # NOTE: nil.beats = beats -> nil en sclang, stop() setea stream a nil. StopStream DEBE ser llamado desde next por consistencia lógica aunque en este caso es redundante.
            self._stream.beats = beats
        return self.next(beats)

    @property
    def stream(self):
        return self._stream

    @stream.setter
    def stream(self, value): # NOTE: OJO: No usa este setter en la implementación interna
        self.original_stream.thread_player = None # // not owned any more
        if value is not None:
            value.thread_player = self
        self.original_stream = value
        if self._stream is not None:
            self._stream = value
            self.stream_has_ended = value is None

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
    def __init__(self):
        self.functions = set() # // cleanup functions from child streams and parent stream

    def add_function(self, event, func):
        if isinstance(event, dict):
            self.functions.add(func)
            if 'add_to_cleanup' not in event:
                event.add_to_cleanup = []
            event.add_to_cleanup.append(func)

    def add_node_cleanup(self, event, func):
        if isinstance(event, dict):
            self.functions.add(func)
            if 'add_to_node_cleanup' not in event:
                event.add_to_node_cleanup = []
            event.add_to_node_cleanup.append(func)

    def update(self, event):
        if isinstance(event, dict):
            if 'add_to_node_cleanup' in event:
                self.functions.update(event.add_to_node_cleanup)
            if 'add_to_cleanup' in event:
                self.functions.update(event.add_to_cleanup)
            if 'remove_from_cleanup' in event:
                for item in event.remove_from_cleanup:
                    self.functions.discard(item)
            print('*** ver por qué EventStreamCleanup.update retorna el argumento event (además inalterado)')
            return event # TODO: Why?

    def exit(self, event, free_nodes=True):
        if isinstance(event, dict):
            self.update(event)
            for func in self.functions:
                func(free_nodes)
            if 'remove_from_cleanup' not in event:
                event.remove_from_cleanup = [] # NOTE: es necesario porque hace reasignación del array como si creara uno nuevo, por eso entiendo que es un array también.
            event.remove_from_cleanup.extend(self.functions)
            self.clear()
            print('*** ver por qué EventStreamCleanup.exit retorna el argumento event (aunque acá sí alterado)')
            return event

    def terminate(self, free_nodes=True):
        for func in self.functions:
            func(free_nodes)
        self.clear()

    def clear(self): # NOTE: no usar para init, así es más claro.
        self.functions = set()


class EventStreamPlayer(PauseStream):
    def __init__(self, stream, event=None):
        super().__init__(stream)
        self.event = event or evt.Event.default() # BUG: tal vez debería ser una property de clase? o que todos los default sean funciones (SIMPLIFICA EL CÓDIGO) o propiedades. Pero Event *default crea un nuevo evento cada vez.
        self.mute_count = 0
        self.cleanup = EventStreamCleanup()

        def stream_player_generator(in_time):
            while True:
                in_time = yield self._next(in_time)

        self.routine = Routine(stream_player_generator)

    # // freeNodes is passed as false from
    # // TempoClock:cmdPeriod
    def removed_from_scheduler(self, free_nodes=True):
        self.next_beat = None # BUG?
        self.cleanup.terminate(free_nodes)
        self._stop()
        mdl.NotificationCenter.notify(self, 'stopped')

    def _stop(self):
        self._stream = None
        self.next_beat = None # BUG? lo setea a nil acá y en el método de arriba que llama a este (no debería estar allá), además stop abajo es igual que arriba SALVO que eso haga que se detenga antes por alguna razón.
        self.waiting = False

    def stop(self):
        self.cleanup.terminate()
        self._stop()
        mdl.NotificationCenter.notify(self, 'user_stopped')

    def reset(self):
        self.routine.reset()
        super().reset()

    def mute(self):
        self.mute_count += 1

    def unmute(self):
        self.mute_count -= 1

    def can_pause(self):
        return not self.stream_has_ended and len(self.cleanup.functions) == 0

    def next(self, in_time):
        return self.routine.next(in_time)

    def _next(self, in_time):
        try: # BUG(s). Revisar next de PauseStream
            if self._stream is None:
                raise StopStream()
            else:
                out_event = self._stream.next(self.event.copy())
                next_time = out_event.play_and_delta(self.cleanup, self.mute_count > 0)
                # if (nextTime.isNil) { this.removedFromScheduler; ^nil }; # *** BUG ***
                # BUG: para event.play_and_delta/event.delta, los patterns no van a devolver
                # BUG: nil y setear la llave, van a tirar StopStream.
                # BUG: Igualmente tampoco encuentro un caso que de nil en sclang,
                # BUG: outEvent no puede ser nil porque comprueba, playAndDelta
                # BUG: no parece que pueda retornar nil (según pruebas con Pbind, \delta, nil va al if, (delta: nil) es 0). VER _Event_Delta
                self.next_beat = in_time + next_time # // inval is current logical beat
                return next_time
        except StopStream:
            self.stream_has_ended = self._stream is not None
            self.cleanup.clear()
            self.removed_from_scheduler() # BUG? Hay algo raro, llama cleanup.clear() en la línea anterior, que borras las funciones de cleanup, pero luego llama a cleanup.terminate a través removed_from_scheduler en esta línea que evalúa las funciones que borró (no las evalúa)
            raise StopStream() # NOTE: podría ir afuera

    def as_event_stream_player(self): # BUG: VER: lo implementan Event, EventStreamPlayer, Pattern y Stream, parece protocolo.
        return self

    def play(self, clock=None, reset=False, quant=None):
        if self._stream is not None:
            print('already playing')
            return self
        if reset:
            self.reset()
        self.clock = clock or self.clock or clk.TempoClock.default
        self.stream_has_ended = False
        self._stream = self.original_stream
        self._stream.clock = self.clock
        self.waiting = True # // make sure that accidental play/stop/play sequences don't cause memory leaks
        self.era = sac.CmdPeriod.era
        quant = clk.Quant.as_quant(quant) # NOTE: se necesita porque lo actualiza event.sync_with_quant
        self.event = self.event.sync_with_quant(quant) # NOTE: actualiza el evento y retorna una copia o actualiza el objeto Quant pasado.

        def event_stream_play():
            if self.waiting and self.next_beat is None:
                self.clock.sched(0, self)
                self.waiting = False
                mdl.NotificationCenter.notify(self, 'playing')

        if isinstance(self.clock, clk.TempoClock):
            self.clock.play(event_stream_play, quant)
        else:
            self.clock.play(event_stream_play)
        mdl.NotificationCenter.notify(self, 'user_played')
        return self


def stream(obj):
    if hasattr(obj, '__stream__'):
        return obj.__stream__()

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
