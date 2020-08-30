"""From Patterns.sc & Ppar.sc"""

import logging
import copy

from ...base import stream as stm
from ...base import builtins as bi
from ...base import utils as utl
from ...base import functions as fn
from ...base import _taskq as tsq
from .. import pattern as ptt
from .. import eventstream as est
from .. import event as evt
from . import listpatterns as lsp


_logger = logging.getLogger(__name__)


### Event patterns ###


class Pkey(ptt.Pattern):
    # // Access a key from the input event.
    def __init__(self, key, length=None):  # Changed: repeats is for lists.
        self.key = key
        self.length = length

    def __stream__(self):
        key_stm = stm.stream(self.key)

        def _stm_func(inevent):
            if inevent is not None:
                try:
                    return inevent[key_stm.next(inevent)]  # raises StopStream
                except KeyError:
                    raise stm.StopStream from None
            else:
                raise stm.StopStream

        func_stm = stm.FunctionStream(_stm_func)
        if self.length is None:
            return func_stm
        else:
            # Object.fin() only used here.
            length = self.length

            def _rtn_func(inevent):
                try:
                    for _ in range(length):
                        inevent = yield func_stm.next(inevent)
                except stm.StopStream:
                    pass

            return stm.Routine(_rtn_func)

    def __embed__(self, inevent):
        if not isinstance(inevent, dict):
            raise TypeError(
                f'inevent must be dict, not {type(inevent).__name__}')
        key_stm = stm.stream(self.key)
        length = self.length or bi.inf
        try:
            for _ in utl.counter(length):
                inevent = (yield inevent[key_stm.next(inevent)]) or dict()
        except (stm.StopStream, KeyError):
            pass
        return inevent

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
            pass
        return inval

    # storeArgs


class EventPattern(ptt.Pattern):
    def __stream__(self):
        return est.PatternEventStream(self)


class Pchain(EventPattern):
    def __init__(self, *patterns):
        self.patterns = list(patterns)

    def chain(self, pattern):  # <>  # *** NOTE: Maybe a function like stm.stream.
        return type(self)(*self.patterns, pattern)

    def __embed__(self, inevent):
        streams = [stm.stream(p) for p in reversed(self.patterns)]
        try:
            while True:
                inevent = inevent.copy()
                for stream in streams:
                    inevent = stream.next(inevent)
                inevent = yield inevent
        except stm.StopStream:
            pass
        return inevent

    # storeOn


class Pevent(EventPattern):
    # This class can be used to change the default value of PatternEventStream.
    def __init__(self, pattern, event):
        self.pattern = pattern
        self.event = event

    def __embed__(self, inevent):
        stream = stm.stream(self.pattern)
        try:
            while True:
                inevent = yield stream.next(self.event)
        except stm.StopStream:
            pass
        return inevent

    # storeArgs


class Pbind(EventPattern):
    def __init__(self, mapping):
        self.dict = dict(mapping)

    def __embed__(self, inevent):
        event = None
        stream_dict = {k: stm.stream(v) for k, v in self.dict.items()}

        try:
            while True:
                if inevent is None:
                    return  # Equivalent to ^nil.yield.
                event = inevent.copy()
                event.update(self._stream_dict_next(stream_dict))
                inevent = yield event
        except stm.StopStream:
            pass
        return inevent

    @staticmethod
    def _stream_dict_next(stream_dict):
        event = dict()
        for name, stream in stream_dict.items():
            stream_out = stream.next(event)  # raises StopStream
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
        return event

    # storeArgs # TODO


class Pmono(Pbind):
    _kept_keys = {'server', 'node_id', 'has_gate'}

    def __init__(self, synth_name, mapping, articulate=False):
        super().__init__(mapping)
        self.synth_name = synth_name
        self.articulate = articulate

    def __embed__(self, inevent):
        if self.articulate:
            return (yield from self._embed_mono_artic(inevent))
        else:
            return (yield from self._embed_mono(inevent))

    def _embed_mono(self, inevent):
        synth_name = self.synth_name
        kept_keys = self._kept_keys
        stream_dict = {k: stm.stream(v) for k, v in self.dict.items()}
        cleanup = est.CleanupEntry()
        server = node_id = mono_params = event = None

        try:
            while True:
                if node_id is None:
                    event = evt.event(inevent, type='_mono_on')
                    event.update(self._stream_dict_next(stream_dict))
                    event._prepare_event(synth_name)
                    server = event['server']
                    node_id = event['node_id']
                    mono_params = event['msg_params'][::2]  # For _update_msg_params
                    cleanup.add_event(evt.event(
                        {k: event[k] for k in kept_keys}, type='_mono_off'))
                    inevent = yield event
                else:
                    event = evt.event(inevent, type='_mono_set')
                    event.update(self._stream_dict_next(stream_dict))
                    event['server'] = server
                    event['node_id'] = node_id
                    event['mono_params'] = mono_params
                    inevent = yield event
        except stm.StopStream:
            cleanup.run()
        return inevent

    def _embed_mono_artic(self, inevent):
        synth_name = self.synth_name
        kept_keys = self._kept_keys
        stream_dict = {k: stm.stream(v) for k, v in self.dict.items()}
        cleanup = est.CleanupEntry()
        server = node_id = mono_params = event = cleanup_event = None

        try:
            while True:
                if node_id is None:
                    event = evt.event(inevent, type='_mono_on')
                    event.update(self._stream_dict_next(stream_dict))
                    event._prepare_event(synth_name)
                    if event('sustain') >= event('delta')\
                    and not evt.is_rest(event):
                        server = event['server']
                        node_id = event['node_id']
                        mono_params = event['msg_params'][::2]  # For _update_msg_params
                        cleanup_event = evt.event(
                            {k: event[k] for k in kept_keys}, type='_mono_off')
                        cleanup.add_event(cleanup_event)
                        inevent = yield event
                    else:
                        event = evt.event(event, type='note')
                        inevent = yield event
                else:
                    event = evt.event(inevent, type='_mono_set')
                    event.update(self._stream_dict_next(stream_dict))
                    event['server'] = server
                    event['node_id'] = node_id
                    event['mono_params'] = mono_params
                    if event('sustain') < event('delta'):
                        cleanup_event['delay'] = event('sustain')
                        cleanup_event.play()
                        cleanup.remove_event(cleanup_event)
                        node_id = None
                    elif evt.is_rest(event):
                        cleanup_event.play()
                        cleanup.remove_event(cleanup_event)
                        node_id = None
                    inevent = yield event
        except stm.StopStream:
            cleanup.run()
        return inevent


### Ppar.sc ###


class Ppar(EventPattern):
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
