"""From Patterns.sc"""

from ...base import builtins as bi
from ...base import stream as stm
from ...base import main as _libsc3
from .. import pattern as ptt
from .. import eventstream as est


class ValuePattern(ptt.Pattern):
    def __stream__(self):
        return est.PatternValueStream(self)


class Pvalue(ValuePattern):
    # This pattern is for special cases where common
    # values aren't or can't be embeded as streams.
    def __init__(self, value):
        self.value = value

    def __embed__(self, inval):
        return (yield from stm.embed(self.value, inval))

    # storeArgs


### Math patterns ###


class Pseries(ValuePattern):
    # // Arithmetic series.
    def __init__(self, start=0.0, step=1.0, length=float('inf')):
        self.start = start
        self.step = step
        self.length = length

    def __embed__(self, inval):
        cur = self.start  # value makes the pattern object to keep state
        length = self.length  # if the parameter is a stream.
        step_stream = stm.stream(self.step)
        outval = stepval = None
        try:
            for _ in bi.counter(length):
                stepval = step_stream.next(inval)
                outval = cur
                cur += stepval
                inval = yield outval
        except stm.StopStream:
            pass
        return inval

    # storeArgs


class Pgeom(ValuePattern):
    # // Geometric series.
    def __init__(self, start=1.0, grow=1.0, length=float('inf')):
        self.start = start
        self.grow = grow
        self.length = length

    def __embed__(self, inval):
        cur = self.start
        length = self.length
        grow_stream = stm.stream(self.grow)
        outval = growval = None
        try:
            for _ in bi.counter(length):
                growval = grow_stream.next(inval)
                outval = cur
                cur *= growval
                inval = yield outval
        except stm.StopStream:
            pass
        return inval

    # storeArgs


class Pbrown(ValuePattern):
    def __init__(self, lo=0.0, hi=1.0, step=0.125, length=float('inf')):
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
            for _ in bi.counter(self.length):
                loval = lo_stream.next(inval)
                hival = hi_stream.next(inval)
                stepval = step_stream.next(inval)
                current = bi.fold(
                    self._calc_next(current, stepval), loval, hival)
                inval = yield current
        except stm.StopStream:
            pass
        return inval

    def _calc_next(self, current, step):
        return current + bi.xrand2(step)

    # storeArgs


class Pgbrown(Pbrown):
    def _calc_next(self, current, step):
        return current * (1 + bi.xrand2(step))


class Pwhite(ValuePattern):
    def __init__(self, lo=0.0, hi=1.0, length=float('inf')):
        self.lo = lo
        self.hi = hi
        self.length = length

    def __embed__(self, inval):
        lo_stream = stm.stream(self.lo)
        hi_stream = stm.stream(self.hi)
        hival = loval = None
        try:
            for _ in bi.counter(self.length):
                loval = lo_stream.next(inval)
                hival = hi_stream.next(inval)
                inval = yield bi.rrand(loval, hival)
        except stm.StopStream:
            pass
        return inval

    # storeArgs


class Pprob(ValuePattern):
    def __init__(self, distribution, lo=0.0, hi=1.0,
                 table_size=None, length=float('inf')):
        self.distribution = distribution
        self.lo = lo
        self.hi = hi
        # Patterns arguments should be constant after instantiation.
        self.table_size = table_size or max(64, len(distribution))
        self.table = bi.as_random_table(distribution, self.table_size)
        self.length = length

    def __embed__(self, inval):
        table = self.table
        lo_stream = stm.stream(self.lo)
        hi_stream = stm.stream(self.hi)
        lval = hval = None
        try:
            for _ in bi.counter(self.length):
                lval = lo_stream.next(inval)
                hval = hi_stream.next(inval)
                inval = yield (bi.table_rand(table) * (hval - lval)) + lval
        except stm.StopStream:
            pass
        return inval


### Random distribution patterns ###


class Plprand(Pwhite):  # It iherits just for the constructor.
    def __embed__(self, inval):
        pw = Pwhite(self.lo, self.hi, self.length)  # type(self).__base__(lo, hi, length)
        return (yield from stm.embed(bi.min(pw, pw), inval))


class Phprand(Pwhite):
    def __embed__(self, inval):
        pw = Pwhite(self.lo, self.hi, self.length)
        return (yield from stm.embed(bi.max(pw, pw), inval))


class Pmeanrand(Pwhite):
    def __embed__(self, inval):
        pw = Pwhite(self.lo, self.hi, self.length)
        return (yield from stm.embed((pw + pw) * 0.5, inval))


class Pbeta(ValuePattern):
    def __init__(self, lo=0.0, hi=1.0, prob1=1, prob2=1, length=float('inf')):
        self.lo = lo
        self.hi = hi
        self.prob1 = prob1
        self.prob2 = prob2
        self.length = length

    def __embed__(self, inval):
        lo_stream = stm.stream(self.lo)
        hi_stream = stm.stream(self.hi)
        prob1_stream = stm.stream(self.prob1)
        prob2_stream = stm.stream(self.prob2)
        loval = hival = sum = temp = rprob1 = rprob2 = None
        try:
            for _ in bi.counter(self.length):
                sum = 2
                rprob1 = bi.reciprocal(prob1_stream.next(inval))
                rprob2 = bi.reciprocal(prob2_stream.next(inval))
                loval = lo_stream.next(inval)
                hival = hi_stream.next(inval)
                while sum > 1:
                    temp = bi.rand(1.0) ** rprob1
                    sum = temp + bi.rand(1.0) ** rprob2
                inval = yield temp / sum * (hival - loval) + loval
        except stm.StopStream:
            pass
        return inval


class Pcauchy(ValuePattern):
    def __init__(self, mean=0.0, spread=1.0, length=float('inf')):
        self.mean = mean
        self.spread = spread
        self.length = length

    def __embed__(self, inval):
        mean_stream = stm.stream(self.mean)
        spread_stream = stm.stream(self.spread)
        ran = meanval = spreadval = None
        try:
            for _ in bi.counter(self.length):
                ran = 0.5
                meanval = mean_stream.next(inval)
                spreadval = spread_stream.next(inval)
                while ran == 0.5:
                    ran = bi.rand(1.0)
                inval = yield spreadval * bi.tan(ran * bi.pi) + meanval
        except stm.StopStream:
            pass
        return inval


class Pgauss(ValuePattern):
    def __init__(self, mean=0.0, dev=1, length=float('inf')):
        self.mean = mean
        self.dev = dev
        self.length = length

    def __embed__(self, inval):
        mean_stream = stm.stream(self.mean)
        dev_stream = stm.stream(self.dev)
        devval = meanval = None
        try:
            for _ in bi.counter(self.length):
                devval = dev_stream.next(inval)
                meanval = mean_stream.next(inval)
                inval = yield bi.sqrt(-2 * bi.log(bi.rand(1.0))) * bi.sin(bi.rand(bi.pi2)) * devval + meanval
        except stm.StopStream:
            pass
        return inval


class Ppoisson(ValuePattern):
    def __init__(self, mean=1, length=float('inf')):
        self.mean = mean
        self.length = length

    def __embed__(self, inval):
        mean_stream = stm.stream(self.mean)
        meanval = inc = test = temp = None
        try:
            for _ in bi.counter(self.length):
                meanval = mean_stream.next(inval)
                inc = 0
                test = bi.rand(1.0)
                temp = bi.exp(-meanval)
                while test > temp:
                    inc += 1
                    test = test * bi.rand(1.0)
                inval = yield inc
        except stm.StopStream:
            pass
        return inval


class Pexprand(ValuePattern):
    def __init__(self, lo=0.0001, hi=1.0, length=float('inf')):
        self.lo = lo
        self.hi = hi
        self.length = length

    def __embed__(self, inval):
        lo_stream = stm.stream(self.lo)
        hi_stream = stm.stream(self.hi)
        loval = hival = None
        try:
            for _ in bi.counter(self.length):
                loval = lo_stream.next(inval)
                hival = hi_stream.next(inval)
                inval = yield bi.exprand(loval, hival)
        except stm.StopStream:
            pass
        return inval
