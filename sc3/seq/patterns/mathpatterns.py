"""From Patterns.sc"""


from .. import stream as stm
from .. import pattern as ptt


### Math patterns ###


class Pseries(ptt.Pattern):
    # // Arithmetic series.
    def __init__(self, start=0, step=1, length=None):  # *** BUG: length = inf
        self.start = start
        self.step = step
        self.length = length

    def __embed__(self, inval):
        counter = 0
        cur = self.start  # value makes the pattern object to keep state
        len = self.length  # if the parameter is a stream.
        step_stream = stm.stream(self.step)
        outval = stepval = None
        while counter < len:
            try:
                stepval = step_stream.next(inval)
                outval = cur
                cur += stepval
                counter += 1
                inval = yield outval
            except stm.StopStream:
                return inval
        return inval

    # storeArgs


class Pgeom(ptt.Pattern):
    # // Geometric series.
    def __init__(self, start=0, grow=1, length=None):  # *** BUG: length = inf
        self.start = start
        self.grow = grow
        self.length = length

    def __embed__(self, inval):
        ...

    # storeArgs


class Pbrown(ptt.Pattern):
    ...

    def __embed__(self, inval):
        ...

    def _calc_next(self, cur, step):
        ...

    # storeArgs


class Pgbrown(Pbrown):
    def _calc_next(self, cur, step):
        ...


class Pwhite(ptt.Pattern):
    ...

    def __embed__(self, inval):
        ...

    # storeArgs


class Pprob(ptt.Pattern):
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
