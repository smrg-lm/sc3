"""Buffer.sc"""

import logging
import pathlib
import time
import array
import uuid

from ..base import responsedefs as rdf
from ..base import model as mdl
from ..base import functions as fn
from ..base import platform as plf
from ..base import builtins as bi
from ..base import utils as utl
from ..base import stream as stm
from ..base import clock as clk
from . import _graphparam as gpp
from . import server as srv


__all__ = ['Buffer']


_logger = logging.getLogger(__name__)


class BufferException(Exception):
    pass


class BufferAlreadyFreed(BufferException):
    def __init__(self, method=None):
        if method is not None:
            self.args = (f"'{method}' called",)


class Buffer(gpp.UGenParameter, gpp.NodeParameter):
    _server_caches = dict()

    def __init__(self, frames=1024, channels=1, server=None, bufnum=None,
                 *, alloc=True, completion_msg=None):
        super(gpp.UGenParameter, self).__init__(self)
        # // Doesn't send.
        self._server = server or srv.Server.default
        if bufnum is None:
            self._bufnum = self._server.next_buffer_number(1)
        else:
            self._bufnum = bufnum
        self._frames = frames
        self._channels = channels
        self._sample_rate = self._server._status_watcher.sample_rate
        self._path = None
        self._start_frame = None
        self._do_on_info = None
        self._cache()
        if alloc:
            self.alloc(completion_msg)

    @property
    def frames(self):
        return self._frames

    @property
    def channels(self):
        return self._channels

    @property
    def server(self):
        return self._server

    @property
    def bufnum(self):
        return self._bufnum

    @property
    def path(self):
        return self._path

    @property
    def start_frame(self):
        return self._start_frame

    @property
    def sample_rate(self):
        return self._sample_rate

    @property
    def duration(self):
        if self._frames is None or self._sample_rate is None:
            raise ValueError('duration parameters (frames/sr) not initialized')
        return self._frames / self._sample_rate


    ### Specialized Constructors ###

    @classmethod
    def new_consecutive(cls, num_bufs=1, frames=1024, channels=1,
                        server=None, bufnum=None, completion_msg=None):
        if bufnum is None:
            buf_base = server.next_buffer_number(num_bufs)
        else:
            buf_base = bufnum
        buf_list = []
        for i in range(num_bufs):
            new_buf = cls(frames, channels, server, buf_base + i, alloc=False)
            server.send_msg(
                '/b_alloc', buf_base + i, frames,
                channels, fn.value(completion_msg, new_buf, i))
            # new_buf._cache() # NOTE: __init__ llama a _cache
            buf_list.append(new_buf)
        return buf_list

    @classmethod
    def new_read(cls, path, start_frame=0, frames=-1, server=None,
                 bufnum=None, action=None):
        # // read whole file into memory for PlayBuf etc.
        # // Adds a query as a completion message.
        obj = cls(None, None, server, bufnum, alloc=False)
        obj._do_on_info = action
        # obj._cache() # NOTE: __init__ llama a _cache
        obj.alloc_read(
            path, start_frame, frames, lambda buf: ['/b_query', buf.bufnum])
        return obj

    @classmethod
    def new_read_no_update(cls, path, start_frame=0, frames=-1, server=None,
                           bufnum=None, completion_msg=None):
        obj = cls(None, None, server, bufnum, alloc=False)
        obj.alloc_read(path, start_frame, frames, completion_msg)
        return obj

    @classmethod
    def new_read_channel(cls, path, start_frame=0, frames=-1, channels=None,
                         server=None, bufnum=None, action=None):
        obj = cls(server, None, None, bufnum, alloc=False)
        obj._do_on_info = action
        obj.alloc_read_channel(
            path, start_frame, frames, channels,
            lambda buf: ['/b_query', buf.bufnum])
        return obj

    @classmethod
    def new_cue(cls, path, start_frame=0, channels=1, buffer_size=32768,
                server=None, bufnum=None, completion_msg=None):
        # // Preload a buffer for use with DiskIn
        obj = cls.new_alloc(
            buffer_size, channels, server, bufnum,
            lambda buf: buf.read_msg(
                path, start_frame, buffer_size, 0, True, completion_msg))
        return obj

    @classmethod
    def new_load_list(cls, channel_lst, server=None, action=None):  # Was new_load_collection
        # Difference: this version receives a list of channel data (lists).
        # // Transfer a collection of numbers to a buffer through a file.
        server = server or srv.Server.default
        if server.is_local:
            channel_lst = [list(array.array('f', l)) for l in channel_lst]  # Type check & cast.
            path = str(
                plf.Platform.tmp_dir / ('SC_' + uuid.uuid4().hex + '.wav'))
            sample_rate = int(server._status_watcher.sample_rate)
            try:
                # Was using SoundFile in sclang.
                _write_wave_file(path, channel_lst, sample_rate)
            except Exception as e:
                raise BufferException('failed to write data') from e

            def remove_file(buf):
                try:
                    pathlib.Path(path).unlink()
                    buf._path = None
                except:
                    _logger.warning(f'could not delete data file: {path}')
                finally:
                    fn.value(action, buf)

            return cls.new_read(server, path, action=remove_file)
        else:
            _logger.warning("cannot call 'new_load' with a non-local Server")

    @classmethod
    def new_send_list(cls, lst, channels=1, server=None, wait=-1, action=None):  # Was send_collection
        # // Send a Collection to a buffer one UDP sized packet at a time.
        lst = list(array.array('f', lst))  # Type check & cast.
        buffer = cls(
            server, bi.ceil(len(lst) / channels), channels, alloc=False)
        # It was forkIfNeeded, can't be implemented in Python because
        # yield statment scope is different. The check for need was:
        # if isinstance(_libsc3.main.current_tt, Routine). Always fork here
        # is even a bit more clear, use action to sync externally.
        def send_func():
            buffer.alloc()
            yield from server.sync()
            buffer.send_list(lst, 0, wait, action)

        stm.Routine.run(send_func)
        return buffer


    def alloc(self, completion_msg=None):
        self._server.send_msg(*self.alloc_msg(completion_msg))

    def alloc_msg(self, completion_msg=None):
        return [
            '/b_alloc', self._bufnum, self._frames,
            self._channels, fn.value(completion_msg, self)]

    def alloc_read(self, path, start_frame=0, frames=-1,
                   completion_msg=None):
        self._path = path
        self._start_frame = start_frame
        self._server.send_msg(*self.alloc_read_msg(
            path, start_frame, frames, completion_msg))

    def alloc_read_msg(self, path, start_frame=0, frames=-1,
                       completion_msg=None):
        self._path = path
        self._start_frame = start_frame
        return [
            '/b_allocRead', self._bufnum, path,
            start_frame, frames, fn.value(completion_msg, self)]

    def alloc_read_channel(self, path, start_frame=0, frames=-1,
                           channels=None, completion_msg=None):
        self._path = path
        self._start_frame = start_frame
        self._server.send_msg(*self.alloc_read_channel_msg(
            path, start_frame, frames, channels, completion_msg))

    def alloc_read_channel_msg(self, path, start_frame=0, frames=-1,
                               channels=None, completion_msg=None):
        self._path = path
        self._start_frame = start_frame
        return [
            '/b_allocReadChannel', self._bufnum, path, start_frame,
            frames, *channels, fn.value(completion_msg, self)]

    def read(self, path, file_start_frame=0, frames=-1,
             buf_start_frame=0, leave_open=False, action=None):
        # self._cache() # NOTE: __init__ llama a _cache
        self._do_on_info = action
        self._server.send_msg(*self.read_msg(
            path, file_start_frame, frames, buf_start_frame,
            leave_open, lambda buf: ['/b_query', buf.bufnum]))

    def read_no_update(self, path, file_start_frame=0, frames=-1,
                       buf_start_frame=0, leave_open=False,
                       completion_msg=None):
        self._server.send_msg(*self.read_msg(
            path, file_start_frame, frames,
            buf_start_frame, leave_open, completion_msg))

    def read_msg(self, path, file_start_frame=0, frames=-1,
                 buf_start_frame=0, leave_open=False, completion_msg=None):
        self._path = path
        return [
            '/b_read', self._bufnum, path, file_start_frame, frames,
            buf_start_frame, leave_open, fn.value(completion_msg, self)]

    def read_channel(self, path, file_start_frame=0, frames=-1,
                     buf_start_frame=0, leave_open=False,
                     channels=None, action=None):
        self._do_on_info = action
        self._server.send_msg(*self.read_channel_msg(
            path, file_start_frame, frames, buf_start_frame,
            leave_open, channels, lambda buf: ['/b_query', buf.bufnum]))

    def read_channel_msg(self, path, file_start_frame=0, frames=-1,
                         buf_start_frame=0, leave_open=False, channels=None,
                         completion_msg=None):
        # // doesn't set my numChannels etc.
        self._path = path
        return [
            '/b_readChannel', self._bufnum, path, file_start_frame,
            frames, buf_start_frame, leave_open, *channels,
            fn.value(completion_msg, self)]

    def cue(self, path, start_frame=0, completion_msg=None):
        # // Preload a buffer for use with DiskIn.
        self._path = path
        self._server.send_msg(*self.cue_msg(path, start_frame, completion_msg))
        # NOTE: Doesn't call _cache()

    def cue_msg(self, path, start_frame=0, completion_msg=None):
        return [
            '/b_read', self._bufnum, path, start_frame, 0, 1,
            self._frames, fn.value(completion_msg, self)]  # NOTE: Uses 1 instead of True but not always.

    def load_list(self, channel_lst, start_frame=0, action=None):  # Was load_collection
        if self._server.is_local:
            framesize = (self._frames - start_frame) * self._channels
            # if len(channel_lst) > self._channels:
            #     # Channel mismatch is reported by Server.
            #     _logger.warning('channel_lst has more channels than buffer')
            for i, chn in enumerate(channel_lst[:]):
                if len(chn) > framesize:
                    _logger.warning(
                        f'channel_lst[{i}] larger than '
                        'available number of frames')
                channel_lst[i] = list(array.array('f', chn))  # Type check & cast.
            path = str(
                plf.Platform.tmp_dir / ('SC_' + uuid.uuid4().hex + '.wav'))
            sample_rate = int(self._server._status_watcher.sample_rate)
            try:
                # Was using SoundFile in sclang.
                _write_wave_file(path, channel_lst, sample_rate)
            except Exception as e:
                raise BufferException('failed to write data') from e

            def remove_file(buf):
                try:
                    pathlib.Path(path).unlink()
                    buf._path = None
                except:
                    _logger.warning(f'could not delete data file: {path}')
                finally:
                    fn.value(action, buf)

            return self.read(
                path, buf_start_frame=start_frame, action=remove_file)
        else:
            _logger.warning("cannot call 'load' with a non-local Server")

    def send_list(self, lst, start_frame=0, wait=-1, action=None):  # Was send_collection
        number = (int, float)
        if not isinstance(start_frame, number):
            raise TypeError('start_frame must be int of float')
        if not isinstance(wait, number):
            raise TypeError('wait must be int of float')
        lst = list(array.array('f', lst))  # Type check & cast.
        size = len(lst)
        if size > (self._frames - start_frame) * self._channels:
            _logger.warning('list larger than available number of frames')
        self._stream_list(
            lst, size, start_frame * self._channels, wait, action)

    def _stream_list(self, lst, size, start_frame=0, wait=-1, action=None):  # Was streamCollection
        def stream_func():
            # // wait = -1 allows an OSC roundtrip between packets.
            # // wait = 0 might not be safe in a high traffic situation.
            # // Maybe okay with tcp.
            max_bndl_size = 1626  # // Max size for setn under udp.
            pos = 0
            sublst = None
            while pos < size:
                sublst = lst[pos:pos+max_bndl_size]
                self._server.send_msg(
                    '/b_setn', self._bufnum, start_frame + pos,
                    len(sublst), *sublst)
                pos += max_bndl_size
                if wait >= 0:
                    yield wait
                else:
                    yield from self._server.sync()
            fn.value(action, self)

        stm.Routine.run(stream_func)

    # // these next two get the data and put it in a float array
    # // which is passed to action

    def load_to_list(self, index=0, count=-1, action=None):
        def load_fork():
            path = str(
                plf.Platform.tmp_dir / ('SC_' + uuid.uuid4().hex + '.wav'))
            self.write(path, 'wav', 'float', count, index)
            yield from self._server.sync()
            channel_lst = _read_wave_file(path)
            channel_lst = [list(l) for l in channel_lst]
            try:
                pathlib.Path(path).unlink()
            except:
                _logger.warning(f'could not delete data file: {path}')
            fn.value(action, channel_lst, self)

        stm.Routine.run(load_fork)

    def get_to_list(self, index=0, count=None, wait=0.01,
                    timeout=3, action=None):
        # // risky without wait
        if action is None:
            raise ValueError('get_to_list without action makes no sense')  # *** NOTE: es que el orden de los parámetros debería ser distinto pero es contrario a la norma.

        # BUG: some methods have an strict type check but some others don't.
        max_udp_size = 1633  # // Max size for getn under udp.
        pos = index = int(index)
        if count is None:
            count = int(self._frames * self._channels)
        array = []  # [0.0] * count
        ref_count = int(bi.roundup(count / max_udp_size))
        count += pos
        done = False

        def resp_func(msg, *_):
            nonlocal done, ref_count
            if msg[1] == self._bufnum:
                array.extend(msg[4:])
                ref_count -= 1
                if ref_count <= 0:
                    done = True
                    resp.free()  # *** BUG: clear() ???
                    fn.value(action, array)  #, self)  # *** NOTE: CHANGEG: because get & getn don't pass self to action, only data

        resp = rdf.OscFunc(resp_func, '/b_setn', self._server.addr)

        def getn_func():
            nonlocal pos
            while pos < count:
                getsize = bi.min(max_udp_size, count - pos)
                self._server.send_msg(*self.getn_msg(pos, getsize))
                pos += getsize
                if wait >= 0:
                    yield wait
                else:
                    yield from self._server.sync()

        stm.Routine.run(getn_func)

        # // Lose the responder if the network choked.
        def timeout_func():
            if not done:
                resp.free()
                _logger.warning('get_to_list failed, try increasing wait time')  # *** NOTE: timeout may also fail for long buffers.

        clk.SystemClock.sched(timeout, timeout_func)

    def write(self, path=None, header_format="aiff", sample_format="int24",
              frames=-1, start_frame=0, leave_open=False,
              completion_msg=None):
        if self._bufnum is None:
            raise BufferAlreadyFreed('write')

        if path is None:
            dir = plf.Platform.recording_dir
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            path = dir / ('SC_' + timestamp + '.' + header_format)
        else:
            path = pathlib.Path(path)
            if not path.suffix:
                path = pathlib.Path(str(path) + '.' + header_format)

        self._server.send_msg(*self.write_msg(
            str(path), header_format, sample_format, frames,
            start_frame, leave_open, completion_msg))

    def write_msg(self, path, header_format="aiff", sample_format="int24",
                  frames=-1, start_frame=0, leave_open=False,
                  completion_msg=None):
        if self._bufnum is None:
            raise BufferAlreadyFreed('write_msg')
        # // Doesn't change my path.
        return ['/b_write', self._bufnum, path, header_format, sample_format,
                int(frames), int(start_frame), int(leave_open),
                fn.value(completion_msg, self)]

    def free(self, completion_msg=None):
        if self._bufnum is None:
            _logger.warning('Buffer has already been freed')
        self._server.send_msg(*self.free_msg(completion_msg))

    def free_msg(self, completion_msg=None):
        if self._bufnum is None:
            _logger.warning(
                'cannot call free_msg on a Buffer that has been freed')
        self._uncache()
        self._server._buffer_allocator.free(self._bufnum)
        msg = ['/b_free', self._bufnum, fn.value(completion_msg, self)]
        self._bufnum = self._frames = self._channels = None
        self._sample_rate = self._path = self._start_frame = None
        return msg

    @classmethod
    def free_all(cls, server=None):  # Move up?
        server = server if server is not None else srv.Server.default
        server.free_all_buffers()
        type(self)._clear_server_caches(server) # *** BUG: no hace _clear_server_caches de default si es nil en sclang.

    def zero(self, completion_msg=None):
        if self._bufnum is None:
            raise BufferAlreadyFreed('zero')
        self._server.send_msg(*self.zero_msg(completion_msg))

    def zero_msg(self, completion_msg=None):
        if self._bufnum is None:
            raise BufferAlreadyFreed('zero_msg')
        return ['/b_zero', self._bufnum, fn.value(completion_msg, self)]

    def set(self, index, value, *more_pairs):
        if self._bufnum is None:
            raise BufferAlreadyFreed('set')
        self._server.send_msg(*self.set_msg(index, value, *more_pairs))

    def set_msg(self, index, value, *more_pairs):
        if self._bufnum is None:
            raise BufferAlreadyFreed('set_msg')
        return ['/b_set', self._bufnum, index, value, *more_pairs]

    def setn(self, *args):
        if self._bufnum is None:
            raise BufferAlreadyFreed('setn')
        self._server.send_msg(*self.setn_msg(*args))

    def setn_msg(self, *args):
        if self._bufnum is None:
            raise BufferAlreadyFreed('setn_msg')
        nargs = []
        for control, values in utl.gen_cclumps(args, 2):
            if isnstance(values, list):
                nargs.extend([control, len(values), *values])
            else:
                nargs.extend([control, 1, values])
        return ['/b_setn', self._bufnum, *nargs]

    def get(self, index, action):
        if self._bufnum is None:
            raise BufferAlreadyFreed('get')

        def resp_func(msg, *_):
            # // The server replies with a message of the form:
            # // [/b_set, bufnum, index, value]. We want 'value,'
            # // which is at index 3.
            fn.value(action, msg[3])

        rdf.OscFunc(
            resp_func, '/b_set', self._server.addr,
            arg_template=[self._bufnum, index]).one_shot()

        self._server.send_msg(*self.get_msg(index))

    def get_msg(self, index):  # *** BUG: sclang, los *_msg van sin action acá.
        if self._bufnum is None:
            raise BufferAlreadyFreed('get_msg')
        return ['/b_get', self._bufnum, index]

    def getn(self, index, count, action):
        if self._bufnum is None:
            raise BufferAlreadyFreed('getn')

        def resp_func(msg, *_):
            # // The server replies with a message of the form:
            # // [/b_setn, bufnum, starting index, length, ...sample values].
            # // We want the sample values, which start at index 4.
            fn.value(action, msg[4:])

        rdf.OscFunc(
            resp_func, '/b_setn', self._server.addr,
            arg_template=[self._bufnum, index]).one_shot()

        self._server.send_msg(*self.getn_msg(index, count))

    def getn_msg(self, index, count):  # *** BUG: sclang, los *_msg van sin action acá.
        if self._bufnum is None:
            raise BufferAlreadyFreed('getn_msg')
        return ['b_getn', self._bufnum, index, count]

    def fill(self, start, frames, values):
        if self._bufnum is None:
            raise BufferAlreadyFreed('fill')
        self._server.send_msg(*self.fill_msg(start, frames, *values))

    def fill_msg(self, start, frames, *values):
        if self._bufnum is None:
            raise BufferAlreadyFreed('fill_msg')
        return ['/b_fill', self._bufnum, start, int(frames), *values]  # *** NOTE: puede enviar más values que frames, ignora el servidor, los checks de tipos y valores en estas clases son raros.


    ### Gen commands ###

    def _gen_action_responder(self, action):
        if action is not None:
            def resp_func(msg, *_):
                # // The server replies with a message of the form:
                # // [/done, /b_gen, bufnum]
                fn.value(action, self)

            rdf.OscFunc(
                resp_func, '/done', self._server.addr,
                arg_template=['/b_gen', self._bufnum]).one_shot()  # *** BUG: comprobar que filtra por arg_template (no recuerdo si está implementado así).

    def _gen_oflags(self, normalize, as_wavetable, clear_first):
        flags = (int(normalize), int(as_wavetable) * 2, int(clear_first) * 4)
        return sum(flags)

    def normalize(self, new_max=1, as_wavetable=False, action=None):
        if self._bufnum is None:
            raise BufferAlreadyFreed('normalize')
        self._gen_action_responder(action)
        self._server.send_msg(*self.normalize_msg(new_max, as_wavetable))

    def normalize_msg(self, new_max=1, as_wavetable=False):
        if self._bufnum is None:
            raise BufferAlreadyFreed('normalize_msg')
        if as_wavetable:
            format = 'wnormalize'
        else:
            format = 'normalize'
        return ['/b_gen', self._bufnum, format, new_max]  # format would be cmd?

    def gen(self, cmd, args=(), normalize=True, as_wavetable=True,
            clear_first=True, action=None):
        if self._bufnum is None:
            raise BufferAlreadyFreed('gen')
        self._gen_action_responder(action)
        self._server.send_msg(*self.gen_msg(
            cmd, args, normalize, as_wavetable, clear_first))

    def gen_msg(self, cmd, args=(), normalize=True, as_wavetable=True,
                clear_first=True):
        if self._bufnum is None:
            raise BufferAlreadyFreed('gen')
        oflags = self._gen_oflags(normalize, as_wavetable, clear_first)
        return ['/b_gen', self._bufnum, cmd, oflags, *args]

    def sine1(self, amps, normalize=True, as_wavetable=True,
              clear_first=True, action=None):
        if self._bufnum is None:
            raise BufferAlreadyFreed('sine1')
        self._gen_action_responder(action)
        self._server.send_msg(*self.sine1_msg(
            amps, normalize, as_wavetable, clear_first))

    def sine1_msg(self, amps, normalize=True, as_wavetable=True,
                  clear_first=True):
        if self._bufnum is None:
            raise BufferAlreadyFreed('sine1_msg')
        oflags = self._gen_oflags(normalize, as_wavetable, clear_first)
        return ['/b_gen', self._bufnum, 'sine1', oflags, *amps]

    def sine2(self, freqs, amps, normalize=True, as_wavetable=True,
              clear_first=True, action=None):
        if self._bufnum is None:
            raise BufferAlreadyFreed('sine2')
        self._gen_action_responder(action)
        self._server.send_msg(*self.sine2_msg(
            freqs, amps, normalize, as_wavetable, clear_first))

    def sine2_msg(self, freqs, amps, normalize=True, as_wavetable=True,
                  clear_first=True):
        if self._bufnum is None:
            raise BufferAlreadyFreed('sine2_msg')
        oflags = self._gen_oflags(normalize, as_wavetable, clear_first)
        return ['/b_gen', self._bufnum, 'sine2', oflags,
                utl.lace([freqs, amps], len(freqs) * 2)]

    def sine3(self, freqs, amps, phases, normalize=True, as_wavetable=True,
              clear_first=True, action=None):
        if self._bufnum is None:
            raise BufferAlreadyFreed('sine3')
        self._gen_action_responder(action)
        self._server.send_msg(*self.sine3_msg(
            freqs, amps, phases, normalize, as_wavetable, clear_first))

    def sine3_msg(self, freqs, amps, phases, normalize=True,
                  as_wavetable=True, clear_first=True):
        if self._bufnum is None:
            raise BufferAlreadyFreed('sine3_msg')
        oflags = self._gen_oflags(normalize, as_wavetable, clear_first)
        return ['/b_gen', self._bufnum, 'sine3', oflags,
                utl.lace([freqs, amps, phases], len(freqs) * 2)]

    def cheby(self, amps, normalize=True, as_wavetable=True,
              clear_first=True, action=None):
        if self._bufnum is None:
            raise BufferAlreadyFreed('cheby')
        self._gen_action_responder(action)
        self._server.send_msg(*self.cheby_msg(
            amps, normalize, as_wavetable, clear_first))

    def cheby_msg(self, amps, normalize=True, as_wavetable=True,
                  clear_first=True):
        if self._bufnum is None:
            raise BufferAlreadyFreed('cheby_msg')
        oflags = self._gen_oflags(normalize, as_wavetable, clear_first)
        return ['/b_gen', self._bufnum, 'cheby', oflags, *amps]

    def copy_data(self, dst_buffer, dst_start=0, start=0,
                  num_samples=-1, action=None):
        if self._bufnum is None:
            raise BufferAlreadyFreed('copy_data')

        if action is not None:
            def resp_func(msg, *_):
                # // The server replies with a message of the form:
                # // [/done, /b_gen, bufnum]
                fn.value(action, self, dst_buffer)

            rdf.OscFunc(
                resp_func, '/done', self._server.addr,
                arg_template=['/b_gen', self._bufnum]).one_shot()  # *** BUG: comprobar que filtra por arg_template (no recuerdo si está implementado así).

        self._server.send_msg(*self.copy_msg(
            dst_buffer, dst_start, start, num_samples))

    def copy_data_msg(self, dst_buffer, dst_start=0, start=0, num_samples=-1):
        if self._bufnum is None:
            raise BufferAlreadyFreed('copy_data_msg')
        return ['/b_gen', dst_buffer.bufnum, 'copy', dst_start,
                self._bufnum, start, num_samples]


    def close(self, completion_msg=None):
        # // Close a file, write header, after DiskOut usage.
        if self._bufnum is None:
            raise BufferAlreadyFreed('close')
        self._server.send_msg(*self.close_msg(completion_msg))

    def close_msg(self, completion_msg):
        if self._bufnum is None:
            raise BufferAlreadyFreed('close_msg')
        return ['/b_close', self._bufnum, fn.value(completion_msg, self)]

    def query(self, action=None):
        if self._bufnum is None:
            raise BufferAlreadyFreed('query')
        if action is None:
            def action(addr, bufnum, frames, channels, sample_rate):
                _logger.info(
                    f'bufnum: {bufnum}\n'
                    f'frames: {frames}\n'
                    f'channels: {channels}\n'
                    f'sample_rate: {sample_rate}')

        def resp_func(msg, *_):
            fn.value(action, *msg)

        rdf.OscFunc(
            resp_func, '/b_info', self._server.addr,
            arg_template=[self._bufnum]).one_shot()
        self._server.send_msg('/b_query', self._bufnum)

    def query_msg(self):
        if self._bufnum is None:
            raise BufferAlreadyFreed('query_msg')
        return ['/b_query', self._bufnum]

    def update_info(self, action):
        # // Add to the array here. That way, update will
        # // be accurate even if this buf has been freed.
        self._cache()
        self._do_on_info = action
        self._server.send_msg('/b_query', self._bufnum)


    ### Cache methods ###

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
                    buffer._frames = msg[2]
                    buffer._channels = msg[3]
                    buffer._sample_rate = msg[4]
                    buffer._query_done()
                except KeyError:
                    pass

            resp = rdf.OscFunc(resp_func, '/b_info', server.addr)
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
        # // Called from Server when b_info is received.
        fn.value(self._do_on_info, self)
        self._do_on_info = None

    def __repr__(self):
        return (
            f'{type(self).__name__}({self._bufnum}, {self._frames}, '
            f'{self._channels}, {self._sample_rate}, {self._path})')


    ### UGen graph parameter interface ###

    def _as_ugen_input(self, *_):
        return self.bufnum

    def _as_audio_rate_input(self):
        raise TypeError("Buffer can't be used as audio rate input")


    ### Node parameter interface ###

    def _as_control_input(self):
        return self.bufnum


    # asBufWithValues # NOTE: se implementa acá, en Ref y en SimpleNumber pero no se usa en la librería estandar.


# Minimal utility functions to avoid depencencies.

import struct

def _wave_header(frames, channels, sample_rate):
    return (
        b'RIFF' +
        struct.pack('<L', frames + 36) +  # Remaining size
        b'WAVE' +
        # Format chunk.
        b'fmt ' +
        struct.pack('<L', 16) +  # Size
        struct.pack('<H', 3) +  # IEEE float PCM
        struct.pack('<H', channels) +
        struct.pack('<L', sample_rate) +
        struct.pack('<L', 4 * sample_rate * channels) +
        struct.pack('<H', 4 * channels) +
        struct.pack('<H', 32) +
        # Data chunk
        b'data' +
        struct.pack('<L', 4 * frames * channels)  # Size
    )

def _write_wave_file(path, data, sample_rate):
    # data is [ch1[float, float, ...], ch2[], ...]
    with open(path, 'w+b') as file:
        channels = len(data)
        fmt = '<' + 'f' * channels
        file.write(_wave_header(len(data[0]), channels, sample_rate))
        for frame in zip(*data):
            file.write(struct.pack(fmt, *frame))

def _read_wave_file(path):
    ret = []
    with open(path, 'r+b') as file:
        file.seek(22)
        channels = struct.unpack('<H', file.read(2))[0]
        fmt = '<' + 'f' * channels
        size = 4 * channels

        # b'fmt ' chunk length
        file.seek(16)
        ck_len = struct.unpack('<L', file.read(4))[0]
        file.seek(20 + ck_len)

        while file.read(4) != b'data':
            data = file.read(4)
            if not data:
                raise Exception('bad file format or algorithm')
            ck_len = struct.unpack('<L', data)[0]
            file.seek(file.tell() + ck_len)

        for _ in range(struct.unpack('<L', file.read(4))[0] // size):
            ret.append(struct.unpack(fmt, file.read(size)))
    return list(zip(*ret))
