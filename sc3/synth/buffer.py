"""Buffer.sc"""

import pathlib
import time

from ..base import responsedefs as rdf
from ..base import model as mdl
from ..base import functions as fn
from ..base import main as _libsc3
from . import _graphparam as gpp
from . import server as srv


class Buffer(gpp.UGenParameter, gpp.NodeParameter):
    _server_caches = dict()

    def __init__(self, server=None, num_frames=None,
                 num_channels=None, bufnum=None):
        super(gpp.UGenParameter, self).__init__(self)
        # // Doesn't send.
        self._server = server or srv.Server.default
        if bufnum is None:
            self._bufnum = self._server.next_buffer_number(1)
        else:
            self._bufnum = bufnum
        self._num_frames = num_frames
        self._num_channels = num_channels
        self._sample_rate = self._server.sample_rate
        self._path = None
        self._start_frame = None
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

    @classmethod
    def new_alloc(cls, server=None, num_frames=None, num_channels=1,
                  completion_msg=None, bufnum=None):
        obj = cls(server, num_frames, num_channels, bufnum)
        obj.alloc(completion_msg)
        # obj._cache() # BUG: sclang dos veces porque alloc_msg llama this.cache. Además, cache() solo registra el servidor en el diccionario y el responder para '/b_info' que no se usa en los constructores. Acá se llama solamente en __init__.
        return obj

    @classmethod
    def new_alloc_consecutive(cls, num_bufs=1, server=None, num_frames=None,
                              num_channels=1, completion_msg=None, bufnum=None):
        if bufnum is None:
            buf_base = server.next_buffer_number(num_bufs)
        else:
            buf_base = bufnum
        buf_list = []
        for i in range(num_bufs):
            new_buf = cls(server, num_frames, num_channels, buf_base + i)
            server.send_msg('/b_alloc', buf_base + i, num_frames,
                            num_channels, fn.value(completion_msg, new_buf, i))
            # new_buf._cache() # NOTE: __init__ llama a _cache
            buf_list.append(new_buf)
        return buf_list

    @classmethod
    def new_read(cls, server, path, start_frame=0, num_frames=-1,
                 action=None, bufnum=None):
        # // read whole file into memory for PlayBuf etc.
        # // Adds a query as a completion message.
        obj = cls(server, None, None, bufnum)
        obj._do_on_info = action
        # obj._cache() # NOTE: __init__ llama a _cache
        obj.alloc_read(path, start_frame, num_frames,
                       lambda buf: ['/b_query', buf.bufnum])
        return obj

    @classmethod
    def new_read_no_update(cls, server, path, start_frame=0, num_frames=-1,
                           bufnum=None, completion_msg=None):
        obj = cls(server, None, None, bufnum)
        # BUG: este constructor no llama a cache() en sclang, será el no update
        # BUG: REVISAR DE NUEVO QUÉ ACTUALIZA CACHE, NO VEO LA DIFERENCIA,
        # BUG: SIEMPRE SE LLAMA SALVO ACÁ Y SE LLAMABA DOS VECES. AGREGAR FLAG A __init__.
        obj.alloc_read(path, start_frame, num_frames, completion_msg)
        return obj

    @classmethod
    def new_read_channel(cls, server, path, start_frame=0, num_frames=-1,
                         channels=None, action=None, bufnum=None):
        obj = cls(server, None, None, bufnum)
        obj._do_on_info = action
        # obj._cache() # NOTE: __init__ llama a _cache
        obj.alloc_read_channel(path, start_frame, num_frames, channels,
                               lambda buf: ['/b_query', buf.bufnum])
        return obj

    # // preload a buffer for use with DiskIn
    @classmethod
    def new_cue(cls, server, path, start_frame=0, num_channels=2,
                buffer_size=32768, completion_msg=None):
        obj = cls.new_alloc(server, buffer_size, num_channels,
                            lambda buf: buf.read_msg(path, start_frame,
                                                     buffer_size, 0, True,
                                                     completion_msg))
        # self._cache() # NOTE: __init__ llama a _cache a través de alloc.
        return obj

    def alloc(self, completion_msg=None): # NOTE: es alloc de instancia
        self._server.send_msg(*self.alloc_msg(completion_msg))

    def alloc_msg(self, completion_msg=None):
        # self._cache() # NOTE: __init__ llama a _cache
        return ['/b_alloc', self._bufnum, self._num_frames,
                self._num_channels, fn.value(completion_msg, self)]  # NOTE: no veo por qué solo startFrame.asInteger en sclang.

    def alloc_read(self, path, start_frame=0, num_frames=-1,
                   completion_msg=None):
        self._path = path
        self._start_frame = start_frame
        self._server.send_msg(*self.alloc_read_msg(
            path, start_frame, num_frames, completion_msg)) # NOTE: no veo por qué solo startFrame.asInteger en sclang.

    def alloc_read_msg(self, path, start_frame=0, num_frames=-1,
                       completion_msg=None):
        # self._cache() # NOTE: __init__ llama a _cache
        self._path = path
        self._start_frame = start_frame
        return ['/b_allocRead', self._bufnum, path,
                start_frame, num_frames, fn.value(completion_msg, self)]  # NOTE: no veo por qué solo startFrame.asInteger y comprueba num_frames en sclang si no lo hace con el resto.

    def alloc_read_channel(self, path, start_frame=0, num_frames=-1,
                           channels=None, completion_msg=None):
        self._path = path
        self._start_frame = start_frame
        self._server.send_msg(*self.alloc_read_channel_msg(
            path, start_frame, num_frames, channels, completion_msg)) # NOTE: no veo por qué solo startFrame.asInteger en sclang.

    def alloc_read_channel_msg(self, path, start_frame=0, num_frames=-1,
                               channels=None, completion_msg=None):
        # self._cache() # NOTE: __init__ llama a _cache
        self._path = path
        self._start_frame = start_frame
        return ['/b_allocReadChannel', self._bufnum, path, start_frame,
                num_frames, *channels, fn.value(completion_msg, self)] # NOTE: no veo por qué solo startFrame.asInteger y comprueba num_frames en sclang si no lo hace con el resto.

    def read(self, path, file_start_frame=0, num_frames=-1,
             buf_start_frame=0, leave_open=False, action=None):
        # self._cache() # NOTE: __init__ llama a _cache
        self._do_on_info = action
        self._server.send_msg(*self.read_msg(
            path, file_start_frame, num_frames, buf_start_frame,
            leave_open, lambda buf: ['/b_query', buf.bufnum]))

    def read_no_update(self, path, file_start_frame=0, num_frames=-1,
                       buf_start_frame=0, leave_open=False,
                       completion_msg=None):
        self._server.send_msg(*self.read_msg(path, file_start_frame, num_frames,
                                             buf_start_frame, leave_open,
                                             completion_msg))

    def read_msg(self, path, file_start_frame=0, num_frames=-1,
                 buf_start_frame=0, leave_open=False, completion_msg=None):
        self._path = path
        return ['/b_read', self._bufnum, path, file_start_frame, num_frames,
                buf_start_frame, leave_open, fn.value(completion_msg, self)]  # NOTE: no veo por qué solo startFrame.asInteger y comprueba num_frames en sclang si no lo hace con el resto.

    def read_channel(self, path, file_start_frame=0, num_frames=-1,
                     buf_start_frame=0, leave_open=False,
                     channels=None, action=None):
        # self._cache() # NOTE: __init__ llama a _cache
        self._do_on_info = action
        self._server.send_msg(*self.read_channel_msg(
            path, file_start_frame, num_frames, buf_start_frame,
            leave_open, channels, lambda buf: ['/b_query', buf.bufnum]))

    def read_channel_msg(self, path, file_start_frame=0, num_frames=-1,
                         buf_start_frame=0, leave_open=False, channels=None,
                         completion_msg=None):
        # // doesn't set my numChannels etc.
        self._path = path
        return ['/b_readChannel', self._bufnum, path, file_start_frame,
                num_frames, buf_start_frame, leave_open, *channels,
                fn.value(completion_msg, self)]  # NOTE: no veo por qué solo startFrame.asInteger y comprueba num_frames en sclang si no lo hace con el resto.

    def cue(self, path, start_frame=0, completion_msg=None):  # Was cue_soundfile
        # // Preload a buffer for use with DiskIn.
        self._path = path
        self._server.send_msg(*self.cue_msg(path, start_frame, completion_msg))
        # NOTE: no llama a cache()

    def cue_msg(self, path, start_frame=0, completion_msg=None):  # Was cue_soundfile_msg
        return ['/b_read', self._bufnum, path, start_frame, 0, 1,  # NOTE: no veo por qué solo startFrame.asInteger y comprueba num_frames en sclang si no lo hace con el resto.
                self._num_frames, fn.value(completion_msg, self)]  # *** BUG: pone 1 en vez de True, porque es el mensaje, pero no lo hace siempre.

    @classmethod
    def new_load(cls, server, collection, num_channels=1, action=None):  # Was new_load_collection
        ...  # Move classmethod method up.

    def load(self, collection, start_frame=0, action=None):  # Was load_collection
        ...

    @classmethod
    def new_send(cls, server, collection, num_channels=1, wait=-1, action=None):  # Was send_collection
        # // Send a Collection to a buffer one UDP sized packet at a time.
        ... # Move class method up.

    def send(self, collection, start_frame=0, wait=-1, action=None):  # Was send_collection
        ...

    def _stream_data(self, collstream, collsize, start_frame=0, wait=-1, action=None):  # Was streamCollection
        # // Called internally.
        ...


    # TODO:
    # // these next two get the data and put it in a float array which is passed to action
    # loadToFloatArray
    # // risky without wait
    # getToFloatArray


    def write(self, path=None, header_format="aiff", sample_format="int24",
              num_frames=-1, start_frame=0, leave_open=False,
              completion_msg=None):
        if self._bufnum is None:
            raise Exception(
                'cannot call write on a Buffer that has been freed')

        if path is None:
            dir = _libsc3.main.platform.recording_dir
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            path = dir / ('SC_' + timestamp + '.' + header_format)
        else:
            path = pathlib.Path(path)
            if not path.suffix:
                path = pathlib.Path(str(path) + '.' + header_format)

        self._server.send_msg(*self.write_msg(
            str(path), header_format, sample_format, num_frames,
            start_frame, leave_open, completion_msg))

    def write_msg(self, path, header_format="aiff", sample_format="int24",
                  num_frames=-1, start_frame=0, leave_open=False,
                  completion_msg=None):
        if self._bufnum is None:
            raise Exception(
                'cannot call write_msg on a Buffer that has been freed')
        # // Doesn't change my path.
        return ['/b_write', self._bufnum, path, header_format, sample_format,
                int(num_frames), int(start_frame), int(leave_open),
                fn.value(completion_msg, self)]

    def free(self, completion_msg=None):
        if self._bufnum is None:
            _logger.warning(
                'cannot call free on a Buffer that has been freed')
        self._server.send_msg(*self.free_msg(completion_msg))

    def free_msg(self, completion_msg=None):
        if self._bufnum is None:
            _logger.warning(
                'cannot call free_msg on a Buffer that has been freed')
        self._uncache()
        self._server.buffer_allocator.free(self._bufnum)
        msg = ['/b_free', self._bufnum, fn.value(completion_msg, self)]
        self._bufnum = self._num_frames = self._num_channels = None
        self._sample_rate = self._path = self._start_frame = None
        return msg

    @classmethod
    def free_all(cls, server=None):  # Move up?
        server = server if server is not None else srv.Server.default
        server.free_all_buffers()
        type(self)._clear_server_caches(server) # *** BUG: no hace _clear_server_caches de default si es nil en sclang.

    def zero(self, completion_msg=None):
        ...

    def zero_msg(self, completion_msg=None):
        ...

    def set(self, index, value, *more_pairs):
        ...

    def set_msg(self, index, value, *more_pairs):
        ...

    def setn(self, *args):
        ...

    def setn_msg_args(self, *args):
        ...

    def setn_msg(self, *args):
        ...

    def get(self, index, action=None):
        ...

    def get_msg(self, index, action=None):
        ...

    def getn(self, index, count, action=None):
        ...

    def getn_msg(self, index, count, action=None):
        ...

    def fill(self, start, num_frames, value, *more_values):
        ...

    def fill_msg(self, start, num_frames, value, *more_values):
        ...

    def normalize(self, new_max=1, as_wavetable=False):
        ...

    def normalize_msg(self, new_max=1, as_wavetable=False):
        ...


    # TODO:
    # gen
    # gen_msg
    # sine1
    # sine2
    # sine3
    # cheby
    # sine1_msg
    # sine2_msg
    # sine3_msg
    # cheby_msg
    # copy_data  # NOTE: ver el cambio de nombre de streamCollection.
    # copy_msg
    # clase
    # close_msg
    # query
    # query_msg
    # update_info


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
    # *loadDialog # No builtin gui.

    def play(self, loop=False, mul=1):
        print('*** implementar Buffer.play tal vez mejor como función play(buffer) que retorna el objeto player y que cada clase implemente __play__') # TODO

    # duration, pasada arriba como propiedead de solo lectura.


    ### UGen graph parameter interface ###

    def _as_ugen_input(self, *_):
        return self.bufnum

    def _as_audio_rate_input(self):
        raise TypeError("Buffer can't be used as audio rate input")


    ### Node parameter interface ###

    def _as_control_input(self):
        return self.bufnum


    # asBufWithValues # NOTE: se implementa acá, en Ref y en SimpleNumber pero no se usa en la librería estandar.
