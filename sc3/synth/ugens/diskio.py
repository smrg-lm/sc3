"""DiskIO.sc"""

from ...base import utils as utl
from .. import ugen as ugn
from .. import _graphparam as gpp


class DiskOut(ugn.UGen):
    @classmethod
    def ar(cls, buf, input):
        return cls._multi_new('audio', buf, *utl.as_list(input))

    def _check_inputs(self):  # override
        if self._rate == 'audio':
            for input in self._inputs[1:]:
                if gpp.ugen_param(input)._as_ugen_rate() != 'audio':
                    return f'input was not audio rate: {input}'
        return self._check_valid_inputs()


class DiskIn(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, num_channels, buf, loop=0):
        return cls._multi_new('audio', num_channels, buf, loop)

    def _init_ugen(self, num_channels, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(num_channels, self.rate)


class VDiskIn(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, num_channels, buf, rate=1, loop=0, send_id=0):
        return cls._multi_new('audio', num_channels, buf, rate, loop, send_id)

    def _init_ugen(self, num_channels, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(num_channels, self.rate)
