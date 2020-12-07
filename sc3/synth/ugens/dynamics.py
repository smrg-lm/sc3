"""Compander.sc"""

from .. import ugen as ugn
from . import delays as dly


class Amplitude(ugn.UGen):
    _default_rate = 'control'

    @classmethod
    def ar(cls, input=0.0, attack_time=0.01, release_time=0.01):
        return cls._multi_new('audio', input, attack_time, release_time)

    @classmethod
    def kr(cls, input=0.0, attack_time=0.01, release_time=0.01):
        return cls._multi_new('control', input, attack_time, release_time)


class Normalizer(ugn.UGen):
    # buffer?
    @classmethod
    def ar(cls, input=0.0, level=1, dur=0.01):
        return cls._multi_new('audio', input, level, dur)


class Limiter(Normalizer):
    pass


class Compander(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, control=0.0, thresh=0.5, slope_below=1.0,
           slope_above=1.0, clamp_time=0.01, relax_time=0.1):
        return cls._multi_new(
            'audio', input, control, thresh, slope_below,
            slope_above, clamp_time, relax_time)


# // CompanderD passes the signal directly to the control input,
# // but adds a delay to the process input so that the lag in the gain
# // clamping will not lag the attacks in the input sound

class CompanderD(ugn.PseudoUGen):
    @classmethod
    def ar(cls, input=0.0, thresh=0.5, slope_below=1.0, slope_above=1.0,
           clamp_time=0.01, relax_time=0.01):
        return Compander.ar(
            dly.DelayN.ar(input, clamp_time, clamp_time), input, thresh,
            slope_below, slope_above, clamp_time, relax_time)
