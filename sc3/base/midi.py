
from . import main as _libsc3


class MidiIO():
    def __init__(self, name, virtual=False):
        self._name = name
        self._virtual = virtual
        self._port = None

    @property
    def name(self):
        return self._name

    # @property
    # def port(self):
    #     return self._port

    @property
    def closed(self):
        return self._port.closed

    def close(self):
        pass


class MidiIn(MidiIO):
    def __init__(self, name, virtual=False):
        super().__init__(name, virtual)
        self._port = _libsc3.main._midi_interface.open_input_port(
            self._name, self._virtual)

    def close(self):
        _libsc3.main._midi_interface.close_input_port(self._name, self._port)

    @classmethod
    def sources(self):
        return _libsc3.main._midi_interface.sources()


class MidiOut(MidiIO):
    def __init__(self, name, virtual=False):
        super().__init__(name, virtual)
        self._port = _libsc3.main._midi_interface.open_output_port(
            self._name, self._virtual)

    def close(self):
        _libsc3.main._midi_interface.close_output_port(self._name, self._port)

    def send_msg(self, msg, **kwargs):
        _libsc3.main._midi_interface.send_msg(self._port, msg, **kwargs)

    def reset(self):
        self._port.reset()

    def panic(self):
        self._port.panic()

    @classmethod
    def destinations(self):
        return _libsc3.main._midi_interface.destinations()
