"""From Patterns.sc"""

import inspect

from ...base import stream as stm
from ...base import builtins as bi
from .. import pattern as ptt


class FunctionPattern(ptt.Pattern):
    pass


class Pfunc(FunctionPattern):
    def __init__(self, next_func, reset_func=None, data=None):
        self.next_func = next_func
        self.reset_func = reset_func
        self.data = data

    def __stream__(self):
        return stm.FunctionStream(self.next_func, self.reset_func, self.data)

    # storeArgs


class Prout(FunctionPattern):
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


class Pfuncn(FunctionPattern):
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


class Plazy(FunctionPattern):
    def __init__(self, func):
        self.func = func

    def __embed__(self, inval):
        return (yield from stm.embed(self.func(inval), inval))

    # storeArgs


class Pproduct(FunctionPattern):  # Was PstepNfunc.
    def __init__(self, func, patterns):
        self.func = func or (lambda values: values)
        self.patterns = patterns

    def __embed__(self, inval):
        # If there wasn't inval things would be much easier.
        # for t in itertools.product(*self.patterns): ...
        patterns = self.patterns
        size = len(patterns)
        max_level = size - 1
        streams = [None] * size
        values = [None] * size
        yield from self._recgen(inval, 0, max_level, patterns, streams, values)

    def _recgen(self, inval, level, max_level, patterns, streams, values):
        try:
            streams[level] = stm.stream(patterns[level])
            while True:
                values[level] = streams[level].next(inval)
                if level < max_level:
                    yield from self._recgen(
                        inval, level + 1, max_level, patterns, streams, values)
                else:
                    yield self.func(values)
        except stm.StopStream:
            pass
        return inval

    # storeArgs


# Superseded by PstepNfunc (Pproduct).
# class Pstep2add(FunctionPattern)
# class Pstep3add(FunctionPattern)
# class PstepNadd(PstepNfunc)


# BUG: ver su utilidad, qué diferencia hay
# con usar un operador enario directamente?
# class PdegreeToKey(Pnarop):
#     ...


class Pif(FunctionPattern):
    # This implementation is a bit different from the original, there is no
    # default value and the stream ends with the first raised StopStream.
    def __init__(self, condition, iftrue, iffalse):
        self.condition = condition
        self.iftrue = iftrue
        self.iffalse = iffalse

    def __stream__(self):
        cond_stream = stm.stream(self.condition)
        true_stream = stm.stream(self.iftrue)
        false_stream = stm.stream(self.iffalse)

        def next_func(inval):
            test = cond_stream.next(inval)
            if test:
                return true_stream.next(inval)
            else:
                return false_stream.next(inval)

        def reset_func():
            cond_stream.reset()
            true_stream.reset()
            false_stream.reset()

        return stm.FunctionStream(next_func, reset_func)
