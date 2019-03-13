"""Patterns.sc"""

import supercollie.functions as fn


# NOTE: No define ningún método como responsabilidad de subclase,
# por eso es que Pattern no es una ABC.
class Pattern(fn.AbstractFunction):
    pass


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
class Pprotect(FilterPattern): # BUG: FilterPatterns.sc
    pass


# // access a key from the input event
class Pkey(Pattern):
    pass


class Pif(Pattern):
    pass
