"""ListPatterns.sc"""

import collections

from ...base import utils as utl
from ...base import stream as stm
from ...base import builtins as bi
from .. import pattern as ptt


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

    def __embed__(self, inval):
        # NOTE: Are sclang assignments in case the object is mutable?
        # NOTE: review use of value in sclang.
        # if (inval.eventAt('reverse') == true, { # Not good.
        lst = self.lst
        offset = self.offset
        for _ in utl.counter(self.repeats):
            for item in lst[offset:]:
                inval = yield from stm.embed(item, inval)
            for item in lst[:offset]:
                inval = yield from stm.embed(item, inval)
        return inval

    # storeArgs # TODO


class Pser(Pseq):
    def __embed__(self, inval):
        lst = self.lst
        offset = self.offset
        size = len(lst)
        for i in utl.counter(self.repeats):
            inval = yield from stm.embed(lst[(i + offset) % size], inval)
        return inval


# class Pindex(ptt.Pattern):
#     # I don't see the difference with Pswitch, here or in sclang.
#     def __init__(self, lst, indx_pattern, repeats=1):
#         self.lst = lst
#         self.indx_pattern = indx_pattern
#         self.repeats = repeats
#
#     # storeArgs
#
#     def __embed__(self, inval):
#         lst_stream = stm.stream(self.lst)
#         indx_stream = None
#         indx_pattern = self.indx_pattern
#         lst = size = None
#         try:
#             for _ in utl.counter(self.repeats):
#                 lst = lst_stream.next(inval)  # raises StopStream
#                 size = len(lst)
#                 indx_stream = stm.stream(indx_pattern)
#                 for i in indx_stream:
#                     inval = yield from stm.embed(lst[i % size], inval)
#         except stm.StopStream:
#             return inval


class Pswitch(ptt.Pattern):
    def __init__(self, lst, which=0):
        self.lst = lst
        self.which = which

    def __embed__(self, inval):
        lst = self.lst
        size = len(lst)
        indx_stream = stm.stream(self.which)
        indx = None
        try:
            while True:
                indx = indx_stream.next(inval)  # raises StopStream
                inval = yield from stm.embed(lst[indx % size], inval)
        except stm.StopStream:
            return inval

    # storeArgs


class Pswitch1(Pswitch):
    def __embed__(self, inval):
        # EventStreamCleanup removed.
        stream_lst = [stm.stream(i) for i in self.lst]
        size = len(stream_lst)
        indx_stream = stm.stream(self.which)
        indx = None
        try:
            while True:
                indx = indx_stream.next(inval)
                inval = yield stream_lst[indx % size].next(inval)
        except stm.StopStream:
            return inval


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


### Random ###

class Pshuffle(ListPattern):  # Pshuf
    def __embed__(self, inval):
        slist = self.lst[:]
        bi.shuffle(slist)
        for _ in utl.counter(self.repeats):
            for item in slist:
                inval = yield from stm.embed(item)
        return inval


class Prand(ListPattern):
    # repeats should be length.
    def __embed__(self, inval):
        lst = self.lst
        size = len(lst)
        for _ in utl.counter(self.repeats):
            inval = yield from stm.embed(lst[bi.rand(size)], inval)
        return inval


class Pxrand(ListPattern):
    # repeats should be length.
    def __embed__(self, inval):
        size = len(self.lst)
        index = bi.rand(size)
        for _ in utl.counter(self.repeats):
            index = (index + bi.rand(size - 1) + 1) % size
            inval = yield from stm.embed(lst[index], inval)
        return inval


class Pwrand(ListPattern):
    # repeats should be length.
    def __init__(self, lst, weights=None, repeats=1):  #, *, cum_weights=None, k=1):
        super().__init__(lst, repeats)
        self.weights = weights
        # self.cum_weights = cum_weights
        # self.k = k

    def __embed__(self, inval):
        lst = self.lst
        weights = self.weights
        ilst = range(len(weights)) if weights else range(len(lst))
        indx = None
        wstream = stm.stream(weights)
        try:
            for _ in utl.counter(self.repeats):
                indx = bi.choices(ilst, wstream.next(inval))[0]  #, cum_weights=cw, k=k)
                inval = yield from stm.embed(lst[indx], inval)
        except stm.StopStream:
            return inval


class Pwalk(ListPattern):
    # // random walk pattern - hjh - jamshark70@gmail.com
    def __init__(self, lst, steps=None, directions=1, start=0):
        super().__init__(lst)
        self.steps = steps or Prand([-1, 1], bi.inf)
        self.directions = 1 if directions is None else directions
        self.start = start

    # storeArgs

    def __embed__(self, inval):
        lst = self.lst
        step = None
        size = len(lst)
        index = self.start
        step_stream = stm.stream(self.steps)
        direction_stream = stm.stream(self.directions)
        direction = direction_stream.next(inval)

        try:
            while True:
                step = step_stream.next(inval)  # raises StopStream
                inval = yield from stm.embed(lst[int(index)], inval)
                step *= direction
                if index + step < 0 or index + step >= size:
                    direction = direction_stream.next(inval)  # or 1  # raises StopStream
                    step = abs(step) * bi.sign(direction)
                index += step
                index %= size
        except stm.StopStream:
            return inval



### Finite State Machine ###

class Pfsm(ListPattern):
    # // Finite State Machine
    ...

class Pdfsm(ListPattern):
    # // Deterministic Finite State Machine
    ...
