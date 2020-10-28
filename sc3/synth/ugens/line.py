"""Line.sc"""

from ...base import builtins as bi
from .. import ugen as ugn
from .. import _graphparam as gpp


class Line(ugn.UGen):
    @classmethod
    def ar(cls, start=0.0, end=1.0, dur=1.0, done_action=0):
        return cls._multi_new('audio', start, end, dur, done_action)

    @classmethod
    def kr(cls, start=0.0, end=1.0, dur=1.0, done_action=0):
        return cls._multi_new('control', start, end, dur, done_action)


class XLine(ugn.UGen):
    @classmethod
    def ar(cls, start=1.0, end=2.0, dur=1.0, done_action=0):
        return cls._multi_new('audio', start, end, dur, done_action)

    @classmethod
    def kr(cls, start=1.0, end=2.0, dur=1.0, done_action=0):
        return cls._multi_new('control', start, end, dur, done_action)


class LinExp(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, input=0.0, srclo=0.0, srchi=1.0, dstlo=1.0, dsthi=2.0):
        return cls._multi_new('audio', input, srclo, srchi, dstlo, dsthi)

    @classmethod
    def kr(cls, input=0.0, srclo=0.0, srchi=1.0, dstlo=1.0, dsthi=2.0):
        return cls._multi_new('control', input, srclo, srchi, dstlo, dsthi)

    def _check_inputs(self):
        return self._check_sr_as_first_input()


class LinLin(ugn.PseudoUGen):
    @classmethod
    def ar(cls, input=0.0, srclo=0.0, srchi=1.0, dstlo=1.0, dsthi=2.0):
        scale = (dsthi - dstlo) / (srchi - srclo)
        offset = dstlo - (scale * srclo)
        return ugn.MulAdd.new(input, scale, offset)

    @classmethod
    def kr(cls, input=0.0, srclo=0.0, srchi=1.0, dstlo=1.0, dsthi=2.0):
        scale = (dsthi - dstlo) / (srchi - srclo)
        offset = dstlo - (scale * srclo)
        return input * scale + offset

    @classmethod
    def _method_selector_for_rate(cls, rate):  # FIXME: API, same in SelectX
        if rate == 'audio':
            return 'ar'
        elif rate == 'control':
            return 'kr'
        # return None  # original behaviour
        raise AttributeError(f'{cls.__name__} has no {rate} rate constructor')


class AmpComp(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, freq=bi.midicps(60), root=bi.midicps(60), exp=0.3333):
        return cls._multi_new('audio', freq, root, exp)

    @classmethod
    def kr(cls, freq=bi.midicps(60), root=bi.midicps(60), exp=0.3333):
        return cls._multi_new('control', freq, root, exp)

    @classmethod
    def ir(cls, freq=bi.midicps(60), root=bi.midicps(60), exp=0.3333):
        return cls._multi_new('scalar', freq, root, exp)

    def _check_inputs(self):
        if self.rate == 'audio':
            return self._check_sr_as_first_input()
        else:
            return None


class AmpCompA(AmpComp):
    @classmethod
    def ar(cls, freq=1000.0, root=0.0, min_amp=0.32, root_amp=1.0):
        return cls._multi_new('audio', freq, root, min_amp, root_amp)

    @classmethod
    def kr(cls, freq=1000.0, root=0.0, min_amp=0.32, root_amp=1.0):
        return cls._multi_new('control', freq, root, min_amp, root_amp)

    @classmethod
    def ir(cls, freq=1000.0, root=0.0, min_amp=0.32, root_amp=1.0):
        return cls._multi_new('scalar', freq, root, min_amp, root_amp)


class K2A(ugn.UGen, ugn.PureUGen):
    # // Control rate to audio rate converter.
    @classmethod
    def ar(cls, input=0.0):
        return cls._multi_new('audio', input)


class A2K(ugn.UGen, ugn.PureUGen):
    # // Audio rate to control rate converter. only needed in specific cases.
    @classmethod
    def kr(cls, input=0.0):
        return cls._multi_new('control', input)


class T2K(A2K):
    # // Audio rate to control rate trigger converter.
    def _check_inputs(self):
        if gpp.ugen_param(self.inputs[0])._as_ugen_rate() != 'audio':
            return 'First input is not audio rate'
        else:
            return None


class T2A(K2A):
    # // Control rate to audio rate trigger converter.
    @classmethod
    def ar(cls, input=0.0, offset=0):
        return cls._multi_new('audio', input, offset)


class DC(ugn.MultiOutUGen, ugn.PureUGen):
    @classmethod
    def ar(cls, input=0.0):
        return cls._multi_new('audio', input)

    @classmethod
    def kr(cls, input=0.0):
        return cls._multi_new('control', input)

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(len(inputs), self.rate)


class Silent(ugn.PseudoUGen):
    @classmethod
    def ar(cls, num_channels=1):
        sig = DC.ar(0)
        if num_channels == 1:
            return sig
        else:
            return ugn.ChannelList([sig] * num_channels)
