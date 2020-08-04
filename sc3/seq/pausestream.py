"""Stream.sc part 2"""

import logging

from ..base import stream as stm
from ..base import model as mdl
from ..base import systemactions as sac
from ..base import clock as clk
from . import event as evt


__all__ = ['Task', 'task']


_logger = logging.getLogger(__name__)


### Higher level abstractions ###


# class OneShotStream(Stream): ... # TODO: ver para qué sirve, la única referencia está en Object:iter, no está documentada.
# class EmbedOnce(Stream): ... # TODO, ver, solo se usa en JITLib, no está documentada.
# class StreamClutch(Stream): ... # TODO: no se usa en la librería de clases, actúa como un filtro, sí está documentada.
# class CleanupStream(Stream): ... # TODO: no se usa en la librería de clases, creo, ver bien, no tiene documentación.


class PauseStream(stm.Stream):
    # // PauseStream is a stream wrapper that can be started and stopped.
    def __init__(self, stream):
        self._stream = stream
        self._clock = None
        self._next_beat = None
        self._is_waiting = False
        self._is_playing = False
        self._era = 0

    @property
    def is_playing(self):
        return self._is_playing

    def play(self, clock=None, reset=False, quant=None):
        if self._is_playing:
            return
            # Pattern.play return the stream, maybe for API usage constency
            # Stream.play should return self, but I'm not sure.
            # return self
        if reset:
            self.reset()
        self._stream.thread_player = self
        self._clock = clock or self._clock or clk.SystemClock
        self._stream._clock = self._clock  # BUG: threading.
        self._is_waiting = True # // make sure that accidental play/stop/play sequences don't cause memory leaks
        self._is_playing = True
        self._era = sac.CmdPeriod.era

        def pause_stream_play():
            if self._is_waiting and self._next_beat is None:
                self._clock.sched(0, self)
                self._is_waiting = False
                mdl.NotificationCenter.notify(self, 'playing')

        self._clock.play(pause_stream_play, quant)
        mdl.NotificationCenter.notify(self, 'user_played')
        # Pattern.play return the stream, maybe for API usage constency
        # Stream.play should return self, but I'm not sure.
        # return self

    def reset(self):
        self._stream.reset()

    def stop(self):
        self._stop()
        with self._stream._state_cond:
            if self._stream.state == self._stream.State.Running:
                raise stm.StopStream
            else:
                self._stream.stop()
        mdl.NotificationCenter.notify(self, 'user_stopped')

    def _stop(self):
        self._is_playing = False
        self._is_waiting = False

    def removed_from_scheduler(self):
        self._next_beat = None
        self._stop()
        mdl.NotificationCenter.notify(self, 'stopped')

    def pause(self):
        self._stop()
        mdl.NotificationCenter.notify(self, 'user_paused')

    def resume(self, clock=None, quant=None):
        self.play(clock, False, quant)

    def next(self, inval=None):
        try:
            if not self._is_playing:
                raise stm.StopStream
            next_time = self._stream.next(inval)  # raises StopStream
            self._next_beat = inval + next_time  # // inval is current logical beat
            return next_time
        except stm.StopStream:
            self.removed_from_scheduler()
            raise

    def __awake__(self, beats, seconds, clock):
        return self.next(beats)

    @property
    def thread_player(self):
        return self

    @thread_player.setter
    def thread_player(self, value):
        pass


class Task(PauseStream):
    # // Task is a PauseStream for wrapping a Routine.
    def __init__(self, func):
        super().__init__(stm.Routine(func))  # BUG: qué pasa si func llega a ser una rutina? qué error tira?

    # storeArgs # TODO: ver en general para la librería


# decorator syntax
def task(func):
    return Task(func)


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


class EventStreamPlayer(PauseStream):
    def __init__(self, stream, event=None):
        super().__init__(stream)
        self.event = event or evt.event()
        self.mute_count = 0
        self.cleanup = EventStreamCleanup()

        def stream_player_generator(in_time):
            while True:
                in_time = yield self._next(in_time)

        self.routine = stm.Routine(stream_player_generator)

    # // freeNodes is passed as false from
    # // TempoClock:cmdPeriod
    def removed_from_scheduler(self, free_nodes=True):
        self._next_beat = None # BUG?
        self.cleanup.terminate(free_nodes)
        self._stop()
        mdl.NotificationCenter.notify(self, 'stopped')

    def _stop(self):
        self._is_playing = False
        self._is_waiting = False
        self._next_beat = None # BUG? lo setea a nil acá y en el método de arriba que llama a este (no debería estar allá), además stop abajo es igual que arriba SALVO que eso haga que se detenga antes por alguna razón.

    def stop(self):
        self.cleanup.terminate()
        self._stop()
        mdl.NotificationCenter.notify(self, 'user_stopped')

    def reset(self):
        self.routine.reset()
        super().reset()

    def mute(self):
        self.mute_count += 1

    def unmute(self):
        self.mute_count -= 1

    def next(self, in_time):
        return self.routine.next(in_time)

    def _next(self, in_time):
        try:
            if not self._is_playing:
                raise stm.StopStream
            outevent = self._stream.next(self.event.copy())  # raises StopStream
            next_time = self._play_and_delta(outevent)
            # if (nextTime.isNil) { this.removedFromScheduler; ^nil };
            # BUG: For event.play_and_delta/event.delta patterns won't return
            # nil and set the key, they will raise StopStream. Equally I either
            # can't find a case of nil sclang, outEvent can't return nil because
            # it checks, playAndDelta don't seem to return nil. Tested with
            # Pbind, \delta, nil goes to if, (delta: nil) is 0. See _Event_Delta.
            self._next_beat = in_time + next_time  # // inval is current logical beat
            return next_time
        except stm.StopStream:
            self.cleanup.clear()
            self.removed_from_scheduler() # BUG? Hay algo raro, llama cleanup.clear() en la línea anterior, que borras las funciones de cleanup, pero luego llama a cleanup.terminate a través removed_from_scheduler en esta línea que evalúa las funciones que borró (no las evalúa)
            raise

    def _play_and_delta(self, outevent):  # Was Event.playAndDelta.
        if self.mute_count > 0:
            outevent['type'] = 'rest'
        self.cleanup.update(outevent)
        outevent.play()
        return outevent('delta')

    # def _as_event_stream_player(self):
    #     return self

    def play(self, clock=None, reset=False, quant=None):
        if self._is_playing:
            return
            # Pattern.play return the stream, maybe for API usage constency
            # Stream.play should return self, but I'm not sure.
            # return self
        if reset:
            self.reset()

        self._clock = clock or self._clock or clk.SystemClock
        self._stream._clock = self._clock
        self._is_waiting = True # // make sure that accidental play/stop/play sequences don't cause memory leaks
        self._is_playing = True
        self._era = sac.CmdPeriod.era

        # synchWithQuant is used here only. See note in Event.sc.
        quant = clk.Quant.as_quant(quant)  # Also needs a copy, or quant is disposable?
        if quant.timing_offset is None:
            quant.timing_offset = self.event('timing_offset')
        else:
            self.event = self.event.copy()
            self.event['timing_offset'] = quant.timing_offset

        def event_stream_play():
            if self._is_waiting and self._next_beat is None:
                self._clock.sched(0, self)
                self._is_waiting = False
                mdl.NotificationCenter.notify(self, 'playing')

        self._clock.play(event_stream_play, quant)
        mdl.NotificationCenter.notify(self, 'user_played')
        # Pattern.play return the stream, maybe for API usage constency
        # Stream.play should return self, but I'm not sure.
        # return self


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
            raise stm.StopStream


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
            raise stm.StopStream
