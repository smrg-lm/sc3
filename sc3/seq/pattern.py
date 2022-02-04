"""
The transcription of the pattern library is organized following the
specifications below.

It is understood that there are edge cases for different use cases and that a
type-free stream creation would be a more general approach but also less clear.
In any case, this is open to reconsideration.

Event patterns
--------------
Patterns that create streams of events.

Value patterns
--------------
Patterns that create streams of values.

List patterns
-------------
Container patterns that can create either streams of events or values. Hybrid
streams can be created but they will probably fail in combination with other
type specific patterns.

Filter patterns
---------------
Patterns that receive and process other patterns. Some filter patterns are
designed to process event or value streams but not both.

Function patterns
-----------------
Patterns defined by the evaluation of a function, the resulting stream is
defined by the class but is considered to be a value stream when combined
with other patterns.

Special patterns
----------------
So far, in this transcription, the only special case is Pkey. Must be
defined for a key inside an event pattern, either Pbind or Pmono. It takes the
event stream and extracts the value of another key of the event being processed
in the order the keys were defined.

"""

import inspect

from ..base import _hooks as hks
from ..base import absobject as aob
from ..base import stream as stm
from . import event as evt


est = hks.late_import(__name__, 'sc3.seq.eventstream', 'est')
flp = hks.late_import(__name__, 'sc3.seq.patterns.filterpatterns', 'flp')


__all__ = ['pattern']


class Pattern(aob.AbstractObject):
    @property
    def is_event_pattern(self):
        # Value patterns may create either value or event
        # streams depending if they embed an EventPattern.
        return False


    ### Iterable protocol ###

    def __iter__(self):
        return self.__stream__()


    ### Stream protocol ###

    def __stream__(self):
        if self.is_event_pattern:
            return est.PatternEventStream(self)
        else:
            return est.PatternValueStream(self)

    def __embed__(self, inval=None):
        return (yield from self.__stream__().__embed__(inval))


    ### AbstractObject interface ###

    def _compose_unop(self, selector):
        return Punop(selector, self)

    def _compose_binop(self, selector, other):
        return Pbinop(selector, self, other)

    def _rcompose_binop(self, selector, other):
        return Pbinop(selector, other, self)

    def _compose_narop(self, selector, *args):
        return Pnarop(selector, self, *args)


    def play(self, clock=None, quant=None, proto=None):
        if not self.is_event_pattern:
            raise ValueError(f'{type(self)} is not an event pattern')
        proto = evt.event() if proto is None else evt.event(proto)
        stream = est.EventStreamPlayer(self.__stream__(), proto)
        stream.play(clock, quant)
        return stream

    # def _as_event_stream_player(self, proto_event=None):
    #     return est.EventStreamPlayer(self.__stream__(), proto_event)

    # stream_args
    # do
    # collect
    # select
    # reject
    #
    # ++ // concatenate Patterns
    # <> // compose Patterns
    #
    # mtranspose
    # ctranspose
    # gtranspose
    # detune
    #
    # scaleDur
    # addDur
    # stretch
    # lag
    #
    # legato
    # db
    #
    # clump
    # flatten
    # repeat
    # keep
    # drop
    # stutter
    # finDur
    # fin
    #

    def trace(self, prefix=None, keys=None):
        return flp.Ptrace(self, prefix, keys)

    # differentiate
    # integrate

    # // realtime recording
    # // for NRT see Pattern:asScore
    #
    # // path: if nil, auto-generate path
    # // dur: if nil, record until pattern stops or is stopped externally
    # // fadeTime: allow extra time after last Event for nodes to become silent
    # record


### op patterns ###


class Punop(Pattern):
    def __init__(self, selector, a):
        self.selector = selector
        self.a = a
        self._is_event_pattern = (
            isinstance(a, Pattern) and a.is_event_pattern)

    @property
    def is_event_pattern(self):
        return self._is_event_pattern

    def __stream__(self):
        return stm.UnopStream(self.selector, stm.stream(self.a))

    def __embed__(self, inval=None):
        stream = stm.stream(self.a)
        try:
            while True:
                inval = yield self.selector(stream.next(inval))
        except stm.StopStream:
            return inval

    def __repr__(self):
        return f'{type(self).__name__}({self.selector.__name__}, {self.a})'


class Pbinop(Pattern):
    def __init__(self, selector, a, b):
        self.selector = selector
        self.a = a
        self.b = b
        self._is_event_pattern = any(
            isinstance(x, Pattern) and x.is_event_pattern for x in (a, b))

    @property
    def is_event_pattern(self):
        return self._is_event_pattern

    def __stream__(self):
        return stm.BinopStream(
            self.selector, stm.stream(self.a), stm.stream(self.b))
        # NOTE: See BinaryOpXStream implementation options. Class is not
        # defined.

    def __repr__(self):
        return (
            f'{type(self).__name__}({self.selector.__name__}, '
            f'{self.a}, {self.b})')


class Pnarop(Pattern):  # Was Pnaryop.
    def __init__(self, selector, a, *args):
        self.selector = selector
        self.a = a
        self.args = args
        self._is_event_pattern = (
            isinstance(a, Pattern) and a.is_event_pattern)

    @property
    def is_event_pattern(self):
        return self._is_event_pattern

    def __stream__(self):
        args = [stm.stream(x) for x in self.args]
        return stm.NaropStream(self.selector, stm.stream(self.a), *args)

    def __embed__(self, inval=None):
        stream_a = stm.stream(self.a)
        # NOTE: See omitted optimization.
        stream_lst = [stm.stream(x) for x in self.args]
        try:
            while True:
                a = stream_a.next(inval)
                args = [x.next(inval) for x in stream_lst]
                inval = yield self.selector(a, *args)
        except stm.StopStream:
            return inval

    def __repr__(self):
        return (
            f'{type(self).__name__}({self.selector.__name__}, '
            f'{self.a}, {self.args})')


def pattern(gfunc):
    '''
    Decorator to create value patterns from generator functions. ::

        @pattern
        def pwhite(lo=0.0, hi=1.0, length=float('inf')):
            lo = stream(lo)
            hi = stream(hi)
            loval = hival = None
            try:
                for _ in bi.counter(length):
                    loval = next(lo)
                    hival = next(hi)
                    yield bi.rrand(loval, hival)
            except StopIteration:
                return

        p = stream(pwhite(length=3) ** 2)
        next(p)
    '''

    if not inspect.isgeneratorfunction(gfunc):
        raise Exception(f'{gfunc} is not a generator function')

    class _(Pattern):
        _gfunc = gfunc

        def __init__(self, *args, **kwargs):
            self._args = args
            self._kwargs = kwargs

        def __embed__(self, _=None):
            return type(self)._gfunc(*self._args, **self._kwargs)

    _.__name__ = gfunc.__name__
    _.__qualname__ = gfunc.__qualname__
    return _
