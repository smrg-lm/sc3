"""From Patterns.sc & Ppar.sc"""

import logging
import copy

from ...base import functions as fn
from .. import stream as stm
from .. import pattern as ptt
from . import listpatterns as lsp


_logger = logging.getLogger(__name__)


### Event patterns ###


class Pkey(ptt.Pattern):
    # // Access a key from the input event.
    def __init__(self, key):  # No repeats parameter.
        self.key = key

    def __stream__(self):
        # Simplified: key can't be a stream.
        return stm.FunctionStream(lambda inevent: inevent.get(self.key))  # inevent(self.key))  # *** BUG: would need as_event.

    def __embed__(self, inevent):
        while True:
            inevent = yield inevent(self.key)

    # storeArgs


class Pvalue(ptt.Pattern):
    # Similar to Plazy in Ppatmod.sc but embed is infinite for common objects.
    def __init__(self, func):
        self.func = func

    def __embed__(self, inval):
        value_stream = stm.stream(fn.value(self.func, inval))
        try:
            while True:
                yield value_stream.next(inval)
        except stm.StopStream:
            return inval

    # storeArgs


class Pchain(ptt.Pattern):
    def __init__(self, *patterns):
        self.patterns = list(patterns)

    def chain(self, pattern):  # <>  # *** NOTE: Maybe a function like stm.stream.
        return type(self)(*self.patterns, pattern)

    def __embed__(self, inval=None):
        cleanup = stm.EventStreamCleanup()
        streams = [stm.stream(p) for p in reversed(self.patterns)]
        while True:
            inevent = copy.copy(inval)
            for stream in streams:
                try:
                    inevent = stream.next(inevent)
                except stm.StopStream:
                    return cleanup.exit(inval)
            cleanup.update(inevent)
            inval = yield inevent

    # storeOn


class Pevent(ptt.Pattern):
    def __init__(self, pattern, event=None):
        self.pattern = pattern
        self.event = event or dict()  # *** BUG: Event.default

    def __embed__(self, inval):
        stream = stm.stream(self.pattern)
        while True:
            try:
                inval = yield stream.next(self.event)
            except stm.StopStream:
                return inval

    # storeArgs


class Pbind(ptt.Pattern):
    def __init__(self, *args):
        if len(args) % 2 != 0:
            raise ValueError('Pbind should have even number of args')
        self.pattern_pairs = args

    def __stream__(self):
        return stm.PatternEventStream(self)

    def __embed__(self, inevent=None):
        event = None
        stream_pairs = list(self.pattern_pairs)
        stop = len(stream_pairs)

        for i in range(1, stop, 2):
            stream_pairs[i] = stm.stream(stream_pairs[i])

        while True:
            if inevent is None:
                return  # Equivalent to ^nil.yield.
            event = inevent.copy()
            for i in range(0, stop, 2):
                name = stream_pairs[i]
                stream = stream_pairs[i + 1]
                try:
                    stream_out = stream.next(event)
                except stm.StopStream:
                    return inevent
                if isinstance(name, (list, tuple)):
                    if not isinstance(stream_out, (list, tuple))\
                    or isinstance(stream_out, (list, tuple))\
                    and len(name) > len(stream_out):
                        _logger.warning(
                            'the pattern is not providing enough '
                            f'values to assign to the key set: {name}')
                        return inevent
                    for i, key in enumerate(name):
                        event[key] = stream_out[i]
                else:
                    event[name] = stream_out
            inevent = yield event

    # storeArgs # TODO


class Pmono(ptt.Pattern):
    ...


class PmonoArtic(Pmono):
    ...


### Ppar.sc ###


class Ppar(lsp.ListPattern):
    ...


class Ptpar(Ppar):
    ...


class Pgpar(Ppar):
    ...


class Pgtpar(Pgpar):
    ...
