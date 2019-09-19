"""Patterns.sc"""

import logging

from ..base import functions as fn
from . import stream as stm


_logger = logging.getLogger(__name__)


class Pattern(fn.AbstractFunction):
    # // concatenate Patterns
    # ++
    # // compose Patterns
    # <>

    def __iter__(self):
        return self.__stream__()

    def __stream__(self): # es asStream
        def _(inval=None): # NOTE: Stream es el pattern iterator
            yield from self.__embed__(inval)
        _.__name__ = type(self).__name__ + '_stream_gf' # e.g. Pseq_stream_gf
        _.__qualname__ += _.__name__
        return stm.Routine(_)

    def __embed__(self, inval=None): # NOTE: es embedInStream para Stream sin la funcionalidad del yield from que se define en __stream__
        print('*** usa Pattern __embed__')
        yield from self.__stream__().__embed__(inval)

    def play(self, clock=None, proto_event=None, quant=None):
        return self.as_event_stream_player(proto_event).play(clock, False, quant)

    def as_event_stream_player(self, proto_event=None):
        return stm.EventStreamPlayer(self.__stream__(), proto_event)

    # stream_args
    # do
    # collect
    # select
    # reject

    def _compose_unop(self, selector):
        return Punop(selector, self)

    def _compose_binop(self, selector, other):
        return Pbinop(selector, self, other)

    def _rcompose_binop(self, selector, other):
        return Pbinop(selector, other, self)

    def _compose_narop(self, selector, *args):
        return Pnarop(selector, self, *args)

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

    def __stream__(self): # BUG: no entiendo cuándo se usan estos métodos si anulan __embed__
        print('*** convierte Punop en UnaryOpStream')
        return stm.UnaryOpStream(self.selector, stm.stream(self.a))

    def __embed__(self, inval=None):
        print('*** usa Punop __embed__')
        stream = stm.stream(self.a)
        outval = None
        while True:
            outval = stream.next(inval)
            inval = yield self.selector(outval)

    # storeOn


class Pbinop(Pattern):
    def __init__(self, selector, a, b):
        self.selector = selector
        self.a = a
        self.b = b

    def __stream__(self):
        print('*** convierte Pbinop en BinaryOpStream')
        return stm.BinaryOpStream(
            self.selector,
            stm.stream(self.a),
            stm.stream(self.b)
        )

    # BUG: ver por qué no define __embed__ acá o por qué los define en los otros dos.

    # storeOn


class Pnarop(Pattern): # BUG: nombre cambiado
    def __init__(self, selector, a, *args):
        self.selector = selector
        self.a = a
        self.args = args

    def __stream__(self):
        print('*** convierte Pnarop en NAryOpStream')
        args = [stm.stream(x) for x in self.args]
        return stm.NAryOpStream(self.selector, stm.stream(self.a), *args)

    def __embed__(self, inval=None):
        print('*** usa Pnarop __embed__')
        stream_a = stm.stream(self.a)
        stream_lst = [stm.stream(x) for x in self.args]
        while True:
            a = stream_a.next(inval)
            args = [x.next(inval) for x in stream_lst]
            inval = yield self.selector(a, *args)

    # storeOn


### patterns ###


class Pfunc(Pattern):
    pass


class Prout(Pattern):
    pass


class Pfuncn(Pattern):
    pass


# BUG: ver su utilidad, qué diferencia hay
# con usar un operador enario directamente?
# class PdegreeToKey(Pnarop):
#     pass


class Pchain(Pattern):
    pass


class Pevent(Pattern):
    pass


class Pbind(Pattern):
    def __init__(self, *args):
        if len(args) % 2 != 0:
            raise TypeError('Pbind should have even number of args')
        self.pattern_pairs = args

    def __embed__(self, in_event=None):
        event = None
        #saw_none = False # BUG: en sclang, no se usa.
        stream_pairs = list(self.pattern_pairs)
        stop = len(stream_pairs)

        for i in range(1, stop, 2):
            stream_pairs[i] = stm.stream(stream_pairs[i])

        while True:
            if in_event is None:
                return # NOTE: es next quién tira la excepción
            event = in_event.copy()
            for i in range(0, stop, 2):
                name = stream_pairs[i]
                stream = stream_pairs[i + 1]
                try:
                    stream_out = stream.next(event)
                except stm.StopStream:
                    return in_event # NOTE: ver.
                if isinstance(name, (list, tuple)):
                    if isinstance(stream_out, (list, tuple))\
                    and len(name) > len(stream_out)\
                    or not isinstance(stream_out, (list, tuple)):
                        _logger.warning(
                            'the pattern is not providing enough '
                            f'values to assign to the key set: {name}')
                        return in_event
                    for i, key in enumerate(name):
                        event[key] = stream_out[i]
                else:
                    event[name] = stream_out
            in_event = yield event


    # storeArgs # TODO


class Pmono(Pattern):
    pass


class PmonoArtic(Pmono):
    pass


### math patterns ###


class Pseries(Pattern):
    pass


class Pgeom(Pattern):
    pass


class Pbrown(Pattern):
    pass


class Pgbrown(Pbrown):
    pass


class Pwhite(Pattern):
    pass


class Pprob(Pattern):
    pass


# NOTE: estos patterns y otros que no están en este archivo se usan para
# crear los operadores/builtins como patterns.
class Pstep2add(Pattern): # NOTE: no está documentada, las siguientes si.
    pass


class Pstep3add(Pattern):
    pass


class PstepNfunc(Pattern):
    pass


class PstepNadd(PstepNfunc):
    pass


### imperative patterns ###


# // returns relative time (in beats) from moment of embedding
class Ptime(Pattern):
    pass


# // if an error is thrown in the stream, func is evaluated
# class Pprotect(FilterPattern): # BUG: FilterPatterns.sc
#     pass


# // access a key from the input event
class Pkey(Pattern):
    pass


class Pif(Pattern):
    pass
