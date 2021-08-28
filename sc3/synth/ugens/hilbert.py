
from .. import ugen as ugn
from . import fft
from . import infougens as ifu
from . import delays as dly


class Hilbert(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, input):
        return cls._multi_new('audio', input)

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(2, self.rate)


class HilbertFIR(ugn.PseudoUGen):
    # // class using FFT (with a delay) for
    # // better results than the above UGen
    # // buffer should be 2048 or 1024
    # // 2048, better results, more delay
    # // 1024, less delay, little choppier results
    @classmethod
    def ar(cls, input, buffer):
        data = fft.FFT.new(buffer, input)
        data = fft.PV_PhaseShift90.new(data)
        delay = ifu.BufDur.kr(buffer)
        # // return [source, shift90]
        return ugn.ChannelList(
            [dly.DelayN.ar(input, delay, delay), fft.IFFT.ar(data)])


# Original comment is not clear, which was HilbertIIR?
# // single sideband amplitude modulation, using
# // optimized Hilbert phase differencing network
# // basically coded by Joe Anderson.

class FreqShift(ugn.UGen):
    @classmethod
    def ar(cls, input, freq_shift=0.0, phase=0.0):
        # // Phase of SSB.
        return cls._multi_new('audio', input, freq_shift, phase)
