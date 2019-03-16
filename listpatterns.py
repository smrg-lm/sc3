"""ListPatterns.sc"""

import collections

import supercollie.stream as stm
import supercollie.patterns as ptt


# class Pindex(ptt.Pattern):
#     pass # TODO: ver qué patrones definen funcionalidad excepcional


class ListPattern(ptt.Pattern):
    def __init__(self, lst=[], repeats=1):
        if len(lst) > 0:
            self.lst = lst
            self.repeats = repeats
        else:
            msg = "ListPattern '{}' requires a non empty collection, received: {}"
            raise Exception(msg.format(type(self).__name__, lst))

    # copy # BUG: copia la lista lst
    # storeArgs # TODO


class Pseq(ListPattern):
    def __init__(self, lst, repeats=1, offset=0):
        super().__init__(lst, repeats)
        self.offset = offset

    def __embed__(self, inval=None):
        offset = self.offset # BUG: en realidad llama a value todo este if/else no específicamente next.
                             # BUG: ************** puede ser que llame a value no porque sea un stream sino una función que
                             # BUG: ************** modifican el comportamiento de repeats y offset según los datos el evento.
        # if (inval.eventAt('reverse') == true, { # BUG: TODO: No se si es bueno que el evento defina el comportamiento dle pattern.
        repeats = self.repeats
        lst = collections.deque(self.lst)
        lst.rotate(offset) # TODO: tal vez usa wrapAt porque rotar es más costoso y genera un pico.
        for i in range(repeats):
            for item in lst:
                inval = yield from stm.embed(item, inval)

    # storeArgs # TODO








# TODO: sigue
