"""Recorder.sc"""

import logging
import pathlib
import time

from ..base import model as mdl
from ..base import responsedefs as rdf
from ..base import main as _libsc3
from ..seq import stream as stm
from ..seq import clock as clk
from . import _graphparam as gpp
from . import ugens as ugns
from . import synthdef as sdf
from . import buffer as bff
from . import node as nod


_logger = logging.getLogger(__name__)


class Recorder():
    def __init__(self, server):
        self._server = server
        self.num_channels = None

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
    def paused(self):
        return self._paused

    @property
    def duration(self):
        return self._duration

    @property
    def path(self):
        return self._record_buf.path if self._record_buf is not None else None

    def record(self, path=None, bus=None, num_channels=None,
               node=None, duration=None):
        if self._server.status_watcher.unresponsive\
        or not self._server.status_watcher.server_running: # Was if_not_running.
            return
        bus = bus if bus is not None else 0
        bus = gpp.node_param(bus)._as_control_input()

        if self._record_buf is None:
            def record_setup():
                self.prepare_for_record(path, num_channels)
                self._server.sync()
                self.record(path, bus, num_channels, node, duration)
            stm.Routine.run(record_setup, clk.TempoClock.default)
        else:
            if num_channels is not None and num_channels != self.num_channels:
                _logger.warning(
                    'cannot change recording number of channels while running')
                return

            if path is not None and path != this.path:
                raise ValueError(
                    'recording was prepared already with a different '
                    f'path: {self.path}, tried with this path: {path}')

            if not self.is_recording():
                self._record(bus, node, duration)
                self._changed_server('recording', True)
                channels = [bus + x for x in range(0, self.num_channels)]
                _logger.info(
                    f"recording channels {channels} on "
                    f"path: '{self._record_buf.path}'")
            else:
                if self._paused:
                    self.resume_recording()
                else:
                    _logger.warning(
                        f'recording already ({self._duration} seconds)')

    def record_bus(self, bus, duration=None, path=None,
                   num_channels=None, node=None):
        n = bus.num_channels
        if num_channels is not None:  # and n is not None:
            n = min(num_channels, n)
        self.record(path, bus.index, n, node, duration)

    def is_recording(self):
        if self._record_node is None:
            return False
        else:
            return self._record_node.is_playing

    def num_frames(self):
        if self._record_buf is None:
            return None
        else:
            return self._record_buf.num_frames

    def pause_recording(self):
        if self.is_recording():
            self._record_node.run(False)
            self._changed_server('pause_recording')
            _logger.info(f'recording paused: {self._record_buf.path}')
        else:
            _logger.warning('not recording')
        self._paused = True

    def resume_recording(self):
        if self.is_recording():
            if self._paused:
                self._record_node.run(True)
                self._changed_server('recording', True)
                _logger.info(f'recording resumed: {self._record_buf.path}')
        else:
            _logger.warning('not recording')
        self._paused = False

    def stop_recording(self):
        if self._synthdef is not None:
            self._stop_record()
            self._changed_server('recording', False)
        else:
            _logger.warning('not recording')

    def prepare_for_record(self, path=None, num_channels=None):
        if self.rec_buf_size is None:
            if self._server.rec_buf_size is None:
                n = self._server.sample_rate()
                buf_size = pow(2, math.ceil(math.log(n) / math.log(2)))  # nextPowerOfTwo
            else:
                buf_size = self._server.options.rec_buf_size
        else:
            buf_size = self.rec_buf_size

        if self.rec_header_format is None:
            self.rec_header_format = self._server.options.rec_header_format
        if self.rec_sample_format is None:
            self.rec_sample_format = self._server.options.rec_sample_format
        if num_channels is None:
            num_channels = self._server.options.rec_channels

        if path is None:
            path = self._make_path()
        dir = pathlib.Path(path).parent
        dir.mkdir(exist_ok=True)

        self._record_buf = bff.Buffer.new_alloc(
            self._server, buf_size,
            lambda buf: buf.write_msg(
                path, self.rec_header_format,
                self.rec_sample_format, 0, 0, True))

        # if self._record_buf is None: raise Exception("could not allocate buffer")  # BUG: it can't be nil in sclang either
        self._record_buf.path = path
        self.num_channels = num_channels
        self._id = utl.UniqueID.next()

        def graph_func(input, bufnum, duration):
            tick = ugns.Impulse.kr(1)
            timer = ugns.PulseCount.kr(tick) - 1
            done_action = 0 if self._duration <= 0 else 2
            ungs.Line.kr(0, 0, self._duration, done_action=done_action)
            ugns.SendReply.kr(tick, 'recording_duration', timer, self._id)
            ugns.DiskOut.ar(bufnum, ugns.In.ar(input, num_channels))

        self._synthdef = sdf.SynthDef(
            sdf.SynthDef.generate_tmp_name(), graph_func)
        self._synthdef.send(self._server)

        _logger.info(f"preparing recording on '{self._server.name}'")

    def _record(self, bus, node, dur):
        self._record_node = nod.Synth.tail(
            node or 0, self._synthdef.name,
            ['input', bus, 'bufnum', self._record_buf, 'duration', dur])
        self._record_node.register(True)
        self._record_node.on_free(lambda: self.stop_recording())

        if self._responder is None:
            def resp_recording_func(msg):
                if msg[2] == self._id:
                    self._duration = msg[3]
                    self._changed_server('recording_duration', self._duration)
            self._responder = rdf.OSCFunc(
                resp_recording_func, 'recording_duration', self._server.addr)
        else:
            self._responder.enable()

    def _stop_record(self):
        if self._record_node.is_playing:
            self._record_node.unregister()
            self._record_node.free()
            self._record_node = None
        self._server.send_msg('/d_free', self._synthdef.name)
        self._synthdef = None
        if self._record_buf is not None:
            record_path = self._record_buf.path
            self._record_buf.close(lambda buf: buf.free_msg())
            _logger.info(f'recording stoped: {pathlib.Path(record_path).name}')
            self._record_buf = None
        self._responder.disable()
        self._paused = False
        self._duration = 0
        self._changed_server('recording_duration', 0)

    def _make_path(self):
        dir = str(_libsc3.main.platform.recording_dir)
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        return (dir + '/' + self.file_prefix + timestamp +
                '.' + self._server.rec_header_format)

    def _changed_server(self, msg, *args):
        if self.notify_server:
            mdl.NotificationCenter.notify(self, msg, *args)
