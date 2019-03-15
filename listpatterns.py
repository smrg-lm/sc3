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

    def iter(self, inval=None):
        def _gi(inval):
            if isinstance(self.offset, stm.Stream): # BUG: todos estos checks son signo de polimorfismo, o tendría que convertir todos los parámetros en streams.
                offset = self.offset.next(inval)
            else:
                offset = self.offset
            # if (inval.eventAt('reverse') == true, { # BUG: TODO
            if isinstance(self.repeats, stm.Stream):
                repeats = self.repeats.next(inval)
            else:
                repeats = self.repeats
            lst = collections.deque(self.lst)
            lst.rotate(offset) # TODO: tal vez usa wrapAt porque rotar es más costoso y genera un pico.
            for i in range(repeats):
                for item in lst:
                    if isinstance(item, stm.Stream): # BUG: o puede ser otro iterador? y la expansión multicanal dónde se produce?
                        inval = yield from item.iter(inval)
                    else:
                        inval = yield item # BUG: embedInStream hace this.yield en Object
            #return inval # BUG: no recuerdo si esto tiene efecto, creo que no
        return _gi(inval) # BUG: comprobar que inval está bien como parámetro de iter()

    # storeArgs # TODO








# TODO: sigue
