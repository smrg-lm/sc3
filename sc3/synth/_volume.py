"""Volume.sc"""

import logging

from ..base import systemactions as sac
from ..base import builtins as bi
from ..base import model as mdl
from ..base import stream as stm
from ..base import clock as clk
from . import server as srv
from . import ugens as ugns
from . import synthdef as sdf
from . import node as nod


_logger = logging.getLogger(__name__)


class Volume():
    def __init__(self, server, start_bus=0, num_channels=None,
                 min=-90, max=6, persist=False):
        self._server = server
        self._start_bus = start_bus
        self._num_channels = num_channels
        self._min = min
        self._max = max
        self._persist = persist

        self._gain = 0.0
        self._lag = 0.1
        self._is_muted = False

        self._amp_synth = None
        self._num_output_channels = None
        self._def_name = None

        # // Execute immediately if we're already past server tree functions.
        if self._server._status_watcher.server_running:
            self._send_synthdef()
            self._update_synth()

        sac.ServerBoot.add(self._server, self.__on_server_boot)

    @property
    def server(self):
        return self._server

    @property
    def start_bus(self):
        return self._start_bus

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max

    @property
    def persist(self):
        return self._persist

    @property
    def num_channels(self):
        if self._num_channels is None:
            return self._server.options.output_channels
        else:
            return self._num_channels

    @num_channels.setter
    def num_channels(self, value):
        if self._amp_synth is not None and value != self.num_channels:
            _logger.warning(
                'Change in number of channels will not take '
                'effect until gain is reset to 0dB')
        else:
            self._num_channels = value

    @property
    def gain(self):
        return self._gain

    @gain.setter
    def gain(self, value):
        self._gain = bi.clip(value, self._min, self._max)
        mdl.NotificationCenter.notify(self, 'gain', self._gain)
        self._update_synth()

    @property
    def lag(self):
        return self._lag

    @lag.setter
    def lag(self, value):
        self._lag = value
        if self._amp_synth is not None:
            self._amp_synth.set('volume_lag', self._lag)

    @property
    def is_muted(self):
        return self._is_muted

    @property
    def amp_synth(self):
        return self._amp_synth

    @property
    def num_output_channels(self):
        return self._num_output_channels

    def _send_synthdef(self):
        if self._server._status_watcher.has_booted:

            def send_synthdef():
                self._num_output_channels = self.num_channels
                self._def_name = f'volume_amp_ctrl_{self._num_output_channels}'

                def graph(volume_amp=1, volume_lag=0.1, gate=1, bus=None):
                    env = ugns.Linen.kr(gate, release_time=0.05, done_action=2)
                    input = ugns.In.ar(bus, self._num_output_channels)
                    input *= ugns.Lag.kr(volume_amp, volume_lag)
                    ugns.XOut.ar(bus, env, input)

                sdf.SynthDef(self._def_name, graph).send(self._server)
                yield from self._server.sync()
                sac.ServerTree.add(self._server, self.__on_server_tree)

            stm.Routine.run(send_synthdef)

    def _update_synth(self):
        amp = bi.dbamp(self.gain) if not self._is_muted else 0.0
        active = amp != 1.0
        if active:
            if self._server._status_watcher.has_booted:
                if self._amp_synth is None:
                    self._amp_synth = nod.Synth.after(
                        self._server.default_group, self._def_name,
                        ['volume_amp', amp, 'volume_lag', self._lag,
                         'bus', self._start_bus])
                else:
                    self._amp_synth.set('volume_amp', amp)
        else:
            if self._amp_synth is not None:
                self._amp_synth.release()
                self._amp_synth = None

    def mute(self):
        if not self._is_muted:
            self._is_muted = True
            mdl.NotificationCenter.notify(self, 'mute', True)
            self._update_synth()

    def unmute(self):
        if self._is_muted:
            self._is_muted = False
            mdl.NotificationCenter.notify(self, 'mute', False)
            self._update_synth()

    def free_synth(self):
        sac.ServerTree.remove(self._server, self.__on_server_tree)
        if self._amp_synth is not None:
            self._amp_synth.release()
            self._amp_synth = None

    def reset(self):
        # // Sets amp back to 1 - removes the synth.
        self._is_muted = False
        self.gain = 0.0

    def set_gain_range(self, min=None, max=None):
        '''Set a new gain range, min, max or both.'''
        if min is not None:
            self._min = min
        if max is not None:
            self._max = max
        mdl.NotificationCenter.notify(self, 'gain_range', min, max)
        clipped_gain = bi.clip(self._gain, min, max)
        if clipped_gain != self._gain:
            self.gain = clipped_gain


    ### System Actions ###

    def __on_server_boot(self, _):
        self._amp_synth = None
        self._send_synthdef()
        # // Only create synth now if it won't be created by ServerTree.
        if not self._persist:
            self._update_synth()

    def __on_server_tree(self, _):
        self._amp_synth = None
        if self._persist:
            self._update_synth()


    # No gui embedded.
    # gui
    # close


# class VolumeGui() No gui here.
