"""Thread.sc & Stream.sc part 1"""

from abc import ABC, abstractmethod
import inspect
import enum
import random

from . import main as _libsc3
from . import absobject as aob
from . import clock as clk


__all__ = [
    'Routine', 'routine', 'FunctionStream',
    'Condition', 'FlowVar', 'stream', 'embed']


### Thread.sc ###


class TimeThread():
    State = enum.Enum('State', [
        'Init', 'Running', 'Suspended', 'Paused', 'Done'])

    def __init__(self, func):
        if not inspect.isfunction(func):
            raise TypeError('TimeThread argument is not a function')

        self.func = func
        self._func_has_inval = (  # Maybe it would be better to require the argument. Sync code with Prout and Pfuncn.
            len(inspect.signature(self.func).parameters) > 0)
        self._func_isgenfunc = inspect.isgeneratorfunction(self.func)

        self.parent = None
        self.state = self.State.Init
        self._state_lock = _libsc3.main._main_lock
        self._m_seconds = 0.0
        self._clock = clk.SystemClock  # Default clock.
        self._thread_player = None
        self._rand_seed = None
        self._rgen = _libsc3.main.current_tt._rgen

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    @property
    def _seconds(self):
        return self._m_seconds

    @property
    def _beats(self):
        return self._clock.secs2beats(self._seconds)

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

        By default, routine's random generators are inherited
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
        '''Return the state of the `random.Random` internal generator.'''
        return self._rgen.getstate()

    @rand_state.setter
    def rand_state(self, data):
        self._rgen.setstate(data)


class _MainTimeThread(TimeThread):
    def __init__(self):  # override
        self.parent = None
        self.func = None
        self.state = self.State.Init
        self._m_seconds = 0.0
        self._clock = clk.SystemClock  # Default clock.
        self._thread_player = None

    @property
    def _seconds(self):  # override
        # In RT _MainThread sets logical time to physical time when
        # this property is invoked and then spreads to child routines.
        if _libsc3.main is _libsc3.RtMain:
            _libsc3.main._update_logical_time(_libsc3.main.elapsed_time())
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
    '''Lazy sequence of values.

    Streams are iterator-generators compatible objects that implement
    a specific interface to interact with clocks and patterns.

    '''

    ### Iterator protocol ###

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()


    ### Stream protocol ###

    def __stream__(self):
        '''Return a Stream object.'''
        return self

    def __embed__(self, inval=None):
        '''Return generator-iterator that recursively embeds sub-streams.

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
        '''Same as list(stream) but with inval argument.

        '''

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
        return UnopStream(selector, self)

    def _compose_binop(self, selector, other):
        return BinopStream(selector, self, stream(other))

    def _rcompose_binop(self, selector, other):
        return BinopStream(selector, stream(other), self)

    def _compose_narop(self, selector, *args):
        args = [stream(x) for x in args]
        return NaropStream(selector, self, *args)


    # asEventStreamPlayer
    # trace
    # repeat


### BasicOpStream.sc ###


class UnopStream(Stream):
    def __init__(self, selector, a):
        self.selector = selector
        self.a = a

    def next(self, inval=None):
        a = self.a.next(inval)  # raises StopStream
        return self.selector(a)

    def reset(self):
        self.a.reset()

    def __repr__(self):
        return f'{type(self).__name__}({self.selector.__name__}, {self.a})'


class BinopStream(Stream):
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

    def __repr__(self):
        return (
            f'{type(self).__name__}({self.selector.__name__}, '
            f'{self.a}, {self.b})')


# NOTE: See BinaryOpXStream implementation options. Is not possible to
# implemente without a special function operation.


class NaropStream(Stream):
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

    def __repr__(self):
        return (
            f'{type(self).__name__}({self.selector.__name__}, '
            f'{self.a}, {self.args})')


class FunctionStream(Stream):  # Was FuncStream
    '''Create a stream from function evaluations.

    '''

    # Functions could use StopStream as sclang nil but is not nice.
    def __init__(self, next_func, reset_func=None, data=None):
        self.next_func = next_func
        self._next_nargs = len(inspect.signature(self.next_func).parameters)
        self.reset_func = reset_func or (lambda data: None)
        self._reset_nargs = len(inspect.signature(self.reset_func).parameters)
        self.data = data

    def next(self, inval=None):
        '''Return the next value from the stream.

        Its behaviour is the same as in `Routine.next`.

        '''

        # return fn.value(self.next_func, inval, self.data)  # Not cheap.
        # return self.next_func(inval, self.data)  # Mandatory
        if self._next_nargs > 1:
            return self.next_func(inval, self.data)
        elif self._next_nargs > 0:
            return self.next_func(inval)
        else:
            return self.next_func()

    def reset(self):
        '''Reset the stream by executing the `reset_func` if provided.

        If no `reset_func` was provided this method does nothing.

        '''
        # fn.value(self.reset_func, self.data)  # Not cheap.
        # self.reset_func(self.data)  # Mandatory.
        if self._reset_nargs > 0:
            self.reset_func(self.data)
        else:
            self.reset_func()

    # storeArgs


class Routine(TimeThread, Stream):
    '''
    Routines are iterator-generator compatible objects that implement
    the interfaces needed to interact with clocks and patterns and can
    keep track of individual random states. They could be understood as
    timelines for sequencing code excecution.

    Routines can be played, paused, resumed, stoped and reset. When played,
    they should yield time values, as `int` or `float`, that represent a
    precise timing offset between code excecution that is internally
    converted to OSC timetags for server commands. If running in a clock,
    the return value of the `yield` statement, as well as the initial value
    passed to the routine's function, is a tuple `(self, clock)` that can be
    accessed to change states without keeping an external reference by closure.

    Routines can be nested and played within others, the start time of the
    nested routines will be at the same `logical time` of the parent thus
    keeping synchronization and time relations even if played in a different
    clock than the parent's. By default, nested routines inherit the clock
    and random number generator of the parent.

    .. note::

      To use different random states and seeds the functions provided by
      the `builtins` module must be used.
    '''

    class _SENTINEL(): pass

    def __init__(self, func):
        super().__init__(func)
        self._iterator = None
        self._last_value = None
        self._terminal_value = self._SENTINEL

    @classmethod
    def run(cls, func, clock=None, quant=None):
        '''Create and play a routine from a common function.

        This method is a convenience constructor.

        '''

        obj = cls(func)
        obj.play(clock, quant)
        return obj

    def play(self, clock=None, quant=None):
        '''Schedule the Routine in a clock to play it.

        Parameters
        ----------
        clock : Clock
            An optional clock to schedule the routine. By default, routines
            inherit the clock from the current time thread when played. The
            default clock of the main time thread is SystemClock.
        quant : Quant
            A Quant object or a any value that can be cast into one with
            Quant.as_quant constructor. This parameter only works for
            TempoClock and is ignored by other clocks.

        '''

        with self._state_lock:
            if self.state == self.State.Init\
            or self.state == self.state.Paused:
                self.state = self.State.Suspended
                clock = clock or _libsc3.main.current_tt._clock
                clock.play(self, quant)
        # Pattern.play return the stream, maybe for API usage constency
        # Stream.play should return self, but I'm not sure.
        # return self

    def next(self, inval=None):
        '''Return the next value from the routine.

        This method accepts an optional input value and act the same way
        as the generator's `send` method. Routines behave like iterators
        and generators at the same time, once instantiated, this method
        evaluates its internal function and `inval` can be passed as the
        initial argument to that function. If the function is a generator
        function, an iterator will be created internally the first time
        this method is called and return the value of the first yield
        statement.

        '''

        with self._state_lock:
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
                self._clock = clk.SystemClock  # Default clock.
                self.state = self.State.Done
                raise
            except StopIteration:
                self._iterator = None
                self._last_value = None
                self._clock = clk.SystemClock  # Default clock.
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
        '''Reset the routine to its initial state.'''
        with self._state_lock:
            if self.state == self.State.Running:
                raise RoutineException(
                    'cannot be reset within itself except by YieldAndReset')
            else:
                self._iterator = None
                self._clock = clk.SystemClock  # Default clock.
                self.state = self.State.Init

    def pause(self):
        '''Pause the routine and remove it from the clock if it is playing.

        Raises
        ------
        RoutineException
            If this method is called from within the routine's function itself.

        '''

        with self._state_lock:
            if self.state == self.State.Running:
                raise RoutineException('cannot be paused within itself')
            if self.state == self.State.Init\
            or self.state == self.State.Suspended:
                self.state = self.State.Paused

    def resume(self, clock=None, quant=None):
        '''Resume the routine, this method does nothing if wasn't paused before.

        Parameters
        ----------
        clock : Clock
            An optionally different clock to re-schedule the routine.
            By default, the clock previously passed to the `play` function
            will be used.
        quant : Quant
            A Quant object or a any value that can be cast into one with
            Quant.as_quant constructor. This parameter only works for
            TempoClock and is ignored by other clocks.

        '''

        with self._state_lock:
            if self.state == self.State.Paused:
                self.state = self.State.Suspended
                clock = clock or self._clock
                clock.play(self, quant)

    def stop(self):
        '''Stop the routine and remove it from the clock if it is playing.

        Raises
        ------
        RoutineException
            If this method is called from within the routine's function itself.

        '''

        with self._state_lock:
            if self.state == self.State.Running:
                raise RoutineException('cannot be stopped within itself')
            else:
                self._iterator = None
                self._last_value = None
                self._clock = clk.SystemClock  # Default clock.
                self.state = self.State.Done

    # storeArgs
    # storeOn

    def __awake__(self, clock):
        return self.next((self, clock))

    def __repr__(self):
        return f'{type(self).__name__}({self.func.__qualname__})'


# decorator syntax
class routine():
    '''Decorator to convert generataor functions into Routines.

    This decorator class is redundant with the `Routine` class, it returns an
    instance of that class, but its use is recommended when used as decorator.

    '''

    def __new__(cls, func):
        return Routine(func)

    @staticmethod
    def run(clock=None, quant=None):
        '''Convenience decorator method equivalent to `Routine.run(func, clock, quant)`.'''
        def make_routine(func):
            obj = Routine(func)
            obj.play(clock, quant)
            return obj
        return make_routine


### Condition.sc ###


class Condition():
    '''
    Stop the execution of a routine playing on a clock until a condition
    is meet.

    Clocks' threads can't be blocked with common locks. This class acts like
    a blocking condition by removing the routine from the clock's scheduler
    and putting it in a waiting queue. See `wait` and `hang` methods for
    examples usage.

    Parameters
    ----------
    test: bool | callable
        Initial test condition it can be a callable that return a boolean.

    '''

    def __init__(self, test=False):
        self._test = test
        self._state_lock = _libsc3.main._main_lock
        self._waiting_threads = []

    @property
    def test(self):
        '''Get the truth value of the test.'''
        if callable(self._test):
            return self._test()
        else:
            return self._test

    @test.setter
    def test(self, value):
        '''Set test value. It can be a boolean or a callable that returns one.'''
        self._test = value

    def wait(self):
        '''
        Return a generator that will remove the routine from the clock
        by returning a string and add it to a waiting queue when the
        condition is set to True and signaled. If the test condition is
        already True it rechedules the routine immediately.

        ::

            cond = Condition()
            @routine
            def r():
                yield from cond.wait()  # Queued.
                print('resumed')
            r.play()

            cond.test = True  # Condition must be True to resume.
            cond.signal()  # Signal the routine.

        Raises
        ------
        Exeption
            If the generator is yield outside a routine.

        '''

        current_tt = _libsc3.main.current_tt
        if _libsc3.main.current_tt is _libsc3.main.main_tt:
            raise Exception(
                f'{type(self).__name__}.wait() called outside a routine')
        if not self.test:
            self._waiting_threads.append(current_tt.thread_player)
            yield 'hang'  # Arbitrary non numeric value.
        else:
            yield 0

    # This method may fail in different ways because it doesn't check
    # the test condition and routines can be added or not-removed from
    # _waiting_threads queue at the right time when scheduling is nested.
    # def hang(self, value='hang'):
    #     '''
    #     Return a generator that adds the routine to a waiting queue and
    #     yield the value of `value`. The routine will be recheduled when
    #     `unhang` is called.
    #
    #     ::
    #
    #         cond = Condition()
    #         @routine
    #         def r():
    #             yield from cond.hang()  # Queued.
    #             print('resumed')
    #         r.play()
    #
    #         cond.unhang()  # Resume the routine.
    #
    #     Raises
    #     ------
    #     Exeption
    #         If the generator is yield outside a routine.
    #
    #     '''
    #
    #     current_tt = _libsc3.main.current_tt
    #     if current_tt is _libsc3.main.main_tt:
    #         raise Exception(
    #             f'{type(self).__name__}.hang() called outside a routine')
    #     # // Ignore the test, just wait.
    #     self._waiting_threads.append(current_tt.thread_player)
    #     yield value

    def signal(self):
        '''Check the test and reschedule the routine if True.'''
        with self._state_lock:
            if self.test:
                tmp_wtt = self._waiting_threads
                self._waiting_threads = []
                for tt in tmp_wtt:
                    tt._clock.sched(0, tt)

    def unhang(self):
        '''Unhang a previously hung routine.'''
        with self._state_lock:
            # // Ignore the test, just resume all waiting threads.
            tmp_wtt = self._waiting_threads
            self._waiting_threads = []
            for tt in tmp_wtt:
                tt._clock.sched(0, tt)


class FlowVar():
    '''
    Defer the execution of a routine playing in a clock until a value is set.

    This class is similar of awaitables for routines. Internaly it uses the
    `Condition` class defined in this library. See `value` property for
    example usage.

    '''

    class _UNBOUND(): pass

    def __init__(self):
        self._value = self._UNBOUND
        self.condition = Condition(lambda: self._value is not self._UNBOUND)

    @property
    def value(self):
        '''
        Return a generator that adds the routine to a waiting queue and
        yield a string from the internal `Condition`. The routine will be
        recheduled to return its value when when it is set.

        ::

            f_var = FlowVar()
            @routine
            def r():
                v = yield from f_var.value  # Queued.
                print('say', v)
            r.play()

            f_var.value = 'hello'  # Resume the routine.

        Raises
        ------
        Exeption
            If the generator is yield outside a routine.

        '''

        yield from self.condition.wait()
        return self._value

    @value.setter
    def value(self, inval):
        '''Set the generator return value.

        Raises
        ------
        Exeption
            If the value set more than once (rebind).

        '''

        if self._value is not self._UNBOUND:
            raise Exception('cannot rebind a FlowVar')
        self._value = inval
        self.condition.signal()


### Type Streams ###


class ValueStream(Stream):
    '''Create a stream from any object.

    '''

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

    def __repr__(self):
        return f'{type(self).__name__}({self.value})'


class DictionaryStream(ValueStream):
    '''Create a stream from dict objects.

    Dictionaries have a special meaning because they are the base clase for
    events and can be used as specifications deferring the event object
    creation.

    '''

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
    '''Convert any object into a Stream.

    '''

    if hasattr(obj, '__stream__'):
        return obj.__stream__()
    else:
        if isinstance(obj, dict):
            return DictionaryStream(obj)
        else:
            return ValueStream(obj)


def embed(obj, inval=None):
    '''
    Convert any object into a Stream and return its embeddable form passing
    inval to the `next` calls.

    '''

    if hasattr(obj, '__embed__'):
        return obj.__embed__(inval)
    else:
        if isinstance(obj, dict):
            return DictionaryStream(obj).__embed__(inval)
        else:
            return ValueStream(obj).__embed__(inval)
