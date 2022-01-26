
from abc import ABC, abstractmethod
import logging
import threading

import mido

from . import main as _libsc3


__all__ = ['MidiRtInterface', 'MidiNrtInterface']


_logger = logging.getLogger(__name__)


class MidiInterface(ABC):
    @abstractmethod
    def add_recv_func(self, func):
        pass

    @abstractmethod
    def remove_recv_func(self, func):
        pass

    @abstractmethod
    def send_msg(self, port, msg, **kwargs):
        pass


class MidiRtInterface(MidiInterface):
    def __init__(self):
        self._running = False
        self._recv_functions = set()
        self._input_ports = dict()
        self._output_ports = dict()
        self._threads = dict()

    def add_recv_func(self, func):
        self._recv_functions.add(func)

    def remove_recv_func(self, func):
        self._recv_functions.discard(func)

    def start(self):
        if self._running:
            return
        self._running = True
        _libsc3.main._atexitq.add(_libsc3.main._atexitprio.MIDI, self.stop)

    def stop(self):
        if not self._running:
            return
        self._running = False
        for name, port in self._input_ports.copy().items():
            self.close_input_port(name, port)
        for name, port in self._output_ports.copy().items():
            self.close_output_port(name, port)
        _libsc3.main._atexitq.remove(self.stop)

    def open_input_port(self, name, virtual):
        if not self._running:
            return
        if name in self._input_ports:
            return self._input_ports[name]
        port = mido.open_input(name, virtual)
        self._input_ports[name] = port
        thread = threading.Thread(
            target=self._run,
            name='MIDI ' + str(port),
            args=(self, port))
        thread.daemon = True
        thread.start()
        self._threads[name] = thread
        return port

    def open_output_port(self, name, virtual):
        if name in self._output_ports:
            return self._output_ports[name]
        port = mido.open_output(name, virtual)
        self._output_ports[name] = port
        return port

    def close_input_port(self, name, port):
        port.close()
        if type(port) is mido.backends.rtmidi.Input:
            port._queue.put(None)  # HACK: Is not raising IOError on Linux.
        del self._input_ports[name]

    def close_output_port(self, name, port):
        port.close()
        del self._output_ports[name]

    @staticmethod
    def _run(iface, port):
        while iface._running and not port.closed:
            try:
                msg = port.receive()
                if msg is None:
                    return  # HACK: See close_port.
                # elapsed_time = _libsc3.main.elapsed_time()

                # def sched_func():
                #     # To solve this loop OscFunc has to be rewritten.
                #     for func in type(self)._recv_functions:
                #         func(list(msg), time, addr, self.port)

                # clk.SystemClock.sched(0, sched_func)  # Updates logical time.
            except IOError as e:
                if port.closed:
                    return
                else:
                    raise e

    def send_msg(self, port, msg, **kwargs):  # override
        if port.closed:  # Prevents segfault.
            return
        port.send(mido.Message(msg, **kwargs))

    def sources(self):
        return mido.get_input_names()

    def destinations(self):
        return mido.get_output_names()


class MidiNrtInterface(MidiInterface):
    ...

    def init(self):
        self._midi_score = MidiScore()

    def finish(self):  # close?
        self._midi_score.finish()

    def add_recv_func(cls, func):  # override
        ...

    def remove_recv_func(cls, func):  # override
        ...

    def send_msg(self, port, msg, **kwargs):  # override
        ...


class MidiScore():
    ...
