"""Thread.sc & Stream.sc part 1"""

from abc import ABC, abstractmethod
import inspect
import enum
import threading
import random
import logging

from . import main as _libsc3
from . import absobject as aob
from . import clock as clk


# NRT uses the name _libsc3 through _init before ClassLibrary initialization.
# OscScore may be created on a different way later. This late import was
# originally defined to reduce cyclic relations and import time when the
# library doesn't need to be completely initialized to write an extension.
# from . import classlibrary as clb
# clb.ClassLibrary.late_imports(__name__, ('sc3.base.main', '_libsc3'))


__all__ = [
    'Routine', 'routine', 'FunctionStream',
    'Condition', 'FlowVar', 'stream', 'embed']


_logger = logging.getLogger(__name__)


### Thread.sc ###


class TimeThread():
    State = enum.Enum('State', [
        'Init', 'Running', 'Suspended', 'Paused', 'Done'])

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
        self._m_seconds = 0.0
        self._clock = None
        self._thread_player = None
        self._rand_seed = None
        self._rgen = _libsc3.main.current_tt._rgen

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    # *** TIENE QUE VOLVER A SER PÚBLICO, SE USA MUCHO EN LA DOCUMENTACIÓN,
    # *** RECORDAR POR QUÉ EL ALIAS, CREO PORQUE LO CONVERTÍ EN INTERNO,
    # *** FUE UN ERROR. ANOTAS CON # Updates logical time. LAS LLAMADAS
    # *** A SECONDS (QUE AHORA SON _SECONDS).
    @property
    def seconds(self):
        return self._m_seconds

    @property
    def is_playing(self):
        return (self.state == self.State.Suspended or
                self is _libsc3.main.current_tt)

    @property
    def thread_player(self):
        if self._thread_player is not None:
            return self._thread_player
        else:
            if self.parent is not None\
            and self.parent is not _libsc3.main.main_tt:
                return self.parent.thread_player
            else:
                return self

    @thread_player.setter
    def thread_player(self, player):
        self._thread_player = player

    @property
    def rand_seed(self):
        '''Random seed of the routine.

        By default, Routine's random generators are inherited
        from the parent routine and only change when seeded.
        '''
        return self._rand_seed

    @rand_seed.setter
    def rand_seed(self, x):
        # Routine's rgen are inherited from parent and
        # only changed when seeded. Use sc3.builtins.
        self._rand_seed = x
        self._rgen = random.Random(x)

    @property
    def rand_state(self):
        return self._rgen.getstate()

    @rand_state.setter
    def rand_state(self, data):
        self._rgen.setstate(data)

    # TODO: Maybe for pickling.
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
    def seconds(self):  # override
        # _MainThread set the current physical time when this
        # property is invoked and then spreads to child routines.
        _libsc3.main.update_logical_time()
        return self._m_seconds

    @property
    def is_playing(self):
        return True

    @property
    def _rgen(self):  # override
        return _libsc3.main._m_rgen

    @property
    def rand_seed(self):  # override
        pass

    @rand_seed.setter
    def rand_seed(self, x):  # override
        pass


### Stream.sc part 1 ###


class RoutineException(Exception):
    pass


class StopStream(StopIteration):
    pass


class PausedStream(StopStream):  # Not to be confused with PauseStream which doesn't exists here.
    pass


class YieldAndReset(Exception):
    def __init__(self, yield_value=None):
        super().__init__()  # Doesn't store yield_value in self.args.
        self.yield_value = yield_value


class AlwaysYield(Exception):
    def __init__(self, terminal_value=None):
        super().__init__()  # Doesn't store terminal_value in self.args.
        self.terminal_value = terminal_value


class Stream(aob.AbstractObject, ABC):
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
        '''Returns a Stream object.'''
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

    # play

    @abstractmethod
    def next(self, inval=None):
        pass

    def reset(self):
        pass

    # def stream_arg(self): # BUG: Used for Pcollect, Pselect, Preject, method defined by Object and Pattern.
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
    # subSample # Is somewhat specific, evaluates from offset an skipSize amount.
    # generate # Internal method for list comprehension documented in Object.

    # These method could be left for generator list comprehensions.
    # collect
    # reject
    # select

    # dot # // combine item by item with another stream # NOTE: usa FuncStream
    # interlace # // interlace with another stream # NOTE: usa FuncStream
    # ++ (appendStream)
    # append_stream # NOTE: Uses Routine with embedInStream.
    # collate # // ascending order merge of two streams # NOTE: usa interlace
    # <> # Pchain


    ### AbstractObject interface ###

    def _compose_unop(self, selector):
        return UnaryOpStream(selector, self)

    def _compose_binop(self, selector, other):
        return BinaryOpStream(selector, self, stream(other))

    def _rcompose_binop(self, selector, other):
        return BinaryOpStream(selector, stream(other), self)

    def _compose_narop(self, selector, *args):
        args = [stream(x) for x in args]
        return NAryOpStream(selector, self, *args)


    # asEventStreamPlayer
    # trace
    # repeat


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
        self.args = args  # All args are streams (cast done by _compose_narop).

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
    class _SENTINEL(): pass

    def __init__(self, func):
        super().__init__(func)
        self._iterator = None
        self._last_value = None
        self._terminal_value = self._SENTINEL

    @classmethod
    def run(cls, func, clock=None, quant=None):
        obj = cls(func)
        obj.play(clock, quant)
        return obj

    def play(self, clock=None, quant=None):
        with self._state_cond:
            if self.state == self.State.Init\
            or self.state == self.state.Paused:
                self.state = self.State.Suspended
                clock = clock or clk.SystemClock
                clock.play(self, quant)
        # Pattern.play return the stream, maybe for API usage constency
        # Stream.play should return self, but I'm not sure.
        # return self

    def next(self, inval=None):
        with self._state_cond:
            if self.state == self.State.Paused:
                raise PausedStream

            # Done & AlwaysYield.
            if self.state == self.State.Done:
                if self._terminal_value is self._SENTINEL:
                    raise StopStream
                else:
                    return self._terminal_value

            self.parent = _libsc3.main.current_tt
            _libsc3.main.current_tt = self
            if self._clock:
                self._m_seconds = self.parent._m_seconds
            else:
                self._m_seconds = self.parent.seconds

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
                        # Comon functions for routines generate nil streams
                        # in sclang, return value doesn't count. Check over.
                        if self._func_has_inval:
                            # raise AlwaysYield(self.func(inval))
                            self.func(inval)
                        else:
                            # raise AlwaysYield(self.func())
                            self.func()
                        raise AlwaysYield(None)
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
                raise StopStream from None
            except YieldAndReset as e:
                self._iterator = None
                self.state = self.State.Init
                self._last_value = e.yield_value
            except AlwaysYield as e:
                self._iterator = None
                self._terminal_value = e.terminal_value
                self.state = self.State.Done
                self._last_value = self._terminal_value
            except:
                self.state = self.State.Done  # Failure.
                raise
            finally:
                _libsc3.main.current_tt = self.parent
                self.parent = None

            return self._last_value

    def reset(self):
        with self._state_cond:
            if self.state == self.State.Running:
                raise RoutineException(
                    'cannot be reset within itself except by YieldAndReset')
            else:
                self._iterator = None
                self._clock = None
                self.state = self.State.Init

    def pause(self):
        with self._state_cond:
            if self.state == self.State.Running:
                raise RoutineException('cannot be paused within itself')
            if self.state == self.State.Init\
            or self.state == self.State.Suspended:
                self.state = self.State.Paused

    def resume(self, clock=None, quant=None):
        with self._state_cond:
            if self.state == self.State.Paused:
                self.state = self.State.Suspended
                clock = clock or self._clock or clk.SystemClock
                clock.play(self, quant)

    def stop(self):
        with self._state_cond:
            if self.state == self.State.Running:
                raise RoutineException('cannot be stopped within itself')
            else:
                self._iterator = None
                self._last_value = None
                self._clock = None
                self.state = self.State.Done

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
        # This method and hang could be common functions so instead of doing
        # `yielf from condition.wait()` it could be `yield cond.wait()`. That
        # will affect server.sync() for instance. I don't know which is best.
        # However, FlowVar needs to use `yield from` expression.
        if not self.test:
            self._waiting_threads.append(_libsc3.main.current_tt.thread_player)
            yield 'hang'  # Arbitrary non numeric value.
        else:
            yield 0

    def hang(self, value='hang'):
        # // Ignore the test, just wait.
        self._waiting_threads.append(_libsc3.main.current_tt.thread_player)
        yield value

    def signal(self):
        if self.test:
            tmp_wtt = self._waiting_threads
            self._waiting_threads = []
            for tt in tmp_wtt:
                tt._clock.sched(0, tt)

    def unhang(self):
        # // Ignore the test, just resume all waiting threads.
        tmp_wtt = self._waiting_threads
        self._waiting_threads = []
        for tt in tmp_wtt:
            tt._clock.sched(0, tt)


class FlowVar():
    class _UNBOUND(): pass

    def __init__(self):
        self._value = self._UNBOUND
        self.condition = Condition(lambda: self._value is not self._UNBOUND)

    @property
    def value(self):
        yield from self.condition.wait()
        return self._value

    @value.setter
    def value(self, inval):
        if self._value is not self._UNBOUND:
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

    def __embed__(self, indict=None):
        # Dictionary.embedInStream
        # func = self.value.get('embed', None)
        # if func is not None:
        #     yield from func(self.value, indict)
        if indict is None:
            return (yield self.value)
        else:
            indict = indict.copy()
            indict.update(self.value)
            return (yield indict)

    def next(self, indict=None):
        # Event.next
        if indict is None:
            # Object.composeEvent
            return self.value.copy()
        else:
            # Environment.composeEvent
            indict = indict.copy()
            indict.update(self.value)
            return indict


### Module functions ###


def stream(obj):
    '''Converts any object into a Stream.'''

    if hasattr(obj, '__stream__'):
        return obj.__stream__()
    else:
        if isinstance(obj, dict):
            return DictionaryStream(obj)
        else:
            return ValueStream(obj)


def embed(obj, inval=None):
    '''
    Converts any object into a Stream and returns its embeddable form passing
    inval to the `next` calls.
    '''

    if hasattr(obj, '__embed__'):
        return obj.__embed__(inval)
    else:
        if isinstance(obj, dict):
            return DictionaryStream(obj).__embed__(inval)
        else:
            return ValueStream(obj).__embed__(inval)
