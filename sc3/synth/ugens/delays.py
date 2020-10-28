"""Delays.sc"""

from .. import ugen as ugn
from .. import _graphparam as gpp


class Delay1(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, input=0.0):
        return cls._multi_new('audio', input)  # NOTE: No gpp.ugen_param(input)._as_audio_rate_input().

    @classmethod
    def kr(cls, input=0.0):
        return cls._multi_new('control', input)


class Delay2(Delay1):
    pass


# // These delays use real time allocated memory.

class DelayN(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, input=0.0, max_delay_time=0.2, delay_time=0.2):
        input = gpp.ugen_param(input)._as_audio_rate_input()
        return cls._multi_new('audio', input, max_delay_time, delay_time)

    @classmethod
    def kr(cls, input=0.0, max_delay_time=0.2, delay_time=0.2):
        return cls._multi_new('control', input, max_delay_time, delay_time)


class DelayL(DelayN):
    pass


class DelayC(DelayN):
    pass


class CombN(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, input=0.0, max_delay_time=0.2, delay_time=0.2, decay_time=0.2):
        input = gpp.ugen_param(input)._as_audio_rate_input()
        return cls._multi_new(
            'audio', input, max_delay_time, delay_time, decay_time)

    @classmethod
    def kr(cls, input=0.0, max_delay_time=0.2, delay_time=0.2, decay_time=0.2):
        return cls._multi_new(
            'control', input, max_delay_time, delay_time, decay_time)


class CombL(CombN):
    pass


class CombC(CombN):
    pass


class AllpassN(CombN):
    pass


class AllpassL(CombN):
    pass


class AllpassC(CombN):
    pass


# // These delays use shared buffers.

class BufDelayN(ugn.UGen):
    @classmethod
    def ar(cls, buf=0, input=0.0, delay_time=0.2):
        input = gpp.ugen_param(input)._as_audio_rate_input()
        return cls._multi_new('audio', buf, input, delay_time)

    @classmethod
    def kr(cls, buf=0, input=0.0, delay_time=0.2):
        return cls._multi_new('control', buf, input, delay_time)


class BufDelayL(BufDelayN):
    pass


class BufDelayC(BufDelayN):
    pass


class BufCombN(ugn.UGen):
    @classmethod
    def ar(cls, buf=0, input=0.0, delay_time=0.2, decay_time=1.0):
        input = gpp.ugen_param(input)._as_audio_rate_input()
        return cls._multi_new('audio', buf, input, delay_time)


class BufCombL(BufCombN):
    pass


class BufCombC(BufCombN):
    pass


class BufAllpassN(BufCombN):
    pass


class BufAllpassL(BufCombN):
    pass


class BufAllpassC(BufCombN):
    pass


# GrainTap, commented ugen.


class DelTapWr(ugn.UGen):
    @classmethod
    def ar(cls, buf=0, input=0.0):
        input = gpp.ugen_param(input)._as_audio_rate_input()
        return cls._multi_new('audio', buf, input)

    @classmethod
    def kr(cls, buf=0, input=0.0):
        return cls._multi_new('control', buf, input)


class DelTapRd(ugn.UGen):
    @classmethod
    def ar(cls, buf=0, phase=0.0, delay_time=0.2, interp=1):
        return cls._multi_new('audio', buf, phase, delay_time, interp)

    @classmethod
    def kr(cls, buf=0, phase=0.0, delay_time=0.2, interp=1):
        return cls._multi_new('control', buf, phase, delay_time, interp)
