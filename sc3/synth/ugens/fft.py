"""FFT.sc"""

from .. import ugen as ugn
from . import fftunpacking as ffu
from . import infougens as ifu


# // fft uses a local buffer for holding the buffered audio. wintypes are
# // defined in the C++ source. 0 is default, Welch; 1 is Hann; -1 is rect.


class FFT(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer, input=0.0, hop=0.5, wintype=0, active=1, winsize=0):
        return cls._multi_new('control', buffer, input, hop,
                              wintype, active, winsize)

    def fft_size(self):
        return ifu.BufFrames.ir(self.inputs[0])


class IFFT(ugn.WidthFirstUGen, ugn.UGen):
    _default_rate = 'audio'

    # @classmethod
    # def new(cls, buffer, wintype=0, winsize=0):
    #     return cls.ar(buffer, wintype, winsize)

    @classmethod
    def ar(cls, buffer, wintype=0, winsize=0):
        return cls._multi_new('audio', buffer, wintype, winsize)

    @classmethod
    def kr(cls, buffer, wintype=0, winsize=0):
        return cls._multi_new('control', buffer, wintype, winsize)


class PV_MagAbove(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer, threshold=0.0):
        return cls._multi_new('control', buffer, threshold)


class PV_MagBelow(PV_MagAbove):
    pass


class PV_MagClip(PV_MagAbove):
    pass


class PV_LocalMax(PV_MagAbove):
    pass


class PV_MagSmear(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer, bins=0.0):
        return cls._multi_new('control', buffer, bins)


class PV_BinShift(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer, stretch=1.0, shift=0.0, interp=0):
        return cls._multi_new('control', buffer, stretch, shift, interp)


class PV_MagShift(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer, stretch=1.0, shift=0.0):
        return cls._multi_new('control', buffer, stretch, shift)


class PV_MagSquared(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer):
        return cls._multi_new('control', buffer)


class PV_MagNoise(PV_MagSquared):
    pass


class PV_PhaseShift90(PV_MagSquared):
    pass


class PV_PhaseShift270(PV_MagSquared):
    pass


class PV_Conj(PV_MagSquared):
    pass


class PV_PhaseShift(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer, shift, integrate=0):
        return cls._multi_new('control', buffer, shift, integrate)


class PV_BrickWall(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer, wipe=0.0):
        return cls._multi_new('control', buffer, wipe)


class PV_BinWipe(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer_a, buffer_b, wipe=0.0):
        return cls._multi_new('control', buffer_a, buffer_b, wipe)


class PV_MagMul(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer_a, buffer_b):
        return cls._multi_new('control', buffer_a, buffer_b)


class PV_CopyPhase(PV_MagMul):
    pass


class PV_Copy(PV_MagMul):
    pass


class PV_Max(PV_MagMul):
    pass


class PV_Min(PV_MagMul):
    pass


class PV_Mul(PV_MagMul):
    pass


class PV_Div(PV_MagMul):
    pass


class PV_Add(PV_MagMul):
    pass


class PV_MagDiv(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer_a, buffer_b, zeroed=0.0001):
        return cls._multi_new('control', buffer_a, buffer_b, zeroed)


class PV_RandComb(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer, wipe=0.0, trig=0.0):
        return cls._multi_new('control', buffer, wipe, trig)


class PV_RectComb(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer, num_teeth=0.0, phase=0.0, width=0.5):
        return cls._multi_new('control', buffer, num_teeth, phase, width)


class PV_RectComb2(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer_a, buffer_b, num_teeth=0.0, phase=0.0, width=0.5):
        return cls._multi_new('control', buffer_a, buffer_b,
                              num_teeth, phase, width)


class PV_RandWipe(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer_a, buffer_b, wipe=0.0, trig=0.0):
        return cls._multi_new('control', buffer_a, buffer_b, wipe, trig)


class PV_Diffuser(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer, trig=0.0):
        return cls._multi_new('control', buffer, trig)


class PV_MagFreeze(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer, freeze=0.0):
        return cls._multi_new('control', buffer, freeze)


class PV_BinScramble(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer, wipe=0.0, width=0.2, trig=0.0):
        return cls._multi_new('control', buffer, wipe, width, trig)


class FFTTrigger(ffu.PV_ChainUGen):
    @classmethod
    def new(cls, buffer, hop=0.5, polar=0.0):
        return cls._multi_new('control', buffer, hop, polar)


# Commented ugens:
# class PV_OscBank(ffu.PV_ChainUGen):
# class PV_Scope(ffu.PV_ChainUGen):
# class PV_TimeAverageScope(PV_Scope):
# class PV_MagAllTimeAverage(PV_MagSquared):
# class PV_MagOnePole(ffu.PV_ChainUGen):
# class PV_MagPeakDecay(ffu.PV_ChainUGen):
# class PV_TimeSmear(PV_MagSmear):
# class PV_LoBitEncoder(ffu.PV_ChainUGen):
