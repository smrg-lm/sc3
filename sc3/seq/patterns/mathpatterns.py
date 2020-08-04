"""From Patterns.sc"""

from ...base import utils as utl
from ...base import builtins as bi
from ...base import stream as stm
from .. import pattern as ptt


### Math patterns ###


class Pseries(ptt.Pattern):
    # // Arithmetic series.
    def __init__(self, start=0.0, step=1.0, length=bi.inf):
        self.start = start
        self.step = step
        self.length = length

    def __embed__(self, inval):
        cur = self.start  # value makes the pattern object to keep state
        length = self.length  # if the parameter is a stream.
        step_stream = stm.stream(self.step)
        outval = stepval = None
        for _ in utl.counter(length):
            try:
                stepval = step_stream.next(inval)
                outval = cur
                cur += stepval
                inval = yield outval
            except stm.StopStream:
                return inval
        return inval

    # storeArgs


class Pgeom(ptt.Pattern):
    # // Geometric series.
    def __init__(self, start=1.0, grow=1.0, length=bi.inf):
        self.start = start
        self.grow = grow
        self.length = length

    def __embed__(self, inval):
        cur = self.start
        length = self.length
        grow_stream = stm.stream(self.grow)
        outval = growval = None
        for _ in utl.counter(length):
            try:
                growval = grow_stream.next(inval)
                outval = cur
                cur *= growval
                inval = yield outval
            except stm.StopStream:
                return inval
        return inval

    # storeArgs


class Pbrown(ptt.Pattern):
    def __init__(self, lo=0.0, hi=1.0, step=0.125, length=bi.inf):
        self.lo = lo
        self.hi = hi
        self.step = step
        self.length = length

    def __embed__(self, inval):
        lo_stream = stm.stream(self.lo)
        hi_stream = stm.stream(self.hi)
        step_stream = stm.stream(self.step)
        try:
            loval = lo_stream.next(inval)
            hival = hi_stream.next(inval)
            stepval = step_stream.next(inval)
            current = bi.rrand(loval, hival)
            for _ in utl.counter(self.length):
                loval = lo_stream.next(inval)
                hival = hi_stream.next(inval)
                stepval = step_stream.next(inval)
                current = bi.fold(
                    self._calc_next(current, stepval), loval, hival)
                inval = yield current
        except stm.StopStream:
            return inval
        return inval

    def _calc_next(self, current, step):
        return current + bi.xrand2(step)

    # storeArgs


class Pgbrown(Pbrown):
    def _calc_next(self, current, step):
        return current * (1 + bi.xrand2(step))


class Pwhite(ptt.Pattern):
    def __init__(self, lo=0.0, hi=1.0, length=bi.inf):
        self.lo = lo
        self.hi = hi
        self.length = length

    def __embed__(self, inval):
        lo_stream = stm.stream(self.lo)
        hi_stream = stm.stream(self.hi)
        hival = loval = None
        for _ in utl.counter(self.length):
            try:
                loval = lo_stream.next(inval)
                hival = hi_stream.next(inval)
                inval = yield bi.rrand(loval, hival)
            except StopStream:
                return inval
        return inval

    # storeArgs


class Pprob(ptt.Pattern):
    def __init__(self, distribution, lo=0.0, hi=1.0,
                 length=bi.inf, table_size=None):
        # ArrayedCollection.asRandomTable
        # ArrayedCollection.tableRand
        ...

    def __embed__(self, inval):
        ...


class Pstep2add(ptt.Pattern):
    ...

    def __embed__(self, inval):
        ...

    # storeArgs


class Pstep3add(ptt.Pattern):
    ...

    def __embed__(self, inval):
        ...

    # storeArgs


class PstepNfunc(ptt.Pattern):
    ...

    def __embed__(self, inval):
        ...

    # storeArgs


class PstepNadd(PstepNfunc):
    ...

    # storeArgs
