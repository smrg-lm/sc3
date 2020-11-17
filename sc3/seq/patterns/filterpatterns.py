"""FilterPatterns.sc"""

import copy
import logging

from ...base import builtins as bi
from ...base import stream as stm
from ...base import utils as utl
from ...base import functions as fn
from .. import pattern as ptt
from .. import event as evt


class FilterPattern(ptt.Pattern):
    def __init__(self, pattern):
        self.pattern = pattern
        self._is_event_pattern = pattern.is_event_pattern

    @property
    def is_event_pattern(self):
        return self._is_event_pattern


class Pn(FilterPattern):
    # NOTE: For Pn to have 'key' and to be parent of Pgate seems to be a bit
    # arbitrary. A gate is not usually something that repeats n times, moreover
    # Pgate acts like a hold more that a gate.
    def __init__(self, pattern, repeats=float('inf'), key=None):
        super().__init__(pattern)
        self.repeats = repeats
        self.key = key

    def __embed__(self, inevent):
        pattern = self.pattern
        key = self.key
        if key is None:
            for _ in bi.counter(self.repeats):
                inevent = yield from pattern.__embed__(inevent)
        else:
            for _ in bi.counter(self.repeats):
                inevent[key] = True
                inevent = yield from pattern.__embed__(inevent)
            inevent[key] = False
        return inevent

    # storeArgs


class Pgate(Pn):
    def __embed__(self, inevent):
        pattern = self.pattern
        key = self.key
        stream = output = None
        for _ in bi.counter(self.repeats):
            stream = stm.stream(pattern)
            try:
                while True:
                    if inevent.get(key, False) is True or output is None:
                        output = stream.next(inevent)
                    inevent = yield from stm.embed(copy.copy(output), inevent)
            except stm.StopStream:
                pass
            output = None  # // Force new value for every repeat.
        return inevent

    # storeArgs


class FuncFilterPattern(FilterPattern):
    def __init__(self, func, pattern):
        super().__init__(pattern)
        self.func = func

    # storeArgs


class Pcollect(FuncFilterPattern):
    def __embed__(self, inval):
        func = self.func
        stream = stm.stream(self.pattern)
        outval = None
        try:
            while True:
                outval = stream.next(inval)
                inval = yield fn.value(func, outval, inval)
        except stm.StopStream:
            pass
        return inval

    # asStream  # For some reason it converts to a FunctonStream.


class Pselect(FuncFilterPattern):
    def __embed__(self, inval):
        func = self.func
        stream = stm.stream(self.pattern)
        outval = None
        try:
            while True:
                outval = stream.next(inval)
                if fn.value(func, outval, inval) is True:
                    inval = yield outval
        except stm.StopStream:
            pass
        return inval

    # asStream  # Idem.


class Preject(FuncFilterPattern):
    def __embed__(self, inval):
        func = self.func
        stream = stm.stream(self.pattern)
        outval = None
        try:
            while True:
                outval = stream.next(inval)
                if fn.value(func, outval, inval) is False:
                    inval = yield outval
        except stm.StopStream:
            pass
        return inval

    # asStream  # Idem.


# These are all specific variants of Pchain + Pcollect.
# class Pfset(FuncFilterPattern): ...
# class Psetpre(FilterPattern): ...
# class Paddpre(Psetpre): ...
# class Pmulpre(Psetpre): ...
# class Pset(FilterPattern): ...
# class Padd(Pset): ...
# class Pmul(Pset): ...
# class Psetp(Pset): ...
# class Paddp(Psetp): ...
# class Pmulp(Psetp): ...
# class Pstretch(FilterPattern): ...
# class Pstretchp(Pstretch): ...
# class Pbindf(FilterPattern): ...


# class Pplayer(FilterPattern):  # Undocumented, with note.


class Pdrop(FilterPattern):
    def __init__(self, pattern, n):
        super().__init__(pattern)
        self.n = int(n)

    def __embed__(self, inval):
        stream = stm.stream(self.pattern)
        first_inval = inval
        try:
            for _ in range(self.n):
                inval = stream.next(first_inval)
            while True:
                inval = yield stream.next(inval)
        except stm.StopStream:
            pass
        return inval

    # storeArgs


class Plen(FilterPattern):  # Was Pfin.
    def __init__(self, pattern, n):
        super().__init__(pattern)
        self.n = int(n)

    def __embed__(self, inval):
        stream = stm.stream(self.pattern)
        try:
            for _ in range(self.n):
                inval = yield stream.next(inval)
        except stm.StopStream:
            pass
        return inval

    # storeArgs


class Pdur(ptt.EventPattern, FilterPattern):  # Was Pfindur.
    def __init__(self, pattern, dur, tolerance=0.001, quant=None):
        super(ptt.EventPattern, self).__init__(pattern)
        self.dur = dur
        self.tolerance = tolerance
        self.quant = quant

    def __embed__(self, inevent):
        elapsed = 0.0
        local_dur = self.dur
        tolerance = self.tolerance
        quant = self.quant
        stream = stm.stream(self.pattern)
        delta = next_elapsed = remaining = None
        try:
            while True:
                inevent = stream.next(inevent)
                delta = inevent('delta')
                next_elapsed = elapsed + float(delta)
                if bi.roundup(next_elapsed, tolerance) >= local_dur:
                    remaining = local_dur - elapsed
                    inevent = inevent.copy()
                    inevent['delta'] = type(delta)(remaining)
                    return (yield inevent)
                elapsed = next_elapsed
                inevent = yield inevent
        except stm.StopStream:
            if quant is not None:
                delta = bi.roundup(elapsed, quant) - elapsed
                if delta > 0:
                    inevent = yield evt.silent(delta, inevent)
        return inevent

    # storeArgs


# class Psync(FilterPattern):  # Added as quant to Pdur.


class Pconst(FilterPattern):
    def __init__(self, pattern, sum, tolerance=0.001):
        super().__init__(pattern)
        self.sum = sum
        self.tolerance = tolerance

    def __embed__(self, inval):
        stream = stm.stream(self.pattern)
        local_sum = self.sum
        tolerance = self.tolerance
        sum = next_sum = 0
        value = None
        try:
            while True:
                value = stream.next(inval)
                next_sum = sum + value
                if bi.roundup(next_sum, tolerance) >= local_sum:
                    inval = yield local_sum - sum
                    return inval
                sum = next_sum
                inval = yield value
        except stm.StopStream:
            inval = yield local_sum - sum
        return inval


class Plag(ptt.EventPattern, FilterPattern):
    def __init__(self, pattern, lag):
        super(ptt.EventPattern, self).__init__(pattern)
        self.lag = lag

    def __embed__(self, inevent):
        yield evt.silent(self.lag, inevent)
        return (yield from stm.embed(self.pattern, inevent))

    # storeArgs


class Pstutter(FilterPattern):
    def __init__(self, pattern, n):
        super().__init__(pattern)
        self.n = n

    def __embed__(self, inval):
        stream = stm.stream(self.pattern)
        n_stream = stm.stream(self.n)
        value = n = None
        try:
            while True:
                value = stream.next(inval)
                n = n_stream.next(inval)
                for _ in range(abs(n)):
                    inval = yield copy.copy(value)
        except stm.StopStream:
            pass
        return inval

    # storeArgs


# class PdurStutter(Pstutter):  # Tremolo-like partition.


class Platch(FilterPattern):  # Was Pclutch.
    class _UNDEFINED(): pass

    def __init__(self, pattern, trig=True):
        super().__init__(pattern)
        self.trig = trig

    def __embed__(self, inval):
        stream = stm.stream(self.pattern)
        trig_stream = stm.stream(self.trig)
        UNDEFINED = self._UNDEFINED
        last_inval = UNDEFINED
        trig = None
        try:
            while True:
                trig = trig_stream.next(inval)
                if trig:
                    last_inval = stream.next(inval)
                    inval = yield last_inval
                else:
                    if last_inval is UNDEFINED:
                        last_inval = stream.next(inval)
                    inval = yield copy.copy(last_inval)
        except stm.StopStream:
            pass
        return inval

    # storeArgs


class Pwhile(FuncFilterPattern):
    def __embed__(self, inval):
        func = self.func
        pattern = self.pattern
        while fn.value(func, inval):
            inval = yield from stm.embed(pattern, inval)
        return inval


class Pwrap(FilterPattern):
    def __init__(self, pattern, lo, hi):
        super().__init__(pattern)
        self.lo = lo
        self.hi = hi

    def __embed__(self, inval):
        stream = stm.stream(self.pattern)
        lo_stream = stm.stream(self.lo)
        hi_stream = stm.stream(self.hi)
        value = lo = hi = None
        try:
            while True:
                lo = lo_stream.next(inval)
                hi = hi_stream.next(inval)
                value = stream.next(inval)
                inval = yield bi.wrap(value, lo, hi)
        except stm.StopStream:
            pass
        return inval

    # storeArgs


class Ptrace(FilterPattern):
    _ptrace_logger = logging.getLogger('Ptrace')

    def __init__(self, pattern, prefix=None, keys=None):
        super().__init__(pattern)
        self.prefix = prefix or ''
        self.keys = keys

    def __embed__(self, inval):
        logger = self._ptrace_logger
        stream = stm.stream(self.pattern)
        prefix = self.prefix
        keys = self.keys
        calc_keys = True
        outval = None
        try:
            if self.keys:
                while True:
                    outval = stream.next(inval)
                    if calc_keys:
                        if isinstance(outval, evt.EventType):
                            keys = tuple(
                                k for k in keys if k in outval\
                                or k in outval.default_values)
                        else:
                            keys = tuple()
                        calc_keys = False
                    logger.info('%s%s', prefix, {k: outval(k) for k in keys})
                    inval = yield outval
            else:
                while True:
                    outval = stream.next(inval)
                    logger.info('%s%s', prefix, outval)
                    inval = yield outval
        except stm.StopStream:
            pass
        return inval

    # storeArgs


class Pclump(FilterPattern):
    def __init__(self, pattern, n):
        super().__init__(pattern)
        self.n = n

    def __embed__(self, inval):
        stream = stm.stream(self.pattern)
        n_stream = stm.stream(self.n)
        lst = n = value = None
        try:
            while True:
                lst = []
                n = n_stream.next(inval)
                for _ in range(int(n)):
                    value = stream.next(inval)
                    lst.append(value)
                inval = yield lst
        except stm.StopStream:
            if lst:
                inval = yield lst
        return inval

    # storeArgs


class Pflatten(Pclump):
    def __embed__(self, inval):
        stream = stm.stream(self.pattern)
        n_stream = stm.stream(self.n)
        flatten = utl.flatten
        n = value = None
        try:
            while True:
                n = n_stream.next(inval)
                value = stream.next(inval)
                if isinstance(value, list):
                    value = flatten([value], n)
                    for item in value:
                        inval = yield item
                else:
                    inval = yield value
        except stm.StopStream:
            pass
        return inval


class Pdiff(FilterPattern):
    def __embed__(self, inval):
        stream = stm.stream(self.pattern)
        prev = next = None
        try:
            prev = stream.next(inval)
            while True:
                next = stream.next(inval)
                inval = yield next - prev
                prev = next
        except stm.StopStream:
            pass
        return inval


class Pprorate(FilterPattern):  # Was Protate.
    def __init__(self, pattern, proportion=1):
        super().__init__(pattern)
        self.proportion = proportion

    def __embed__(self, inval):
        stream = stm.stream(self.pattern)
        prop_stream = stm.stream(self.proportion)
        value = c = None
        try:
            while True:
                value = stream.next(inval)
                c = prop_stream.next(inval)
                if isinstance(c, (list, tuple)):
                    for el in c:
                        inval = yield el * value
                else:
                    inval = yield c * value
                    inval = yield (1 - c) * value
        except stm.StopStream:
            pass
        return inval

    # storeArgs


class Pavaroh(FilterPattern):
    def __init__(self, pattern, aroh, avaroh, spo=12):
        super().__init__(pattern)
        self.aroh = aroh  # Aroh and avaroh are Scale objects.
        self.avaroh = avaroh
        self.spo = spo

    def __embed__(self, inval):
        stream = stm.stream(self.pattern)
        spo_stream = stm.stream(self.spo)
        aroh = self.aroh
        avaroh = self.avaroh
        spo = me = scale = None
        melast = 0
        try:
            while True:
                spo = spo_stream.next(inval)
                me = stream.next(inval)
                scale = aroh if me >= melast else avaroh
                melast = me
                inval = yield scale.degree_to_key(me)
        except stm.StopStream:
            pass
        return inval

    # storeArgs
