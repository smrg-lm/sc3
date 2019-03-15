"""Patterns.sc"""

import supercollie.functions as fn
import supercollie.thread as thr


# NOTE: No define ningún método como responsabilidad de subclase,
# por eso es que Pattern no es una ABC.
class Pattern(fn.AbstractFunction):
    def __call__(cls): # BUG: pattern también no es estrictamente una función, se podría declarar AbstractObject o SCObject
        pass

    # // concatenate Patterns
    # ++
    # // compose Patterns
    # <>

    def play(self, clock, proto, quant):
        pass # TODO

    def __iter__(self):
        return self.stream() # BUG: es stream (routine) o iter (gen obj)???

    def stream(self): # NOTE: es asStream
        # TODO: ES PROTOCOLO, un stream no es un iterador común (es una Routine)
        # aunque tiene que ser compatible.
        def _stream(inval=None): # BUG: pattern_iterator?? from _collections_abc import list_iterator
            inval = yield from self.iter(inval)
            print('*** sale de Stream Routne(_stream)')
        return thr.Routine(_stream)

    def iter(self, inval=None): # NOTE: es embedInStream para Stream sin la funcionalidad del yield from
        # NOTE: devuelve un generator object
        def _gi(inval):
            yield None
        return _gi(inval)

    # stream_args

    def event_stream_player(self, proto):
        return EventStreamPlayer(self.stream, proto)

    # embedInStream # NOTE: este método no se usaría en Python.
    # do
    # collect
    # select
    # reject

    def compose_unop(self, selector):
        return Punop(selector, self)

    def compose_binop(self, selector, other):
        return Pbinop(selector, self, other)

    def compose_narop(self, selector, *args):
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
    pass


class Pbinop(Pattern):
    pass


class Pnarop(Pattern): # BUG: nombre cambiado
    pass


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
    pass


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
