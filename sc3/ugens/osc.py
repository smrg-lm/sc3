"""Osc.sc"""

from .. import ugen as ugn
from .. import builtins as bi


class Osc(ugn.PureUGen):
    @classmethod
    def ar(cls, bufnum, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', bufnum, freq, phase).madd(mul, add)

    @classmethod
    def kr(cls, bufnum, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('control', bufnum, freq, phase).madd(mul, add)


class SinOsc(ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', freq, phase).madd(mul, add)

    @classmethod
    def kr(cls, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('control', freq, phase).madd(mul, add)


class SinOscFB(ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, feedback=0.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', freq, feedback).madd(mul, add)

    @classmethod
    def kr(cls, freq=440.0, feedback=0.0, mul=1.0, add=0.0):
        return cls._multi_new('control', freq, feedback).madd(mul, add)


class OscN(ugn.PureUGen):
    @classmethod
    def ar(cls, bufnum, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', bufnum, freq, phase).madd(mul, add)

    @classmethod
    def kr(cls, bufnum, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('control', bufnum, freq, phase).madd(mul, add)


class VOsc(ugn.PureUGen):
    @classmethod
    def ar(cls, bufpos, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', bufpos, freq, phase).madd(mul, add)

    @classmethod
    def kr(cls, bufpos, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('control', bufpos, freq, phase).madd(mul, add)


class VOsc3(ugn.PureUGen):
    @classmethod
    def ar(cls, bufpos, freq1=110.0, freq2=220.0, freq3=440.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', bufpos, freq1, freq2, freq3).madd(mul, add)

    @classmethod
    def kr(cls, bufpos, freq1=110.0, freq2=220.0, freq3=440.0, mul=1.0, add=0.0):
        return cls._multi_new('control', bufpos, freq1, freq2, freq3).madd(mul, add)


class COsc(ugn.PureUGen):
    @classmethod
    def ar(cls, bufnum, freq=440.0, beats=0.5, mul=1.0, add=0.0):
        return cls._multi_new('audio', bufnum, freq, beats).madd(mul, add)

    @classmethod
    def kr(cls, bufnum, freq=440.0, beats=0.5, mul=1.0, add=0.0):
        return cls._multi_new('control', bufnum, freq, beats).madd(mul, add)


class Formant(ugn.PureUGen):
    @classmethod
    def ar(cls, fundfreq=440.0, formfreq=1760.0, bwfreq=880.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', fundfreq, formfreq, bwfreq).madd(mul, add)


class LFSaw(ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, iphase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', freq, iphase).madd(mul, add)

    @classmethod
    def kr(cls, freq=440.0, iphase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('control', freq, iphase).madd(mul, add)


class LFPar(LFSaw):
    pass


class LFCub(LFSaw):
    pass


class LFTri(LFSaw):
    pass


class LFGauss(ugn.UGen):
    @classmethod
    def ar(cls, duration=1, width=0.1, iphase=0.0, loop=1, done_action=0):
        return cls._multi_new('audio', duration, width, iphase, loop, done_action)

    @classmethod
    def kr(cls, duration=1, width=0.1, iphase=0.0, loop=1, done_action=0):
        return cls._multi_new('control', duration, width, iphase, loop, done_action)

    @property
    def _minval(self):
        width = self.inputs[1]
        return bi.exp(1.0 / (-2.0 * bi.squared(width)))

    def range(self, min=0, max=1):
        return self.linlin(self._minval, 1, min, max)


class LFPulse(ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, iphase=0.0, width=0.5, mul=1.0, add=0.0):
        return cls._multi_new('audio', freq, iphase, width).madd(mul, add)

    @classmethod
    def kr(cls, freq=440.0, iphase=0.0, width=0.5, mul=1.0, add=0.0):
        return cls._multi_new('control', freq, iphase, width).madd(mul, add)

    @classmethod
    def signal_range(cls):
        return 'unipolar'


class VarSaw(ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, iphase=0.0, width=0.5, mul=1.0, add=0.0):
        return cls._multi_new('audio', freq, iphase, width).madd(mul, add)

    @classmethod
    def kr(cls, freq=440.0, iphase=0.0, width=0.5, mul=1.0, add=0.0):
        return cls._multi_new('control', freq, iphase, width).madd(mul, add)


class Impulse(ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', freq, phase).madd(mul, add)

    @classmethod
    def kr(cls, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('control', freq, phase).madd(mul, add)

    @classmethod
    def signal_range(self):
        return 'unipolar'


class SyncSaw(ugn.PureUGen):
    @classmethod
    def ar(cls, sync_freq=440.0, saw_freq=440.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', sync_freq, saw_freq).madd(mul, add)

    @classmethod
    def kr(cls, sync_freq=440.0, saw_freq=440.0, mul=1.0, add=0.0):
        return cls._multi_new('control', sync_freq, saw_freq).madd(mul, add)


# TPulse


class Index(ugn.PureUGen):
    @classmethod
    def ar(cls, bufnum, input=0.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', bufnum, input).madd(mul, add)

    @classmethod
    def kr(cls, bufnum, input=0.0, mul=1.0, add=0.0):
        return cls._multi_new('control', bufnum, input).madd(mul, add)


class WrapIndex(Index):
    pass


class IndexInBetween(Index):
    pass


class DetectIndex(Index):
    pass


class Shaper(Index):
    pass


class IndexL(Index):
    pass


class DegreeToKey(ugn.PureUGen):
    ...


class Select(ugn.PureUGen):
    ...


class SelectX():  # Pseudo UGen.
    ...


class LinSelectX(SelectX):
    ...


class SelectXFocus():  # Pseudo UGen.
    ...


class Vibrato(ugn.PureUGen):
    ...


class TChoose(): # Pseudo UGen.
    ...


class TWChoose(): # Pseudo UGen.
    ...
