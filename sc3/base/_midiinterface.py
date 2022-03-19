
from abc import ABC, abstractmethod
import threading
import pprint

from . import main as _libsc3
from . import midi as mdi
from . import clock as clk
from . import _taskq as tsq
from . import _hooks as hks


mido = hks.import_optional_module('mido')


__all__ = ['MidiRtInterface', 'MidiNrtInterface']


class MidiInterface(ABC):
    @abstractmethod
    def add_recv_func(self, func):
        pass

    @abstractmethod
    def remove_recv_func(self, func):
        pass

    @abstractmethod
    def open_input_port(self, name, virtual):
        pass

    @abstractmethod
    def open_output_port(self, name, virtual):
        pass

    @abstractmethod
    def close_input_port(self, name, port):
        pass

    @abstractmethod
    def close_output_port(self, name, port):
        pass

    @abstractmethod
    def send_msg(self, port, msg, **kwargs):
        pass

    def sources(self):
        return None

    def destinations(self):
        return None


class MidiRtInterface(MidiInterface):
    def __init__(self):
        self._running = False
        self._recv_functions = set()
        self._input_ports = dict()
        self._output_ports = dict()
        self._threads = dict()

    def add_recv_func(self, func):  # override
        self._recv_functions.add(func)

    def remove_recv_func(self, func):  # override
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

    def open_input_port(self, name, virtual):  # override
        if not self._running:
            return
        if name in self._input_ports:
            return self._input_ports[name]
        port = mido.open_input(name, virtual)
        self._input_ports[name] = port
        thread = threading.Thread(
            target=self._run,
            name='MIDI ' + str(port),
            args=(self, name, virtual, port))
        thread.daemon = True
        thread.start()
        self._threads[name] = thread
        return port

    def open_output_port(self, name, virtual):  # override
        if name in self._output_ports:
            return self._output_ports[name]
        port = mido.open_output(name, virtual)
        self._output_ports[name] = port
        return port

    def close_input_port(self, name, port):  # override
        port.close()
        if type(port) is mido.backends.rtmidi.Input:
            port._queue.put(None)  # HACK: Is not raising IOError on Linux.
        del self._input_ports[name]

    def close_output_port(self, name, port):  # override
        port.close()
        del self._output_ports[name]

    @staticmethod
    def _run(iface, name, virtual, port):
        midi_in = mdi.MidiIn(name, virtual)  # MidiFunc port argument object.
        while iface._running and not port.closed:
            try:
                msg = port.receive()
                if msg is None:
                    return  # HACK: See close_port.
                data = msg.dict()
                # *** TODO: is_cc, is_meta, is_realtime to keys?
                # *** TODO: data['time'] = _libsc3.main.elapsed_time()  # Or pop('time')
                iface._msg_dispatch(data, midi_in)
            except IOError as e:
                if port.closed:
                    return
                else:
                    raise e

    def _msg_dispatch(self, data, midi_in):
        def sched_func():
            for func in self._recv_functions.copy():
                func(data, midi_in)

        clk.SystemClock.sched(0, sched_func)

    def send_msg(self, port, msg, **kwargs):  # override
        if port.closed:  # Prevents segfault.
            return
        port.send(mido.Message(msg, **kwargs))

    def sources(self):  # override
        return mido.get_input_names()

    def destinations(self):  # override
        return mido.get_output_names()


class MidiNrtInterface(MidiInterface):
    class _DummyPort():
        def __init__(self, name, virtual=False):
            self.name = name
            self.closed = False
            self._virtual = virtual
        def reset(self):
            pass
        def panic(self):
            pass

    def __init__(self):
        self._output_ports = dict()

    def init(self):
        self._midi_score = MidiScore()

    def finish(self):
        self._midi_score.finish()

    def add_recv_func(cls, func):  # override
        pass

    def remove_recv_func(cls, func):  # override
        pass

    def open_input_port(self, name, virtual):  # override
        raise Exception('input ports cannot be open in nrt mode')

    def open_output_port(self, name, virtual):  # override
        if name in self._output_ports:
            return self._output_ports[name]
        port = type(self)._DummyPort(name, virtual)
        self._output_ports[name] = port
        return port

    def close_input_port(self, name, port):  # override
        pass

    def close_output_port(self, name, port):  # override
        port.closed = True
        del self._output_ports[name]

    def send_msg(self, port, msg, **kwargs):  # override
        self._midi_score.add(port, msg, **kwargs)


class MidiScore():
    class _Entry():
        def __init__(self, port, msg):
            self.port = port
            self.msg = msg
            # *** NOTE: May need to define __eq__ and __hash__ for TaskQueue.

    def __init__(self):
        self._scoreq = tsq.TaskQueue()
        self._tracks = []
        self._midi_file = None
        self._finished = False

    @property
    def list(self):
        return self._tracks[:]

    @property
    def midi_file(self):
        return self._midi_file

    @property
    def duration(self):
        return self._scoreq.peek(False)[0]

    def add(self, port, msg, **kwargs):
        if self._finished:
            raise Exception('already finished MIDI score')
        try:
            midi_msg = mido.Message(msg, **kwargs)
        except LookupError:
            midi_msg = mido.MetaMessage(msg, **kwargs)
        send_time = _libsc3.main.current_tt._seconds
        self._scoreq.add(send_time, type(self)._Entry(port, midi_msg))

    def finish(self):
        midi_tempo = int(mido.tempo2bpm(60))
        midi_ppqn = 960
        prev_time = dict()
        devices = dict()
        for send_time, entry in self._scoreq:
            name, msg = entry.port.name, entry.msg
            if not name in devices:
                prev_time[name] = 0
                devices[name] = mido.MidiTrack()
                devices[name].extend([
                    mido.MetaMessage('device_name', name=name),
                    mido.MetaMessage('set_tempo', tempo=midi_tempo)])
            msg.time = int(mido.second2tick(
                send_time - prev_time[name], midi_ppqn, midi_tempo))
            devices[name].append(msg)
            prev_time[name] = send_time
        self._tracks = list(devices.values())
        self._midi_file = mido.MidiFile(
            type=1,
            ticks_per_beat=midi_ppqn,
            tracks=self._tracks)
        self._finished = True

    def write(self, path):
        if not self._finished:
            self.finish()
        self._midi_file.save(path)

    # def render(self, path=None, input_file=None, rules=None):
    #     ...

    def __str__(self):
        return pprint.pformat(self._tracks)
