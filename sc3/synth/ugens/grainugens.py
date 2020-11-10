"""GrainUGens.sc"""

from .. import ugen as ugn


class GrainSin(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, num_channels=1, trigger=0, dur=1, freq=440,
           pan=0, env_bufnum=-1, max_grains=512):
        return cls._multi_new(
            'audio', num_channels, trigger, dur, freq,
            pan, env_bufnum, max_grains)

    def _init_ugen(self, num_channels, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(num_channels, self.rate)

    def _arg_names_inputs_offset(self):  # override
        return 1  # One less than sclang.


class GrainFM(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, num_channels=1, trigger=0, dur=1, car_freq=440,
           mod_freq=200, index=1, pan=0, env_bufnum=-1, max_grains=512):
        return cls._multi_new(
            'audio', num_channels, trigger, dur, car_freq,
            mod_freq, index, pan, env_bufnum, max_grains)

    def _init_ugen(self, num_channels, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(num_channels, self.rate)

    def _arg_names_inputs_offset(self):  # override
        return 1  # One less than sclang.


class GrainBuf(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, num_channels=1, trigger=0, dur=1, snd_buf=None, rate=1,
           pos=0, interp=2, pan=0, env_bufnum=-1, max_grains=512):
        return cls._multi_new(
            'audio', num_channels, trigger, dur, snd_buf, rate,
            pos, interp, pan, env_bufnum, max_grains)

    def _init_ugen(self, num_channels, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(num_channels, self.rate)

    def _arg_names_inputs_offset(self):  # override
        return 1  # One less than sclang.


class GrainIn(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, num_channels=1, trigger=0, dur=1, input=None,
           pan=0, env_bufnum=-1, max_grains=512):
        return cls._multi_new(
            'audio', num_channels, trigger, dur, input,
            pan, env_bufnum, max_grains)

    def _init_ugen(self, num_channels, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(num_channels, self.rate)

    def _arg_names_inputs_offset(self):  # override
        return 1  # One less than sclang.


class Warp1(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, num_channels=1, bufnum=0, pointer=0, freq_scale=1,
           window_size=0.2, env_bufnum=-1, overlaps=8,
           window_rand_ratio=0.0, interp=1):
        return cls._multi_new(
            'audio', num_channels, bufnum, pointer, freq_scale,
            window_size, env_bufnum, overlaps,
            window_rand_ratio, interp)

    def _init_ugen(self, num_channels, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(num_channels, self.rate)

    def _arg_names_inputs_offset(self):  # override
        return 1  # One less than sclang.
