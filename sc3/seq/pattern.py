"""Patterns.sc"""

import inspect

from ..base import functions as fn
from . import event as evt
from . import stream as stm


class Pattern(fn.AbstractFunction):
    ### Iterable protocol ###

    def __iter__(self):
        return self.__stream__()


    ### Stream protocol ###

    def __stream__(self):
        return stm.PatternValueStream(self)

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
        stream = stm.EventStreamPlayer(self.__stream__(), proto)
        stream.play(clock, False, quant)
        return stream

    # def _as_event_stream_player(self, proto_event=None):
    #     return stm.EventStreamPlayer(self.__stream__(), proto_event)

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


### Function patterns ###


class Pfunc(Pattern):
    def __init__(self, next_func, reset_func=None, data=None):
        self.next_func = next_func
        self.reset_func = reset_func
        self.data = data

    def __stream__(self):
        return stm.FunctionStream(self.next_func, self.reset_func, self.data)

    # storeArgs


class Prout(Pattern):
    def __init__(self, func):
        self.func = func
        self._func_has_inval = (  # See note in TimeThread.__init__. Sync code.
            len(inspect.signature(self.func).parameters) > 0)
        self._func_isgenfunc = inspect.isgeneratorfunction(self.func)

    def __stream__(self):
        return stm.Routine(self.func)

    def __embed__(self, inval=None):
        if self._func_isgenfunc:
            if self._func_has_inval:
                iterator = self.func(inval)
            else:
                iterator = self.func()
            try:
                yield next(iterator)
                while True:
                    yield iterator.send(inval)
            except StopIteration as e:
                return e.value  # Contains generator function's return value.
        else:
            if self._func_has_inval:
                return self.func(inval)
            else:
                return self.func()

    # storeArgs


class Pfuncn(Pattern):
    def __init__(self, func, repeats=1):
        self.func = func
        self._func_has_inval = (  # See note in TimeThread.__init__. Sync code.
            len(inspect.signature(self.func).parameters) > 0)
        self.repeats = repeats

    def __embed__(self, inval=None):
        for i in range(self.repeats):
            if self._func_has_inval:
                inval = yield self.func(inval)
            else:
                inval = yield self.func()
        return inval

    # storeArgs


# BUG: ver su utilidad, qué diferencia hay
# con usar un operador enario directamente?
# class PdegreeToKey(Pnarop):
#     ...
