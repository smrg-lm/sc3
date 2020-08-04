"""From Patterns.sc & Ppar.sc"""

import logging
import copy

from ...base import stream as stm
from ...base import functions as fn
from ...base import _taskq as tsq
from .. import pattern as ptt
from .. import pausestream as pst
from .. import event as evt
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
        cleanup = pst.EventStreamCleanup()
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
        self.event = event or evt.event()

    def __embed__(self, inval):
        stream = stm.stream(self.pattern)
        while True:
            try:
                inval = yield stream.next(self.event)
            except stm.StopStream:
                return inval

    # storeArgs


class Pbind(ptt.Pattern):
    def __init__(self, *args, **kwargs):
        self.dict = dict(*args, **kwargs)

    def __stream__(self):
        return pst.PatternEventStream(self)

    def __embed__(self, inevent=None):
        event = None
        stream_dict = {k: stm.stream(v) for k, v in self.dict.items()}

        while True:
            if inevent is None:
                return  # Equivalent to ^nil.yield.
            event = inevent.copy()
            for name, stream in stream_dict.items():
                try:
                    stream_out = stream.next(event)
                except stm.StopStream:
                    return inevent
                if isinstance(name, tuple):
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
    def __embed__(self, inevent):
        # assn?
        queue = tsq.TaskQueue()
        for _ in range(self.repeats):
            now = 0.0
            self._init_streams(queue)
            # // If first event not at time zero.
            if not queue.empty():
                nexttime = queue.peek()[0]
                if nexttime > 0.0:
                    outevent = evt.silent(nexttime, inevent)
                    inevent = yield outevent
                    now = nexttime
            while not queue.empty():
                try:
                    stream = queue.pop()[1]
                    outevent = stream.next(inevent)
                    outevent = evt.event(outevent)  # as_event
                    # // Requeue stream.
                    queue.add(now + float(outevent('delta')), stream)
                    nexttime = queue.peek()[0]
                    outevent['delta'] = nexttime - now
                    inevent = yield outevent
                    now = nexttime
                except stm.StopStream:  # next
                    if not queue.empty():
                        # // That child stream ended, so rest until next one.
                        nexttime = queue.peek()[0]
                        outevent = evt.silent(nexttime - now, inevent)
                        inevent = yield outevent
                        now = nexttime
                    else:
                        queue.clear()
            return inevent

    def _init_streams(self, queue):
        for pattern in self.lst:
            queue.add(0.0, stm.stream(pattern))


class Ptpar(Ppar):
    def _init_streams(self, queue):
        for i in range(0, len(self.lst) - 1, 2):  # gen_cclumps(lst, 2)
            queue.add(self.lst[i], stm.stream(self.lst[i + 1]))


class Pgpar(Ppar):
    ...


class Pgtpar(Pgpar):
    ...
