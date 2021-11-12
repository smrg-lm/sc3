"""Recorder.sc"""

import logging
import pathlib
import time

from ..base import model as mdl
from ..base import responders as rpd
from ..base import main as _libsc3
from ..base import builtins as bi
from ..base import stream as stm
from . import _graphparam as gpp
from . import ugens as ugns
from . import synthdef as sdf
from . import buffer as bff
from . import node as nod


_logger = logging.getLogger(__name__)


class Recorder():
    def __init__(self, server):
        self._server = server
        self._bus = None
        self._channels = None
        self._path = None

        self.rec_header_format = None
        self.rec_sample_format = None
        self.rec_buf_size = None

        self._record_buf = None
        self._record_node = None
        self._synthdef = None

        self._paused = False
        self._duration = 0
        self.notify_server = False
        self.file_prefix = 'SC_'

        self._responder = None
        self._id = None

    @property
    def server(self):
        return self._server

    @property
    def bus(self):
        return self._bus

    @property
    def channels(self):
        return self._channels

    @property
    def paused(self):
        return self._paused

    @property
    def duration(self):
        return self._duration

    @property
    def path(self):
        return self._path

    def record(self, path=None, bus=None, channels=None,
               node=None, duration=None):
        if self._server._status_watcher.unresponsive\
        or not self._server._status_watcher.server_running:
            _logger.error(f"server '{self.server.name}' is not running")
            return
        bus = bus if bus is not None else 0
        self._bus = gpp.node_param(bus)._as_control_input()

        if self._record_buf is None:
            def record_setup():
                self.prepare(path, channels)
                yield from self._server.sync()
                self.record(path, self._bus, channels, node, duration)
            stm.Routine.run(record_setup)
        else:
            if channels is not None and channels != self._channels:
                _logger.warning(
                    'cannot change recording number of channels while running')
                return

            if path is not None and path != self.path:
                raise ValueError(
                    'recording was prepared already with a different '
                    f'path: {self.path}, tried with this path: {path}')

            if not self.is_recording:
                self._record(self._bus, node, duration)
                self._changed_server('recording', True)
                _logger.info(
                    f"recording {self._channels} channel(s) from "
                    f"bus {self._bus} on path: '{self._path}'")
            else:
                if self._paused:
                    self.resume()
                else:
                    _logger.warning(
                        f'recording already ({self._duration} seconds)')

    def record_bus(self, bus, duration=None, path=None,
                   channels=None, node=None):
        if self.is_recording:
            _logger.warning(
                f'already recording from bus {self._bus} '
                f'({self._duration} seconds)')
            return
        n = bus.channels
        if channels is not None:  # and n is not None:
            n = min(channels, n)
        self.record(path, bus.index, n, node, duration)

    @property
    def is_recording(self):
        if self._record_node is None:
            return False
        else:
            return self._record_node.is_playing

    def num_frames(self):
        if self._record_buf is None:
            return None
        else:
            return self._record_buf.frames

    def pause(self):
        if self.is_recording:
            self._record_node.run(False)
            self._changed_server('pause')
            _logger.info(f'recording paused: {self._path}')
        else:
            _logger.warning('not recording')
        self._paused = True

    def resume(self):
        if self.is_recording:
            if self._paused:
                self._record_node.run(True)
                self._changed_server('recording', True)
                _logger.info(f'recording resumed: {self._path}')
        else:
            _logger.warning('not recording')
        self._paused = False

    def stop(self):
        if self._synthdef is not None:
            self._stop()
            self._changed_server('recording', False)
        else:
            _logger.warning('not recording')

    def prepare(self, path=None, channels=None):
        if not self._server._status_watcher.server_running:
            _logger.error(f"server '{self.server.name}' is not running")
            return
        if self.rec_buf_size is None:
            if self._server.options.rec_buf_size is None:
                n = self._server._status_watcher.sample_rate
                buf_size = bi.next_power_of_two(n)
            else:
                buf_size = self._server.options.rec_buf_size
        else:
            buf_size = self.rec_buf_size

        if self.rec_header_format is None:
            self.rec_header_format = self._server.options.rec_header_format
        if self.rec_sample_format is None:
            self.rec_sample_format = self._server.options.rec_sample_format
        if channels is None:
            channels = self._server.options.rec_channels

        if path is None:
            path = self._make_path()
        dir = pathlib.Path(path).parent
        dir.mkdir(exist_ok=True)

        self._record_buf = bff.Buffer(
            buf_size, channels, self._server,
            completion_msg=lambda buf: [
                '/b_write', buf.bufnum, path, self.rec_header_format,
                self.rec_sample_format, 0, 0, True])

        # if self._record_buf is None: raise Exception("could not allocate buffer")  # *** BUG: it can't be nil in sclang either
        self._path = path
        self._channels = channels
        self._id = bi.uid()

        def func(input, bufnum, duration):
            tick = ugns.Impulse.kr(1)
            timer = ugns.PulseCount.kr(tick) - 1
            done_action = 0 if self._duration <= 0 else 2
            ugns.Line.kr(0, 0, self._duration, done_action=done_action)
            ugns.SendReply.kr(tick, '/recording_duration', (timer,), self._id)
            ugns.DiskOut.ar(bufnum, ugns.In.ar(input, channels))

        self._synthdef = sdf.SynthDef(sdf.SynthDef.generate_tmp_name(), func)
        self._synthdef.send(self._server)

        _logger.info(f"preparing recording on '{self._server.name}'")

    def _record(self, bus, node, dur):
        self._record_node = nod.Synth.tail(
            node or 0, self._synthdef.name,
            ['input', bus, 'bufnum', self._record_buf, 'duration', dur])
        self._record_node.register(True)
        self._record_node.on_free(lambda: self.stop())

        if self._responder is None:
            def resp_recording_func(msg, *_):
                if msg[2] == self._id:
                    self._duration = msg[3]
                    self._changed_server('/recording_duration', self._duration)
            self._responder = rpd.OscFunc(
                resp_recording_func, '/recording_duration', self._server.addr)
        else:
            self._responder.enable()

    def _stop(self):
        if self._record_node.is_playing:
            self._record_node.unregister()
            self._record_node.free()
            self._record_node = None
        self._server.addr.send_msg('/d_free', self._synthdef.name)
        self._synthdef = None
        if self._record_buf is not None:
            self._record_buf.close(lambda buf: ['/b_free', buf.bufnum])
            _logger.info(f'recording stopped: {pathlib.Path(self._path).name}')
            self._record_buf = None
        self._bus = None
        self._channels = None
        self._path = None
        self._responder.disable()
        self._paused = False
        self._duration = 0
        self._changed_server('/recording_duration', 0)

    def _make_path(self):
        dir = str(_libsc3.main.platform.recording_dir)
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        return (dir + '/' + self.file_prefix + timestamp +
                '.' + self._server.options.rec_header_format)

    def _changed_server(self, msg, *args):
        if self.notify_server:
            mdl.NotificationCenter.notify(self, msg, *args)
