"""From Patterns.sc"""

import inspect

from ...base import stream as stm
from ...base import builtins as bi
from .. import pattern as ptt


### Function patterns ###


class Pfunc(ptt.Pattern):
    def __init__(self, next_func, reset_func=None, data=None):
        self.next_func = next_func
        self.reset_func = reset_func
        self.data = data

    def __stream__(self):
        return stm.FunctionStream(self.next_func, self.reset_func, self.data)

    # storeArgs


class Prout(ptt.Pattern):
    def __init__(self, func):
        self.func = func
        self._func_has_inval = (  # See note in TimeThread.__init__. Sync code.
            len(inspect.signature(self.func).parameters) > 0)
        self._func_isgenfunc = inspect.isgeneratorfunction(self.func)

    def __stream__(self):
        return stm.Routine(self.func)

    def __embed__(self, inval):
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


class Pfuncn(ptt.Pattern):
    def __init__(self, func, repeats=1):
        self.func = func
        self._func_has_inval = (  # See note in TimeThread.__init__. Sync code.
            len(inspect.signature(self.func).parameters) > 0)
        self.repeats = repeats

    def __embed__(self, inval):
        for i in bi.counter(self.repeats):
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
