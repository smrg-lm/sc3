"""Patterns.sc"""

import logging
import inspect
import copy

from ..base import functions as fn
from . import stream as stm


_logger = logging.getLogger(__name__)


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


    def play(self, clock=None, proto_event=None, quant=None):
        return self.as_event_stream_player(proto_event).play(clock, False, quant)

    def as_event_stream_player(self, proto_event=None):
        return stm.EventStreamPlayer(self.__stream__(), proto_event)

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


### patterns ###


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


class Pchain(Pattern):
    def __init__(self, *patterns):
        self.patterns = list(patterns)

    def chain(self, pattern):  # <>  # *** NOTE: Maybe a function like stm.stream.
        return type(self)(*self.patterns, pattern)

    def __embed__(self, inval=None):
        cleanup = stm.EventStreamCleanup()
        streams = [stm.stream(p) for p in reversed(self.patterns)]
        while True:
            inevent = copy.copy(inval)
            for stream in streams:
                try:
                    inevent = stream.next(inevent)
                except stm.StopStream:
                    return cleanup.exit(inval)
            cleanup.update(inevent)
            inval = yield inevent

    # storeOn


class Pevent(Pattern):
    def __init__(self, pattern, event=None):
        self.pattern = pattern
        self.event = event or dict()  # *** BUG: Event.default

    def __embed__(self, inval):
        stream = stm.stream(self.pattern)
        while True:
            try:
                inval = yield stream.next(self.event)
            except stm.StopStream:
                return inval

    # storeArgs


class Pbind(Pattern):
    def __init__(self, *args):
        if len(args) % 2 != 0:
            raise ValueError('Pbind should have even number of args')
        self.pattern_pairs = args

    def __stream__(self):
        return stm.PatternEventStream(self)

    def __embed__(self, inevent=None):
        event = None
        stream_pairs = list(self.pattern_pairs)
        stop = len(stream_pairs)

        for i in range(1, stop, 2):
            stream_pairs[i] = stm.stream(stream_pairs[i])

        while True:
            if inevent is None:
                return  # Equivalent to ^nil.yield.
            event = inevent.copy()
            for i in range(0, stop, 2):
                name = stream_pairs[i]
                stream = stream_pairs[i + 1]
                try:
                    stream_out = stream.next(event)
                except stm.StopStream:
                    return inevent
                if isinstance(name, (list, tuple)):
                    if not isinstance(stream_out, (list, tuple))\
                    or isinstance(stream_out, (list, tuple))\
                    and len(name) > len(stream_out):
                        _logger.warning(
                            'the pattern is not providing enough '
                            f'values to assign to the key set: {name}')
                        return inevent
                    for i, key in enumerate(name):
                        event[key] = stream_out[i]
                else:
                    event[name] = stream_out
            inevent = yield event

    # storeArgs # TODO


class Pmono(Pattern):
    ...


class PmonoArtic(Pmono):
    ...


### math patterns ###


class Pseries(Pattern):
    ...


class Pgeom(Pattern):
    ...


class Pbrown(Pattern):
    ...


class Pgbrown(Pbrown):
    ...


class Pwhite(Pattern):
    ...


class Pprob(Pattern):
    ...


# NOTE: estos patterns y otros que no están en este archivo se usan para
# crear los operadores/builtins como patterns.
class Pstep2add(Pattern): # NOTE: no está documentada, las siguientes si.
    ...


class Pstep3add(Pattern):
    ...


class PstepNfunc(Pattern):
    ...


class PstepNadd(PstepNfunc):
    ...


### imperative patterns ###


# // returns relative time (in beats) from moment of embedding
class Ptime(Pattern):
    ...


# // if an error is thrown in the stream, func is evaluated
# class Pprotect(FilterPattern): # BUG: FilterPatterns.sc
#     ...


# // access a key from the input event
class Pkey(Pattern):
    ...


class Pif(Pattern):
    ...
