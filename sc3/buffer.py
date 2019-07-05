"""Buffer.sc"""

from . import graphparam as gpp
from . import server as srv


class Buffer(gpp.UGenParameter):
    server_caches = dict()

    # NOTE: new se usa para creación sin alocación de memoria.
    def __init__(self, server=None, num_frames=None,
                 num_channels=None, bufnum=None):
        # NOTE: ver la inicialización repetida, tiene muchos constructores, ver cuales difieren.
        self._server = server or srv.Server.default
        self._bufnum = bufnum or self._server.next_buffer_number(1)
        self._num_frames = num_frames
        self._num_channels = num_channels
        self._sample_rate = self._server.sample_rate
        self._path = None
        self._start_frame = None # BUG: ver por qué usa el setter explícitamente, puede que estas variables se asignene a bajo nivel, tienen nota.
        self._do_on_info = lambda: None
        self._cache()

    @property
    def server(self):
        return self._server

    @property
    def bufnum(self):
        return self._bufnum

    @property
    def num_frames(self):
        return self._num_frames

    @property
    def num_channels(self):
        return self._num_channels

    @property
    def start_frame(self):
        return self._start_frame

    @property
    def sample_rate(self):
        return self._sample_rate

    @property
    def path(self):
        return self._path

    # TODO: sigue

    def _cache(self):
        # // cache Buffers for easy info updating
        pass # TODO

    # TODO: sigue

    # UGen graph parameter interface #
    # TODO: ver el resto en UGenParameter

    def as_ugen_input(self, *_):
        return self.bufnum

    def as_control_input(self):
        return self.bufnum
