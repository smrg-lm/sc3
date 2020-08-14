"""Patterns.sc"""

import inspect

from ..base import functions as fn
from ..base import stream as stm
from ..base import utils as utl
from . import pausestream as pst
from . import event as evt


__all__ = ['pattern']


class Pattern(fn.AbstractFunction):
    ### Iterable protocol ###

    def __iter__(self):
        return self.__stream__()


    ### Stream protocol ###

    def __stream__(self):
        return pst.PatternValueStream(self)

    def __embed__(self, inval=None):
        return (yield from self.__stream__().__embed__(inval))


    ### AbstractFunction interface ###

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
        stream = pst.EventStreamPlayer(self.__stream__(), proto)
        stream.play(clock, False, quant)
        return stream

    # def _as_event_stream_player(self, proto_event=None):
    #     return pst.EventStreamPlayer(self.__stream__(), proto_event)

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
    # trace
    #
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

    def __stream__(self):
        return stm.UnaryOpStream(self.selector, stm.stream(self.a))

    def __embed__(self, inval=None):
        stream = stm.stream(self.a)
        while True:
            try:
                inval = yield self.selector(stream.next(inval))
            except stm.StopStream:
                return inval

    # storeOn


class Pbinop(Pattern):
    def __init__(self, selector, a, b):
        self.selector = selector
        self.a = a
        self.b = b

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

    def __stream__(self):
        args = [stm.stream(x) for x in self.args]
        return stm.NAryOpStream(self.selector, stm.stream(self.a), *args)

    def __embed__(self, inval=None):
        stream_a = stm.stream(self.a)
        # NOTE: See omitted optimization.
        stream_lst = [stm.stream(x) for x in self.args]
        while True:
            try:
                a = stream_a.next(inval)
                args = [x.next(inval) for x in stream_lst]
                inval = yield self.selector(a, *args)
            except stm.StopStream:
                return inval

    # storeOn


def pattern(gfunc):
    '''
    Decorator to create value patterns from generator functions.

    @pattern
    def pwhite(lo=0.0, hi=1.0, length=bi.inf):
        lo = stream(lo)
        hi = stream(hi)
        loval = hival = None
        for _ in utl.counter(length):
            try:
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
