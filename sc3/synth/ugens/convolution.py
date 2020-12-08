"""FFT2.sc & PartConv"""

from ...base import builtins as bi
from .. import ugen as ugn


class Convolution(ugn.UGen):
    # // input and kernel are both audio rate changing signals.
    @classmethod
    def ar(cls, input, kernel, frame_size=512):
        return cls._multi_new('audio', input, kernel, frame_size)


class Convolution2(ugn.UGen):
    # // Fixed kernel convolver with fix by nescivi to update
    # // the kernel on receipt of a trigger message.
    @classmethod
    def ar(cls, input, kernel, trigger=0, frame_size=2048):  # NOTE: wrong kernel size crashes the server.
        return cls._multi_new('audio', input, kernel, trigger, frame_size)


class Convolution2L(ugn.UGen):
    # // Fixed kernel convolver with linear crossfade.
    @classmethod
    def ar(cls, input, kernel, trigger=0, frame_size=2048, crossfade=1):
        return cls._multi_new(
            'audio', input, kernel, trigger, frame_size, int(crossfade))


class StereoConvolution2L(ugn.MultiOutUGen):
    # // Fixed kernel stereo convolver with linear crossfade.
    @classmethod
    def ar(cls, input, kernel_L, kernel_R,
           trigger=0, frame_size=2048, crossfade=1):
        return cls._multi_new(
            'audio', input, kernel_L, kernel_R,
            trigger, frame_size, int(crossfade))

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        self._channels = ugn.ChannelList(
            [ugn.OutputProxy.new(self.rate, self, 0),
             ugn.OutputProxy.new(self.rate, self, 1)])
        return self._channels


class Convolution3(ugn.UGen):
    # // Time based convolution by nescivi.
    @classmethod
    def ar(cls, input, kernel, trigger=0, frame_size=2048):
        return cls._multi_new('audio', input, kernel, trigger, frame_size)

    @classmethod
    def kr(cls, input, kernel, trigger=0, frame_size=2048):
        return cls._multi_new('control', input, kernel, trigger, frame_size)


class PartConv(ugn.UGen):
    # This ugen uses Buffer's calc_partconv_bufsize and prepare_partconv.
    @classmethod
    def ar(cls, input, fftsize, irbufnum):
        return cls._multi_new('audio', input, fftsize, irbufnum)
