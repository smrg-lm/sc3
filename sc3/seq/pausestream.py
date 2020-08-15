"""Stream.sc part 2"""

import logging

from ..base import stream as stm
from ..base import systemactions as sac
from ..base import clock as clk
from . import event as evt


__all__ = []


_logger = logging.getLogger(__name__)


### Higher level abstractions ###


# class OneShotStream(Stream): ... # TODO: ver para qué sirve, la única referencia está en Object:iter, no está documentada.
# class EmbedOnce(Stream): ... # TODO, ver, solo se usa en JITLib, no está documentada.
# class StreamClutch(Stream): ... # TODO: no se usa en la librería de clases, actúa como un filtro, sí está documentada.
# class CleanupStream(Stream): ... # TODO: no se usa en la librería de clases, creo, ver bien, no tiene documentación.


### EventStreamCleanup.sc ###


class EventStreamCleanup():
    # // Cleanup functions are passed a flag. The flag is set false if nodes
    # // have already been freed by CmdPeriod. This caused a minor change to
    # // TempoClock:clear and TempoClock:cmdPeriod

    def __init__(self):
        # // cleanup functions from child streams and parent stream
        self.functions = set()

    def add_function(self, event, func):
        if isinstance(event, dict):
            self.functions.add(func)
            if 'add_to_cleanup' not in event:
                event['add_to_cleanup'] = []
            event['add_to_cleanup'].append(func)

    def add_node_cleanup(self, event, func):
        if isinstance(event, dict):
            self.functions.add(func)
            if 'add_to_node_cleanup' not in event:
                event['add_to_node_cleanup'] = []
            event['add_to_node_cleanup'].append(func)

    def update(self, event):
        if isinstance(event, dict):
            if 'add_to_node_cleanup' in event:
                self.functions.update(event['add_to_node_cleanup'])
            if 'add_to_cleanup' in event:
                self.functions.update(event['add_to_cleanup'])
            if 'remove_from_cleanup' in event:
                for item in event['remove_from_cleanup']:
                    self.functions.discard(item)
        return event

    def exit(self, event, free_nodes=True):
        if isinstance(event, dict):
            self.update(event)
            for func in self.functions:
                func(free_nodes)
            if 'remove_from_cleanup' not in event:
                event['remove_from_cleanup'] = []
            event['remove_from_cleanup'].extend(self.functions)
            self.clear()
        return event

    def terminate(self, free_nodes=True):
        for func in self.functions:
            func(free_nodes)
        self.clear()

    def clear(self):
        self.functions = set()


class EventStreamPlayer(stm.Routine):
    def __init__(self, stream, event=None):
        super().__init__(self._stream_player_func())
        self._stream = stream
        self._event = event or evt.event()
        self._is_muted = False
        self.cleanup = EventStreamCleanup()

    def mute(self):
        self._is_muted = True

    def unmute(self):
        self._is_muted = False

    def reset(self):
        with self._state_cond:
            super().reset()
            self._stream.reset()
            self.cleanup.terminate()

    def resume(self, clock=None, quant=None):
        with self._state_cond:
            if self.state == self.State.Paused:
                self.state = self.State.Suspended
                clock = clock or self._clock or clk.TempoClock.default
                self._event, quant = self._synch_with_quant(self._event, quant)
                clock.play(self, quant)

    def stop(self):
        with self._state_cond:
            super().stop()
            self._on_stop_cleanup()

    def _on_stop_cleanup(self):
        self.cleanup.terminate()
        sac.CmdPeriod.remove(self.__on_cmd_period)

    def _stream_player_func(self):
        def esp_func():
            while True:
                try:
                    outevent = self._stream.next(self._event.copy())
                    yield self._play_and_delta(outevent)
                except stm.StopStream:
                    self._on_stop_cleanup()
                    return
        return esp_func

    def _play_and_delta(self, outevent):  # Was Event.playAndDelta.
        self.cleanup.update(outevent)
        if not (self._is_muted or evt.is_rest(outevent)):
            outevent.play()
        return outevent('delta')

    def play(self, clock=None, quant=None, reset=False):
        if reset:
            self.reset()
        with self._state_cond:
            if self.state == self.State.Init\
            or self.state == self.state.Paused:
                self.state = self.State.Suspended
                clock = clock or clk.TempoClock.default
                self._event, quant = self._synch_with_quant(self._event, quant)
                clock.play(self, quant)
                sac.CmdPeriod.add(self.__on_cmd_period)
        # Pattern.play return the stream, maybe for API usage constency
        # Stream.play should return self, but I'm not sure.
        # return self

    @staticmethod
    def _synch_with_quant(event, quant):  # Was Event.synchWithQuant.
        quant = clk.Quant.as_quant(quant)  # Also needs a copy or quant is disposable?
        if quant.timing_offset is None:
            quant.timing_offset = event('timing_offset')
        else:
            event = event.copy()
            event['timing_offset'] = quant.timing_offset
        return event, quant


    ### System Actions ###

    def __on_cmd_period(self):  # Instead of removed_from_scheduler.
        self._on_stop_cleanup()


### Pattern Streams ###


class PatternValueStream(stm.Stream):
    def __init__(self, pattern):
        self.pattern = pattern
        self._stream = None


    ### Stream protocol ###

    def next(self, inval=None):
        try:
            if self._stream is None:
                self._stream = self.pattern.__embed__(inval)
                return next(self._stream)
            else:
                return self._stream.send(inval)
        except StopIteration:
            raise stm.StopStream from None

    def reset(self):
        self._stream = None


class PatternEventStream(PatternValueStream):
    ### Stream protocol ###

    def next(self, inevent=None):
        try:
            inevent = evt.event() if inevent is None else inevent
            if self._stream is None:
                self._stream = self.pattern.__embed__(inevent)
                return next(self._stream)
            else:
                return self._stream.send(inevent)
        except StopIteration:
            raise stm.StopStream from None
