"""FFT.sc"""

from .. import ugen as ugn
from .. import _global as _gl
from . import fftunpacking as ffu


# // fft uses a local buffer for holding the buffered audio. wintypes are
# // defined in the C++ source. 0 is default, Welch; 1 is Hann; -1 is rect.


class FFT(ffu.PV_ChainUGen):
    ...


class IFFT(ugn.WidthFirstUGen):
    ...


class PV_MagAbove(ffu.PV_ChainUGen):
    ...


class PV_MagBelow(PV_MagAbove):
    pass


class PV_MagClip(PV_MagAbove):
    pass


class PV_LocalMax(PV_MagAbove):
    pass


class PV_MagSmear(ffu.PV_ChainUGen):
    ...


class PV_BinShift(ffu.PV_ChainUGen):
    ...


class PV_MagShift(ffu.PV_ChainUGen):
    ...


class PV_MagSquared(ffu.PV_ChainUGen):
    ...


class PV_MagNoise(PV_MagSquared):
    pass


class PV_PhaseShift90(PV_MagSquared):
    pass


class PV_PhaseShift270(PV_MagSquared):
    pass


class PV_Conj(PV_MagSquared):
    pass


class PV_PhaseShift(ffu.PV_ChainUGen):
    ...


class PV_BrickWall(ffu.PV_ChainUGen):
    ...


class PV_BinWipe(ffu.PV_ChainUGen):
    ...


class PV_MagMul(ffu.PV_ChainUGen):
    ...


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
    ...


class PV_RandComb(ffu.PV_ChainUGen):
    ...


class PV_RectComb(ffu.PV_ChainUGen):
    ...


class PV_RectComb2(ffu.PV_ChainUGen):
    ...


class PV_RandWipe(ffu.PV_ChainUGen):
    ...


class PV_Diffuser(ffu.PV_ChainUGen):
    ...


class PV_MagFreeze(ffu.PV_ChainUGen):
    ...


class PV_BinScramble(ffu.PV_ChainUGen):
    ...


class FFTTrigger(ffu.PV_ChainUGen):
    ...


# Commented ugens:
# class PV_OscBank(ffu.PV_ChainUGen):
# class PV_Scope(ffu.PV_ChainUGen):
# class PV_TimeAverageScope(PV_Scope):
# class PV_MagAllTimeAverage(PV_MagSquared):
# class PV_MagOnePole(ffu.PV_ChainUGen):
# class PV_MagPeakDecay(ffu.PV_ChainUGen):
# class PV_TimeSmear(PV_MagSmear):
# class PV_LoBitEncoder(ffu.PV_ChainUGen):
