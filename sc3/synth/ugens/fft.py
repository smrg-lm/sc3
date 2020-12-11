"""FFT.sc, FFT2.sc and FFTUnpacking.sc"""

from ...base import utils as utl
from .. import ugen as ugn
from . import infougens as ifu


class PV_ChainUGen(ugn.WidthFirstUGen):
    # // Conveniences to apply calculations to an FFT chain.

    def fft_size(self):
        return self._inputs[0].fft_size()

    # pvcalc
    # pvcalc2
    # pvcollect
    # addCopiesIfNeeded


# FFT.sc

class FFT(PV_ChainUGen):
    # // fft uses a local buffer for holding the buffered
    # // audio. wintypes are defined in the C++ source.
    # // 0 is default, Welch; 1 is Hann; -1 is rect.
    _default_rate = 'control'

    @classmethod
    def kr(cls, buffer, input=0.0, hop=0.5, wintype=0, active=1, winsize=0):
        return cls._multi_new(
            'control', buffer, input, hop, wintype, active, winsize)

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


class FFTTrigger(PV_ChainUGen):
    @classmethod
    def new(cls, buffer, hop=0.5, polar=0.0):
        return cls._multi_new('control', buffer, hop, polar)


class PV_MagAbove(PV_ChainUGen):
    @classmethod
    def new(cls, buffer, threshold=0.0):
        return cls._multi_new('control', buffer, threshold)


class PV_MagBelow(PV_MagAbove):
    pass


class PV_MagClip(PV_MagAbove):
    pass


class PV_LocalMax(PV_MagAbove):
    pass


class PV_MagSmear(PV_ChainUGen):
    @classmethod
    def new(cls, buffer, bins=0.0):
        return cls._multi_new('control', buffer, bins)


class PV_BinShift(PV_ChainUGen):
    @classmethod
    def new(cls, buffer, stretch=1.0, shift=0.0, interp=0):
        return cls._multi_new('control', buffer, stretch, shift, interp)


class PV_MagShift(PV_ChainUGen):
    @classmethod
    def new(cls, buffer, stretch=1.0, shift=0.0):
        return cls._multi_new('control', buffer, stretch, shift)


class PV_MagSquared(PV_ChainUGen):
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


class PV_PhaseShift(PV_ChainUGen):
    @classmethod
    def new(cls, buffer, shift, integrate=0):
        return cls._multi_new('control', buffer, shift, integrate)


class PV_BrickWall(PV_ChainUGen):
    @classmethod
    def new(cls, buffer, wipe=0.0):
        return cls._multi_new('control', buffer, wipe)


class PV_BinWipe(PV_ChainUGen):
    @classmethod
    def new(cls, buffer_a, buffer_b, wipe=0.0):
        return cls._multi_new('control', buffer_a, buffer_b, wipe)


class PV_MagMul(PV_ChainUGen):
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


class PV_MagDiv(PV_ChainUGen):
    @classmethod
    def new(cls, buffer_a, buffer_b, zeroed=0.0001):
        return cls._multi_new('control', buffer_a, buffer_b, zeroed)


class PV_RandComb(PV_ChainUGen):
    @classmethod
    def new(cls, buffer, wipe=0.0, trig=0.0):
        return cls._multi_new('control', buffer, wipe, trig)


class PV_RectComb(PV_ChainUGen):
    @classmethod
    def new(cls, buffer, num_teeth=0.0, phase=0.0, width=0.5):
        return cls._multi_new('control', buffer, num_teeth, phase, width)


class PV_RectComb2(PV_ChainUGen):
    @classmethod
    def new(cls, buffer_a, buffer_b, num_teeth=0.0, phase=0.0, width=0.5):
        return cls._multi_new(
            'control', buffer_a, buffer_b, num_teeth, phase, width)


class PV_RandWipe(PV_ChainUGen):
    @classmethod
    def new(cls, buffer_a, buffer_b, wipe=0.0, trig=0.0):
        return cls._multi_new('control', buffer_a, buffer_b, wipe, trig)


class PV_Diffuser(PV_ChainUGen):
    @classmethod
    def new(cls, buffer, trig=0.0):
        return cls._multi_new('control', buffer, trig)


class PV_MagFreeze(PV_ChainUGen):
    @classmethod
    def new(cls, buffer, freeze=0.0):
        return cls._multi_new('control', buffer, freeze)


class PV_BinScramble(PV_ChainUGen):
    @classmethod
    def new(cls, buffer, wipe=0.0, width=0.2, trig=0.0):
        return cls._multi_new('control', buffer, wipe, width, trig)


# Commented ugens:
# class PV_OscBank(PV_ChainUGen):
# class PV_Scope(PV_ChainUGen):
# class PV_TimeAverageScope(PV_Scope):
# class PV_MagAllTimeAverage(PV_MagSquared):
# class PV_MagOnePole(PV_ChainUGen):
# class PV_MagPeakDecay(PV_ChainUGen):
# class PV_TimeSmear(PV_MagSmear):
# class PV_LoBitEncoder(PV_ChainUGen):


# FFT2.sc

class PV_ConformalMap(PV_ChainUGen):
    # // Sick Lincoln remembers complex analysis courses.
    @classmethod
    def new(cls, buf, areal=0.0, aimag=0.0):
        return cls._multi_new('control', buf, areal, aimag)


class PV_JensenAndersen(PV_ChainUGen):
    # *** Not sure why this is ar, see _add_to_synth and prefix name.
    # // Jensen andersen inspired FFT feature detector.
    @classmethod
    def ar(cls, buf, propsc=0.25, prophfe=0.25, prophfc=0.25,
           propsf=0.25, threshold=1.0, wait_time=0.04):
        return cls._multi_new(
            'audio', buf, propsc, prophfe, prophfc,
            propsf, threshold, wait_time)


class PV_HainsworthFoote(PV_ChainUGen):
    # *** Not sure why this is ar, _add_to_synth and prefix name.
    @classmethod
    def ar(cls, buf, proph=0.0, propf=0.0, threshold=1.0, wait_time=0.04):
        return cls._multi_new(
            'audio', buf, proph, propf, threshold, wait_time)


# FFTUnpacking.sc
# // "Unpack FFT" UGens (c) 2007 Dan Stowell.
# // Magical UGens for treating FFT data as demand-rate streams.

class UnpackFFT(ugn.PseudoUGen):
    _default_rate = 'demand'

    @classmethod
    def dr(cls, chain, bufsize, frombin=0, tobin=None):
        upperlimit = bufsize // 2
        tobin = upperlimit if tobin is None else min(tobin, upperlimit)
        tobin += 1
        return utl.flatten(utl.flop([
            [Unpack1FFT(chain, bufsize, i, 0) for i in range(frombin, tobin)],
            [Unpack1FFT(chain, bufsize, i, 1) for i in range(frombin, tobin)]
        ]))


class Unpack1FFT(ugn.UGen):
    _default_rate = 'demand'

    @classmethod
    def dr(cls, chain, bufsize, binindex, which=0):
        return cls._multi_new('demand', chain, bufsize, binindex, which)


class PackFFT(PV_ChainUGen):
    # // This does the demanding, to push the data back into an FFT buffer.
    _default_rate = 'control'

    @classmethod
    def kr(cls, chain, bufsize, magsphases,
           frombin=0, tobin=None, zeroothers=0):
        tobin = tobin or bufsize // 2
        magsphases = utl.as_list(magsphases)
        return cls._multi_new(
            'control', chain, bufsize, frombin, tobin,
            zeroothers, len(magsphases), *magsphases)

    def fft_size(self):
        return self._inputs[1]
