"""Osc.sc"""

from ...base import builtins as bi
from .. import ugen as ugn
from .. import _graphparam as gpp
from . import noise as nse
from . import pan


class Osc(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, bufnum, freq=440.0, phase=0.0):
        return cls._multi_new('audio', bufnum, freq, phase)

    @classmethod
    def kr(cls, bufnum, freq=440.0, phase=0.0):
        return cls._multi_new('control', bufnum, freq, phase)


class SinOsc(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, phase=0.0):
        return cls._multi_new('audio', freq, phase)

    @classmethod
    def kr(cls, freq=440.0, phase=0.0):
        return cls._multi_new('control', freq, phase)


class SinOscFB(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, feedback=0.0):
        return cls._multi_new('audio', freq, feedback)

    @classmethod
    def kr(cls, freq=440.0, feedback=0.0):
        return cls._multi_new('control', freq, feedback)


class OscN(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, bufnum, freq=440.0, phase=0.0):
        return cls._multi_new('audio', bufnum, freq, phase)

    @classmethod
    def kr(cls, bufnum, freq=440.0, phase=0.0):
        return cls._multi_new('control', bufnum, freq, phase)


class VOsc(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, bufpos, freq=440.0, phase=0.0):
        return cls._multi_new('audio', bufpos, freq, phase)

    @classmethod
    def kr(cls, bufpos, freq=440.0, phase=0.0):
        return cls._multi_new('control', bufpos, freq, phase)


class VOsc3(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, bufpos, freq1=110.0, freq2=220.0, freq3=440.0):
        return cls._multi_new('audio', bufpos, freq1, freq2, freq3)

    @classmethod
    def kr(cls, bufpos, freq1=110.0, freq2=220.0, freq3=440.0):
        return cls._multi_new('control', bufpos, freq1, freq2, freq3)


class COsc(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, bufnum, freq=440.0, beats=0.5):
        return cls._multi_new('audio', bufnum, freq, beats)

    @classmethod
    def kr(cls, bufnum, freq=440.0, beats=0.5):
        return cls._multi_new('control', bufnum, freq, beats)


class Formant(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, fundfreq=440.0, formfreq=1760.0, bwfreq=880.0):
        return cls._multi_new('audio', fundfreq, formfreq, bwfreq)


class LFSaw(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, iphase=0.0):
        return cls._multi_new('audio', freq, iphase)

    @classmethod
    def kr(cls, freq=440.0, iphase=0.0):
        return cls._multi_new('control', freq, iphase)


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


class LFPulse(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, iphase=0.0, width=0.5):
        return cls._multi_new('audio', freq, iphase, width)

    @classmethod
    def kr(cls, freq=440.0, iphase=0.0, width=0.5):
        return cls._multi_new('control', freq, iphase, width)

    @classmethod
    def signal_range(cls):  # override
        return 'unipolar'


class VarSaw(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, iphase=0.0, width=0.5):
        return cls._multi_new('audio', freq, iphase, width)

    @classmethod
    def kr(cls, freq=440.0, iphase=0.0, width=0.5):
        return cls._multi_new('control', freq, iphase, width)


class Impulse(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, phase=0.0):
        return cls._multi_new('audio', freq, phase)

    @classmethod
    def kr(cls, freq=440.0, phase=0.0):
        return cls._multi_new('control', freq, phase)

    @classmethod
    def signal_range(cls):  # override
        return 'unipolar'


class SyncSaw(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, sync_freq=440.0, saw_freq=440.0):
        return cls._multi_new('audio', sync_freq, saw_freq)

    @classmethod
    def kr(cls, sync_freq=440.0, saw_freq=440.0):
        return cls._multi_new('control', sync_freq, saw_freq)


# TPulse


class Index(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, bufnum, input=0.0):
        return cls._multi_new('audio', bufnum, input)

    @classmethod
    def kr(cls, bufnum, input=0.0):
        return cls._multi_new('control', bufnum, input)


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


class DegreeToKey(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, bufnum, input=0.0, octave=12.0):
        return cls._multi_new('audio', bufnum, input, octave)

    @classmethod
    def kr(cls, bufnum, input=0.0, octave=12.0):
        return cls._multi_new('control', bufnum, input, octave)


class Select(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, which, lst):
        return cls._multi_new('audio', which, *lst)

    @classmethod
    def kr(cls, which, lst):
        return cls._multi_new('control', which, *lst)

    def _check_inputs(self):
        if self.rate == 'audio':
            for i in range(1, len(self.inputs)):
                if gpp.ugen_param(self.inputs[i])._as_ugen_rate() != 'audio':
                    return f'input was not audio rate: {self.inputs[i]}'
        return self._check_valid_inputs()


# Pseudo UGens don't return instances of themselves but of another subclass
# of UGen, ChannelList or (maybe) optimizations (UGenParameter scalar types).

class SelectX(ugn.PseudoUGen):
    @classmethod
    def _new1(cls, rate, which, lst, wrap):  # wrap was never implemented (needs to be a proper UGen)
        selector = cls._method_selector_for_rate(rate)
        return getattr(cls._crossfade_class(), selector)(
            getattr(Select, selector)(bi.round(which, 2), lst),
            getattr(Select, selector)(bi.trunc(which, 2) + 1, lst),
            bi.fold2(which * 2 - 1, 1))

    @classmethod
    def ar(cls, which, lst, wrap=1):
        return cls._new1('audio', which, lst, wrap)

    @classmethod
    def kr(cls, which, lst, wrap=1):
        return cls._new1('control', which, lst, wrap)

    @classmethod
    def _method_selector_for_rate(cls, rate):  # FIXME: API, same in LinLin
        if rate == 'audio':
            return 'ar'
        elif rate == 'control':
            return 'kr'
        raise AttributeError(f'{cls.__name__} has no {rate} rate constructor')

    @classmethod
    def _crossfade_class(cls):
        return pan.XFade2


class LinSelectX(SelectX):
    @classmethod
    def _crossfade_class(cls):
        return pan.LinXFade2


class SelectXFocus(ugn.PseudoUGen):
    @classmethod
    def new(cls, which, lst, focus=1, wrap=False):
        if wrap:
            return ugn.Mix.new(
                [bi.max(1 - (bi.moddif(which, i, len(lst)) * focus), 0) * input
                 for i, input in enumerate(lst)])
        else:
            return ugn.Mix.new(
                [bi.max(1 - (bi.absdif(which, i) * focus), 0) * input
                 for i, input in enumerate(lst)])

    @classmethod
    def ar(cls, which, lst, focus=1, wrap=False):
        return self.new(which, array, focus, wrap)  # ar/kr are fake rate constructors.

    @classmethod
    def kr(cls, which, lst, focus=1, wrap=False):
        return self.new(which, array, focus, wrap)


class Vibrato(ugn.UGen, ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, rate=6, depth=0.02, delay=0.0, onset=0.0,
           rate_variation=0.04, depth_variation=0.1, iphase=0.0, trig=0.0):
        return cls._multi_new('audio', freq, rate, depth, delay, onset,
                              rate_variation, depth_variation, iphase, trig)

    @classmethod
    def kr(cls, freq=440.0, rate=6, depth=0.02, delay=0.0, onset=0.0,
           rate_variation=0.04, depth_variation=0.1, iphase=0.0, trig=0.0):
        return cls._multi_new('control', freq, rate, depth, delay, onset,
                              rate_variation, depth_variation, iphase, trig)


class TChoose(ugn.PseudoUGen):
    @classmethod
    def ar(cls, trig, lst):
        self._check_empty_list(lst)
        return Select.ar(nse.TIRand.ar(0, len(lst) - 1, trig), lst)

    @classmethod
    def kr(cls, trig, lst):
        self._check_empty_list(lst)
        return Select.kr(nse.TIRand.kr(0, len(lst) - 1, trig), lst)

    def _check_empty_list(self, lst):
        if len(lst) == 0:
            raise ValueError("TChoose: lst can't be empty")


class TWChoose(ugn.PseudoUGen):
    @classmethod
    def ar(cls, trig, lst, weights, normalize=0):
        return Select.ar(nse.TWindex.ar(trig, weights, normalize), lst)

    @classmethod
    def kr(cls, trig, lst, weights, normalize=0):
        return Select.kr(nse.TWindex.kr(trig, weights, normalize), lst)
