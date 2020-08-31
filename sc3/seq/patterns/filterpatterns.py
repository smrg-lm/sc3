"""FilterPatterns.sc"""

import copy

from ...base import builtins as bi
from ...base import stream as stm
from ...base import utils as utl
from ...base import functions as fn
from .. import pattern as ptt


utl.ClassLibrary.late_imports(__name__, ('sc3.seq.eventstream', 'est'))


class FilterPattern(ptt.Pattern):
    def __init__(self, pattern):
        self.pattern = pattern


class Pn(FilterPattern):
    # NOTE: For Pn to have 'key' and to be parent of Pgate seems to be a bit
    # arbitrary. A gate is not usually something that repeats n times, moreover
    # Pgate acts like a hold more that a gate.
    def __init__(self, pattern, repeats=bi.inf, key=None):
        super().__init__(pattern)
        self.repeats = repeats
        self.key = key

    def __embed__(self, inevent):
        pattern = self.pattern
        key = self.key
        if key is None:
            for _ in utl.counter(self.repeats):
                inevent = yield from pattern.__embed__(inevent)
        else:
            for _ in utl.counter(self.repeats):
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
        for _ in utl.counter(self.repeats):
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


class Pdur(FilterPattern):  # Was Pfindur.
    def __init__(self, pattern, dur, tolerance=0.001):
        super().__init__(pattern)
        self.dur = dur
        self.tolerance = tolerance

    def __embed__(self, inevent):
        elapsed = 0.0
        local_dur = self.dur
        tolerance = self.tolerance
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
            pass
        return inevent

    # storeArgs


class Psync(FilterPattern):
    ...


class Pconst(FilterPattern):
    ...


class Plag(FilterPattern):
    ...


class Pstutter(FilterPattern):
    ...


class PdurStutter(Pstutter):
    ...


class Pclutch(FilterPattern):
    ...


class Pwhile(FuncFilterPattern):
    ...


class Pwrap(FilterPattern):
    ...


class Ptrace(FilterPattern):
    ...


class Pclump(FilterPattern):
    ...


class Pflatten(Pclump):
    ...


class Pdiff(FilterPattern):
    ...


class Prorate(FilterPattern):
    ...


class Pavaroh(FilterPattern):
    ...
