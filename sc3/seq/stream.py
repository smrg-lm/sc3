"""Stream.sc"""

from abc import ABC, abstractmethod
import inspect
import enum
import threading
import random
import logging

from ..base import main as _libsc3
from ..base import functions as fn
from ..base import model as mdl
from ..base import systemactions as sac
from . import clock as clk
from . import event as evt


_logger = logging.getLogger(__name__)


class StopStream(StopIteration):
    pass


class YieldAndReset(Exception):
    def __init__(self, yield_value=None):
        super().__init__()  # Doesn't stores yield_value in self.args.
        self.yield_value = value


class AlwaysYield(Exception):
    def __init__(self, terminal_value=None):
        super().__init__()  # Doesn't stores terminal_value in self.args.
        self.terminal_value = terminal_value


class Stream(fn.AbstractFunction, ABC):
    '''
    Streams are iterator-generators compatible objects that implement an
    specific interface to interact with clocks and patterns.
    '''

    ### Iterator protocol ###

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()


    ### Stream protocol ###

    def __stream__(self):
        '''Returns a Stream object, most likely a Routine.'''
        return self

    def __embed__(self, inval=None):
        '''
        Returns generator-iterator that recursively embeds cointained
        sub-streams.
        '''
        try:
            while True:
                yield self.next(inval)
        except StopStream:
            return

    @abstractmethod
    def next(self, inval=None):
        pass


    # def stream_arg(self): # BUG: se usa para Pcollect, Pselect, Preject, el método lo definen Object y Pattern también.
    #     return self

    def all(self, inval=None):
        '''Same as list(stream) but with inval argument.'''
        lst = []
        try:
            while True:
                lst.append(self.next(inval))
        except StopStream:
            pass
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


    ### AbstractFunction interface ###

    def _compose_unop(self, selector):
        return UnaryOpStream(selector, self)

    def _compose_binop(self, selector, other):
        return BinaryOpStream(selector, self, stream(other)) # BUG: BUG: en sclang usa el adverbio y si es nil la operación binaria retorna nil, tal vez porque sin él no hace la operación elemento a elemento de los streams.

    def _rcompose_binop(self, selector, other):
        return BinaryOpStream(selector, stream(other), self)

    def _compose_narop(self, selector, *args):
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


class FunctionStream(Stream):  # Was FuncStream
    # Functions could use StopStream as sclang nil but is not nice.
    def __init__(self, next_func, reset_func=None, data=None):
        self.next_func = next_func
        self._next_nargs = len(inspect.signature(self.next_func).parameters)
        self.reset_func = reset_func or (lambda data: None)
        self._reset_nargs = len(inspect.signature(self.reset_func).parameters)
        self.data = data

    def next(self, inval=None):
        # return fn.value(self.next_func, inval, self.data)  # Not cheap.
        # return self.next_func(inval, self.data)  # Mandatory
        if self._next_nargs > 1:
            return self.next_func(inval, self.data)
        elif self._next_nargs > 0:
            return self.next_func(inval)
        else:
            return self.next_func()

    def reset(self):
        # fn.value(self.reset_func, self.data)  # Not cheap.
        # self.reset_func(self.data)  # Mandatory.
        if self._reset_nargs > 0:
            self.reset_func(self.data)
        else:
            self.reset_func()

    # storeArgs


### Thread.sc ###


class TimeThread():
    State = enum.Enum('State', ['Init', 'Running', 'Suspended', 'Done'])

    def __init__(self, func):
        if not inspect.isfunction(func):
            raise TypeError('TimeThread argument is not a function')

        self.func = func
        self._func_has_inval = (  # Maybe it would be better to require the argument.
            len(inspect.signature(self.func).parameters) > 0)
        self._func_isgenfunc = inspect.isgeneratorfunction(self.func)

        self.parent = None
        self.state = self.State.Init
        self._state_cond = threading.Condition(threading.RLock())
        # _seconds need alias to avoid
        # _MainTimeThread getter in Routine.next().
        self._m_seconds = 0.0
        self._clock = None
        self._thread_player = None
        self._rgen = _libsc3.main.current_tt.rgen

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    @property
    def _seconds(self):
        return self._m_seconds

    @_seconds.setter
    def _seconds(self, seconds):
        self._m_seconds = seconds

    @property
    def is_playing(self):
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
    def thread_player(self, player):
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

    # TODO: ver pickling
    # storeOn { arg stream; stream << "nil"; }
    # archiveAsCompileString { ^true }
    # checkCanArchive { "cannot archive Threads".warn }


class _MainTimeThread(TimeThread):
    def __init__(self):  # override
        self.parent = None
        self.func = None
        self.state = self.State.Init
        self._m_seconds = 0.0
        self._clock = None
        self._thread_player = None

    @property
    def _seconds(self):  # override
        # _MainThread set the current physical time when this
        # property is invoked and then spreads to child routines.
        _libsc3.main.update_logical_time()
        return self._m_seconds

    @_seconds.setter
    def _seconds(self, seconds):
        self._m_seconds = seconds

    @property
    def rgen(self):  # override
        return _libsc3.main._rgen

    def rand_seed(self, x):  # override
        pass


class Routine(TimeThread, Stream):
    def __init__(self, func):
        super().__init__(func)
        self._iterator = None
        self._last_value = None
        self._sentinel = object()
        self._terminal_value = self._sentinel

        # <nextBeat, <>endBeat, <>endValue are used
        # low level in clocks, only for PauseStream?

    @classmethod
    def run(cls, func, clock=None, quant=None):
        obj = cls(func)
        obj.play(clock, quant)
        return obj

    def play(self, clock=None, quant=None):
        clock = clock or clk.SystemClock
        clock.play(self, quant)
        # Pattern.play return the stream, maybe for API usage constency
        # Stream.play should return self, but I'm not sure.
        # return self

    def next(self, inval=None):
        with self._state_cond:
            # _RoutineAlwaysYield (y Done)
            if self.state == self.State.Done:
                if self._terminal_value is self._sentinel:
                    raise StopStream
                else:
                    return self._terminal_value

            self.parent = _libsc3.main.current_tt
            _libsc3.main.current_tt = self
            if self._clock:
                self._m_seconds = self.parent._m_seconds
            else:
                self._m_seconds = self.parent._seconds

            try:
                self.state = self.State.Running
                if self._iterator is None:
                    if self._func_isgenfunc:
                        if self._func_has_inval:
                            self._iterator = self.func(inval)
                        else:
                            self._iterator = self.func()
                        self._last_value = next(self._iterator)
                    else:
                        if self._func_has_inval:
                            self.func(inval)
                        else:
                            self.func()
                        raise AlwaysYield()
                else:
                    self._last_value = self._iterator.send(inval)
                self.state = self.State.Suspended
            except StopStream:
                self._iterator = None
                self._last_value = None
                self._clock = None
                self.state = self.State.Done
                raise
            except StopIteration:
                self._iterator = None
                self._last_value = None
                self._clock = None
                self.state = self.State.Done
                raise StopStream
            except YieldAndReset as e:
                self._iterator = None
                self.state = self.State.Init
                self._last_value = e.yield_value
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
        with self._state_cond:
            if self.state == self.State.Running:
                raise Exception(
                    'Routine cannot reset itself except by YieldAndReset')
            else:
                self._iterator = None
                self.state = self.State.Init

    def stop(self):
        with self._state_cond:
            if self.state == self.State.Running:
                raise StopStream
            else:
                self._iterator = None
                self._last_value = None
                self._clock = None
                self.state = self.State.Done

    # p ^Prout(func)
    # storeArgs
    # storeOn

    def __awake__(self, beats, seconds, clock):
        return self.next(beats)


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
            tmp_wtt = self._waiting_threads
            self._waiting_threads = []
            for tt in tmp_wtt:
                tt._clock.sched(0, tt)

    def unhang(self):
        # // ignore the test, just resume all waiting threads
        tmp_wtt = self._waiting_threads
        self._waiting_threads = []
        for tt in tmp_wtt:
            tt._clock.sched(0, tt)


class FlowVar():
    def __init__(self, compare='unbound'):
        self._compare = compare
        self._value = compare
        self.condition = Condition(lambda: self._value != self._compare) # BUG: 'unbound') creo que es así en vez de como está, no le veo sentido al argumento inicial más que elegir un valor el cuál seguro no se va a asignar.

    @property
    def value(self):
        yield from self.condition.wait()  # *** BUG: hace yield a la nada, y es un descriptor.
        return self._value  # *** BUG: y los generadores ignoran el valor de retorno.

    @value.setter
    def value(self, inval):
        if self._value != self._compare:
            raise Exception('cannot rebind a FlowVar')
        self._value = inval
        self.condition.signal()


### Higher level abstractions ###


# class OneShotStream(Stream): ... # TODO: ver para qué sirve, la única referencia está en Object:iter, no está documentada.
# class EmbedOnce(Stream): ... # TODO, ver, solo se usa en JITLib, no está documentada.
# class StreamClutch(Stream): ... # TODO: no se usa en la librería de clases, actúa como un filtro, sí está documentada.
# class CleanupStream(Stream): ... # TODO: no se usa en la librería de clases, creo, ver bien, no tiene documentación.


class PauseStream(Stream):
    # // PauseStream is a stream wrapper that can be started and stopped.
    def __init__(self, stream):
        self._stream = stream
        self._clock = None
        self._next_beat = None
        self._is_waiting = False
        self._is_playing = False
        self._era = 0

    @property
    def is_playing(self):
        return self._is_playing

    def play(self, clock=None, reset=False, quant=None):
        if self._is_playing:
            return
            # Pattern.play return the stream, maybe for API usage constency
            # Stream.play should return self, but I'm not sure.
            # return self
        if reset:
            self.reset()
        self._stream.thread_player = self
        self._clock = clock or self._clock or clk.SystemClock
        self._stream._clock = self._clock  # BUG: threading.
        self._is_waiting = True # // make sure that accidental play/stop/play sequences don't cause memory leaks
        self._is_playing = True
        self._era = sac.CmdPeriod.era

        def pause_stream_play():
            if self._is_waiting and self._next_beat is None:
                self._clock.sched(0, self)
                self._is_waiting = False
                mdl.NotificationCenter.notify(self, 'playing')

        self._clock.play(pause_stream_play, quant)
        mdl.NotificationCenter.notify(self, 'user_played')
        # Pattern.play return the stream, maybe for API usage constency
        # Stream.play should return self, but I'm not sure.
        # return self

    def reset(self):
        self._stream.reset()

    def stop(self):
        self._stop()
        with self._stream._state_cond:
            if self._stream.state == self._stream.State.Running:
                raise StopStream
            else:
                self._stream.stop()
        mdl.NotificationCenter.notify(self, 'user_stopped')

    def _stop(self):
        self._is_playing = False
        self._is_waiting = False

    def removed_from_scheduler(self):
        self._next_beat = None
        self._stop()
        mdl.NotificationCenter.notify(self, 'stopped')

    def pause(self):
        self._stop()
        mdl.NotificationCenter.notify(self, 'user_paused')

    def resume(self, clock=None, quant=None):
        self.play(clock, False, quant)

    def next(self, inval=None):
        try:
            if not self._is_playing:
                raise StopStream
            next_time = self._stream.next(inval)  # raises StopStream
            self._next_beat = inval + next_time  # // inval is current logical beat
            return next_time
        except StopStream:
            self.removed_from_scheduler()
            raise

    def __awake__(self, beats, seconds, clock):
        return self.next(beats)

    @property
    def thread_player(self):
        return self

    @thread_player.setter
    def thread_player(self, value):
        pass


class Task(PauseStream):
    # // Task is a PauseStream for wrapping a Routine.
    def __init__(self, func):
        super().__init__(Routine(func))  # BUG: qué pasa si func llega a ser una rutina? qué error tira?

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

    def clear(self):
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
        self._next_beat = None # BUG?
        self.cleanup.terminate(free_nodes)
        self._stop()
        mdl.NotificationCenter.notify(self, 'stopped')

    def _stop(self):
        self._is_playing = False
        self._is_waiting = False
        self._next_beat = None # BUG? lo setea a nil acá y en el método de arriba que llama a este (no debería estar allá), además stop abajo es igual que arriba SALVO que eso haga que se detenga antes por alguna razón.

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

    def next(self, in_time):
        return self.routine.next(in_time)

    def _next(self, in_time):
        try:
            if not self._is_playing:
                raise StopStream
            out_event = self._stream.next(self.event.copy())  # raises StopStream
            next_time = out_event.play_and_delta(self.cleanup, self.mute_count > 0)
            # if (nextTime.isNil) { this.removedFromScheduler; ^nil };
            # BUG: For event.play_and_delta/event.delta patterns won't return
            # nil and set the key, they will raise StopStream. Equally I either
            # can't find a case of nil sclang, outEvent can't return nil because
            # it checks, playAndDelta don't seem to return nil. Tested with
            # Pbind, \delta, nil goes to if, (delta: nil) is 0. See _Event_Delta.
            self._next_beat = in_time + next_time  # // inval is current logical beat
            return next_time
        except StopStream:
            self.cleanup.clear()
            self.removed_from_scheduler() # BUG? Hay algo raro, llama cleanup.clear() en la línea anterior, que borras las funciones de cleanup, pero luego llama a cleanup.terminate a través removed_from_scheduler en esta línea que evalúa las funciones que borró (no las evalúa)
            raise

    def as_event_stream_player(self): # BUG: VER: lo implementan Event, EventStreamPlayer, Pattern y Stream, parece protocolo.
        return self

    def play(self, clock=None, reset=False, quant=None):
        if self._is_playing:
            return
            # Pattern.play return the stream, maybe for API usage constency
            # Stream.play should return self, but I'm not sure.
            # return self
        if reset:
            self.reset()
        self._clock = clock or self._clock or clk.SystemClock
        self._stream._clock = self._clock
        self._is_waiting = True # // make sure that accidental play/stop/play sequences don't cause memory leaks
        self._is_playing = True
        self._era = sac.CmdPeriod.era
        quant = clk.Quant.as_quant(quant) # NOTE: se necesita porque lo actualiza event.sync_with_quant
        self.event = self.event.sync_with_quant(quant) # NOTE: actualiza el evento y retorna una copia o actualiza el objeto Quant pasado.

        def event_stream_play():
            if self._is_waiting and self._next_beat is None:
                self._clock.sched(0, self)
                self._is_waiting = False
                mdl.NotificationCenter.notify(self, 'playing')

        self._clock.play(event_stream_play, quant)
        mdl.NotificationCenter.notify(self, 'user_played')
        # Pattern.play return the stream, maybe for API usage constency
        # Stream.play should return self, but I'm not sure.
        # return self


class SingleValueStream(Stream):
    def __init__(self, value):
        self.value = value


    ### Iterator protocol ###

    def __next__(self):
        return self.value


    ### Stream protocol ###

    def __embed__(self, inval=None):
        # Common objects are infinite streams returning themselves. However,
        # when using embedInStream they become an unique value stream.
        yield self.value

    def next(self, inval=None):
        return self.value


class PatternValueStream(Stream):
    def __init__(self, pattern):
        self.pattern = pattern
        self._stream = None


    ### Stream protocol ###

    def next(self, inval=None):
        try:
            if self._stream is None:
                self._stream = self.pattern.__embed__(inval)
                return next(self._stream)
            else:
                return self._stream.send(inval)
        except StopIteration:
            raise StopStream


class PatternEventStream(PatternValueStream):
    ### Stream protocol ###

    def next(self, inevent=None):
        try:
            inevent = dict() if inevent is None else inevent  # *** TODO: Default type, it might end up being dict.
            if self._stream is None:
                self._stream = self.pattern.__embed__(inevent)
                return next(self._stream)
            else:
                return self._stream.send(inevent)
        except StopIteration:
            raise StopStream


def stream(obj):
    '''Converts any object in a Stream.'''

    if hasattr(obj, '__stream__'):
        return obj.__stream__()
    else:
        return SingleValueStream(obj)


def embed(obj, inval=None):
    '''
    Converts any object in a Stream and returns its embeddable form passing
    inval to the `next` calls.
    '''

    if hasattr(obj, '__embed__'):
        return obj.__embed__(inval)
    else:
        return SingleValueStream(obj).__embed__(inval)
