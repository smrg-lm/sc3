"""Thread.sc & Stream.sc part 1"""

from abc import ABC, abstractmethod
import inspect
import enum
import threading
import random
import logging

from . import main as _libsc3
from . import functions as fn
from . import clock as clk


__all__ = ['Routine', 'routine', 'FunctionStream', 'Condition', 'FlowVar']

_logger = logging.getLogger(__name__)


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


### Stream.sc part 1 ###


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
                inval = yield self.next(inval)
        except StopStream:
            return inval

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


# NOTE: See BinaryOpXStream implementation options. Is not possible to
# implemente without a special function operation.


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


### Type Streams ###


class ValueStream(Stream):
    def __init__(self, value):
        self.value = value


    ### Iterator protocol ###

    def __next__(self):
        return self.value


    ### Stream protocol ###

    def __embed__(self, inval=None):
        # Common objects are infinite streams returning themselves. However,
        # when using embedInStream they become an unique value stream.
        return (yield self.value)

    def next(self, inval=None):
        return self.value


class DictionaryStream(ValueStream):
    ### Iterator protocol ###

    def __next__(self):
        # Object.composeEvent
        return self.value.copy()


    ### Stream protocol ###

    def __embed__(self, inevent=None):
        # Dictionary.embedInStream
        # func = self.value.get('embed', None)
        # if func is not None:
        #     yield from func(self.value, inevent)
        if inevent is None:
            return (yield self.value)
        else:
            inevent = inevent.copy()
            inevent.update(self.value)
            return (yield inevent)

    def next(self, inevent=None):
        # Event.next
        if inevent is None:
            # Object.composeEvent
            return self.value.copy()
        else:
            # Environment.composeEvent
            inevent = inevent.copy()
            inevent.update(self.value)
            return inevent


### Module functions ###


def stream(obj):
    '''Converts any object in a Stream.'''

    if hasattr(obj, '__stream__'):
        return obj.__stream__()
    else:
        if isinstance(obj, dict):
            return DictionaryStream(obj)
        else:
            return ValueStream(obj)


def embed(obj, inval=None):
    '''
    Converts any object in a Stream and returns its embeddable form passing
    inval to the `next` calls.
    '''

    if hasattr(obj, '__embed__'):
        return obj.__embed__(inval)
    else:
        if isinstance(obj, dict):
            return DictionaryStream(obj).__embed__(inval)
        else:
            return ValueStream(obj).__embed__(inval)
