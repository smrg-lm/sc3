"""Buffer.sc"""

from . import graphparam as gpp
from . import server as srv
from . import responsedefs as rdf
from . import model as mdl


class Buffer(gpp.UGenParameter):
    _server_caches = dict()

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
        self._do_on_info = lambda buf: None
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

    @property
    def duration(self):
        if self._num_frames is None or self._sample_rate is None:
            raise ValueError('duration parameters (frames/sr) not initialized')
        return self._num_frames / self._sample_rate

    # TODO: sigue

    def _cache(self):
        # // cache Buffers for easy info updating
        type(self)._init_server_cache(self._server)
        type(self)._server_caches[self._server][self._bufnum] = self

    def _uncache(self):
        try:
            del type(self)._server_caches[self._server][self._bufnum]
            if len(type(self)._server_caches[self._server]) == 1:
                # // The 1 item would be the responder, if there is more than 1
                # // item then the rest are cached buffers, else we can remove.
                # // cx: Tho I don't see why its important. It will just have
                # // to be added back when the next buffer is added and the
                # // responder is removed when the server reboots.
                type(self)._clear_server_caches(self._server)
        except KeyError:
            pass

    @classmethod
    def _init_server_cache(cls, server):
        if server not in cls._server_caches:
            cls._server_caches[server] = dict()

            def resp_func(msg, *_):
                try:
                    buffer = cls._server_caches[server][msg[1]]
                    buffer._num_frames = msg[2]
                    buffer._num_channels = msg[3]
                    buffer._sample_rate = msg[4]
                    buffer._query_done()
                except KeyError:
                    pass

            resp = rdf.OSCFunc(resp_func, '/b_info', server.addr)
            resp.permanent = True
            cls._server_caches[server]['responder'] = resp
            mdl.NotificationCenter.register(
                server, 'new_allocators',
                cls, lambda: cls._clear_server_caches(server)
            )

    @classmethod
    def _clear_server_caches(cls, server):
        try:
            cls._server_caches[server]['responder'].free()
            del cls._server_caches[server]
        except KeyError:
            pass

    @classmethod
    def cached_buffers_do(cls, server, func):
        if server in cls._server_caches: # NOTE: No uso try porque llama a una función arbitraria.
            for i, (bufnum, buf)\
            in enumerate(cls._server_caches[server].items()):
                if type(bufnum) is not str: # NOTE: esta comprobación hay que hacerla porque el responder está junto con los buffers, y la hago por string por si bufnum es de otro tipo numérico, para que no falle en silencio.
                    func(buf, i)

    @classmethod
    def cached_buffer_at(cls, server, bufnum):
        try:
            return cls._server_caches[server][bufnum]
        except KeyError:
            return None

    def _query_done(self):
        # // called from Server when b_info is received
        self._do_on_info(self)
        self._do_on_info = lambda buf: None

    # printOn
    # *loadDialog # TODO: ver qué se hace con los métodos gui en general.

    def play(self, loop=False, mul=1):
        print('*** implementar Buffer.play tal vez mejor como función play(buffer) que retorna el objeto player y que cada clase implemente __play__') # TODO

    # duration, pasada arriba como propiedead de solo lectura.

    # UGen graph parameter interface #
    # TODO: ver el resto en UGenParameter

    def as_ugen_input(self, *_):
        return self.bufnum

    def as_control_input(self):
        return self.bufnum

    # asBufWithValues # NOTE: se implementa acá, en Ref y en SimpleNumber pero no se usa en la librería estandar.
