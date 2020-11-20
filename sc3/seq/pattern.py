"""Patterns.sc"""

import inspect

from ..base import classlibrary as clb
from ..base import absobject as aob
from ..base import stream as stm
from . import event as evt


clb.ClassLibrary.late_imports(__name__,
    ('sc3.seq.eventstream', 'est'),
    ('sc3.seq.patterns.filterpatterns', 'flp'))


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


    def play(self, clock=None, proto=None, quant=None):
        proto = evt.event() if proto is None else evt.event(proto)
        stream = est.EventStreamPlayer(self.__stream__(), proto)
        stream.play(clock, False, quant)
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


class EventPattern(Pattern):
    @property
    def is_event_pattern(self):
        return True

    def __stream__(self):
        return est.PatternEventStream(self)


### op patterns ###


class Punop(Pattern):
    def __init__(self, selector, a):
        self.selector = selector
        self.a = a
        self._is_event_pattern = a.is_event_pattern

    @property
    def is_event_pattern(self):
        return self._is_event_pattern

    def __stream__(self):
        return stm.UnaryOpStream(self.selector, stm.stream(self.a))

    def __embed__(self, inval=None):
        stream = stm.stream(self.a)
        try:
            while True:
                inval = yield self.selector(stream.next(inval))
        except stm.StopStream:
            return inval

    # storeOn


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
        return stm.BinaryOpStream(
            self.selector, stm.stream(self.a), stm.stream(self.b))
        # NOTE: See BinaryOpXStream implementation options. Class is not
        # defined.

    # storeOn


class Pnarop(Pattern): # BUG: nombre cambiado
    def __init__(self, selector, a, *args):
        self.selector = selector
        self.a = a
        self.args = args
        self._is_event_pattern = a.is_event_pattern

    @property
    def is_event_pattern(self):
        return self._is_event_pattern

    def __stream__(self):
        args = [stm.stream(x) for x in self.args]
        return stm.NAryOpStream(self.selector, stm.stream(self.a), *args)

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

    # storeOn


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
