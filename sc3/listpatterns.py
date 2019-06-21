"""ListPatterns.sc"""

import collections

import sc3.stream as stm
import sc3.patterns as ptt


# class Pindex(ptt.Pattern):
#     pass # TODO: ver qué patrones definen funcionalidad excepcional


class ListPattern(ptt.Pattern):
    def __init__(self, lst=None, repeats=1):
        lst = lst or []
        if len(lst) > 0:
            self.lst = lst
            self.repeats = repeats
        else:
            msg = "ListPattern '{}' requires a non empty collection"
            raise ValueError(msg.format(type(self).__name__))

    # copy # BUG: copia la lista lst
    # storeArgs # TODO


class Pseq(ListPattern):
    def __init__(self, lst, repeats=1, offset=0):
        super().__init__(lst, repeats)
        self.offset = offset

    def __embed__(self, inval=None):
        offset = self.offset # BUG: *** en el original llama a value (no a next).
                             # BUG: *** puede ser que llame a value no porque sea un stream sino una función que
                             # BUG: *** modifican el comportamiento de repeats y offset según los datos el evento.
        # if (inval.eventAt('reverse') == true, { # BUG: TODO: No se si es bueno que el evento defina el comportamiento dle pattern.
        repeats = self.repeats
        lst = collections.deque(self.lst)
        lst.rotate(offset) # TODO: tal vez usa wrapAt porque rotar es más costoso y genera un pico.
        for i in range(repeats):
            for item in lst:
                inval = yield from stm.embed(item, inval)

    # storeArgs # TODO


# Es una variante de Pseq que cuenta por item en lugar de por lista
class Pser(Pseq):
    pass


class Pshuf(ListPattern):
    pass


class Prand(ListPattern):
    pass

class Pxrand(ListPattern):
    pass


class Pwrand(ListPattern):
    pass


# # TODO: estos dos son un tanto específicos.
# # // Finite State Machine
# class Pfsm(ListPattern):
#     pass
# # // Deterministic Finite State Machine
# class Pdfsm(ListPattern):
#     pass


# TODO: selecciona elementos por índice en la lista.
class Pswitch(ptt.Pattern):
    pass


# TODO: idem pero no embebe el item si es un stream sino que alterna por elemento
class Pswitch1(Pswitch):
    pass


# TODO: es un tipo de paralelización de streams.
class Ptuple(ListPattern):
    pass


# TODO: entrelaza elementos de sub listas, es secuencial.
class Place(Pseq):
    pass


# TODO: este es un caso de funcionalidad repetida por tipo de dato
# de entrada, este tipo de cosas estaría bueno unificar, como hace
# en general en el resto de la librería. Pero es un detalle por ahora.
# // similar to Place, but the list is an array of Patterns or Streams
class Ppatlace(Pseq):
    pass


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
    pass


class Pwalk(ListPattern):
    pass


### Ppar.sc ###


# TODO: es un ListPattern, pero es exclusivamente para event streams,
# tampoco es que haya otra forma, Ptuple tal vez, se necesita delta.
# En este sentido actúa como un conjunto de elementos específico (listas).
class Ppar(ListPattern):
    pass


class Ptpar(Ppar):
    pass


class Pgpar(Ppar):
    pass


class Pgtpar(Pgpar):
    pass
