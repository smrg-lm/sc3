"""InfoUGens.sc"""

from .. import ugen as ugn


class InfoUGenBase(ugn.UGen):
    _default_rate = 'scalar'

    @classmethod
    def ir(cls):
        return cls._multi_new('scalar')


class SampleRate(InfoUGenBase):
    pass


class SampleDur(InfoUGenBase):
    pass


class RadiansPerSample(InfoUGenBase):
    pass


class BlockSize(InfoUGenBase):
    pass


class ControlRate(InfoUGenBase):
    pass


class ControlDur(InfoUGenBase):
    pass


class SubsampleOffset(InfoUGenBase):
    pass


class NumOutputBuses(InfoUGenBase):
    pass


class NumInputBuses(InfoUGenBase):
    pass


class NumAudioBuses(InfoUGenBase):
    pass


class NumControlBuses(InfoUGenBase):
    pass


class NumBuffers(InfoUGenBase):
    pass


class NodeID(InfoUGenBase):
    pass


class NumRunningSynths(InfoUGenBase):
    @classmethod
    def kr(cls):
        return cls._multi_new('control')


class BufInfoUGenBase(ugn.UGen):
    _default_rate = 'control'

    @classmethod
    def kr(cls, bufnum):
        return cls._multi_new('control', bufnum)

    @classmethod
    def ir(cls, bufnum):
        # // The .ir method is not the safest choice, since a buffer can be
        # // reallocated at any time, using .ir will not track the changes.
        return cls._multi_new('scalar', bufnum)


class BufSampleRate(BufInfoUGenBase):
    pass


class BufRateScale(BufInfoUGenBase):
    pass


class BufFrames(BufInfoUGenBase):
    pass


class BufSamples(BufInfoUGenBase):
    pass


class BufDur(BufInfoUGenBase):
    pass


class BufChannels(BufInfoUGenBase):
    pass
