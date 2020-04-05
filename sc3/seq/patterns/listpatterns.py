"""ListPatterns.sc"""

import collections

from .. import stream as stm
from .. import pattern as ptt


# class Pindex(ptt.Pattern):
#     ... # TODO: ver qué patrones definen funcionalidad excepcional


class ListPattern(ptt.Pattern):
    def __init__(self, lst=None, repeats=1):
        lst = list(lst)  # raises TypeError
        if len(lst) > 0:
            self.lst = lst
            self.repeats = repeats
        else:
            raise ValueError(
                f"ListPattern '{type(self).__name__}' "
                "requires a non empty collection")

    # copy # BUG: copia la lista lst
    # storeArgs # TODO


class Pseq(ListPattern):
    def __init__(self, lst, repeats=1, offset=0):
        super().__init__(lst, repeats)
        self.offset = offset

    def __embed__(self, inval=None):
        # NOTE: Are sclang assignments in case the object is mutable?
        # NOTE: review use of value in sclang.
        # if (inval.eventAt('reverse') == true, { # Not good.
        for i in range(self.repeats):
            for item in self.lst[self.offset:]:
                inval = yield from stm.embed(item, inval)
            for item in self.lst[:self.offset]:
                inval = yield from stm.embed(item, inval)
        return inval

    # storeArgs # TODO


# Es una variante de Pseq que cuenta por item en lugar de por lista
class Pser(Pseq):
    ...


class Pshuf(ListPattern):
    ...


class Prand(ListPattern):
    ...

class Pxrand(ListPattern):
    ...


class Pwrand(ListPattern):
    ...


# # TODO: estos dos son un tanto específicos.
# # // Finite State Machine
# class Pfsm(ListPattern):
#     ...
# # // Deterministic Finite State Machine
# class Pdfsm(ListPattern):
#     ...


# TODO: selecciona elementos por índice en la lista.
class Pswitch(ptt.Pattern):
    ...


# TODO: idem pero no embebe el item si es un stream sino que alterna por elemento
class Pswitch1(Pswitch):
    ...


# TODO: es un tipo de paralelización de streams.
class Ptuple(ListPattern):
    ...


# TODO: entrelaza elementos de sub listas, es secuencial.
class Place(Pseq):
    ...


# TODO: este es un caso de funcionalidad repetida por tipo de dato
# de entrada, este tipo de cosas estaría bueno unificar, como hace
# en general en el resto de la librería. Pero es un detalle por ahora.
# // similar to Place, but the list is an array of Patterns or Streams
class Ppatlace(Pseq):
    ...


# TODO: este es una operación específica, una manera de recorrer
# la lista. Ver si no se puede hacer programáticamente de otra manera,
# aunque es el mismo principio que con rand, xrand, walk, etc.
class Pslide(ListPattern):
    # // 'repeats' is the number of segments.
    # // 'len' is the length of each segment.
    # // 'step' is how far to step the start of each segment from previous.
    # // 'start' is what index to start at.
    # // indexing wraps around if goes past beginning or end.
    # // step can be negative.
    ...


class Pwalk(ListPattern):
    ...


### Ppar.sc ###


# TODO: es un ListPattern, pero es exclusivamente para event streams,
# tampoco es que haya otra forma, Ptuple tal vez, se necesita delta.
# En este sentido actúa como un conjunto de elementos específico (listas).
class Ppar(ListPattern):
    ...


class Ptpar(Ppar):
    ...


class Pgpar(Ppar):
    ...


class Pgtpar(Pgpar):
    ...
