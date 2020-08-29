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
        self.pattern = pattern
        self.repeats = repeats
        self.key = key

    def __stream__(self):
        return est.PatternEventStream(self)

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


# Pselect
# Preject
# Pfset
# Psetpre
# Paddpre
# Pmulpre
# Pset
# Padd
# Pmul
# Psetp
# Paddp
# Pmulp
# Pstretch
# Pstretchp
# Pplayer
# Pdrop
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


class Pfin(FilterPattern):
    def __init__(self, count, pattern):
        self.pattern = pattern
        self.count = count

    def __embed__(self, inevent):
        stream = stm.stream(self.pattern)
        try:
            for _ in utl.counter(self.count):
                inevent = stream.next(inevent)
                inevent = yield inevent
        except stm.StopStream:
            pass
        return inevent

    # storeArgs


# And more...
