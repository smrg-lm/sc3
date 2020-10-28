"""Noise.sc"""

from .. import ugen as ugn


class RandSeed(ugn.WidthFirstUGen):
    _default_rate = 'scalar'

    @classmethod
    def ar(cls, trig=0.0, seed=56789):
        cls._multi_new('audio', trig, seed)
        # return 0.0  # // RandSeed has no output.

    @classmethod
    def kr(cls, trig=0.0, seed=56789):
        cls._multi_new('control', trig, seed)
        # return 0.0  # // RandSeed has no output.

    @classmethod
    def ir(cls, trig=0.0, seed=56789):
        cls._multi_new('scalar', trig, seed)
        # return 0.0  # // RandSeed has no output.


class RandID(ugn.WidthFirstUGen):
    _default_rate = 'scalar'

    # // Choose which random number generator to use for this synth.
    @classmethod
    def kr(cls, id=0):
        cls._multi_new('control', id)
        # return 0.0  # // RandID has no output.

    @classmethod
    def ir(cls, id=0):
        cls._multi_new('scalar', id)
        # return 0.0  # // RandID has no output.


class Rand(ugn.UGen):
    # // Uniform distribution.
    _default_rate = None

    @classmethod
    def new(cls, lo=0.0, hi=1.0):
        return cls._multi_new('scalar', lo, hi)


class IRand(ugn.UGen):
    # // Uniform distribution of integers.
    _default_rate = None

    @classmethod
    def new(cls, lo=0, hi=127):
        return cls._multi_new('scalar', lo, hi)


class TRand(ugn.UGen):
    # // Uniform distribution.
    @classmethod
    def ar(cls, lo=0.0, hi=1.0, trig=0.0):
        return cls._multi_new('audio', lo, hi, trig)

    @classmethod
    def kr(cls, lo=0.0, hi=1.0, trig=0.0):
        return cls._multi_new('control', lo, hi, trig)


class TIRand(ugn.UGen):
    # // Uniform distribution of integers.
    @classmethod
    def ar(cls, lo=0, hi=127, trig=0.0):
        return cls._multi_new('audio', lo, hi, trig)

    @classmethod
    def kr(cls, lo=0, hi=127, trig=0.0):
        return cls._multi_new('control', lo, hi, trig)


class LinRand(ugn.UGen):
    _default_rate = None

    # // Linear distribution.
    # // if minmax <= 0 then skewed towards lo.
    # // else skewed towards hi.
    @classmethod
    def new(cls, lo=0.0, hi=1.0, minmax=0):
        return cls._multi_new('scalar', lo, hi, minmax)


class NRand(ugn.UGen):
    # // Sum of N uniform distributions.
    # // n = 1 : uniform distribution - same as Rand
    # // n = 2 : triangular distribution
    # // n = 3 : smooth hump
    # // as n increases, distribution converges towards gaussian.
    _default_rate = None

    @classmethod
    def new(cls, lo=0.0, hi=0.0, n=0):
        return cls._multi_new('scalar', lo, hi, n)


class ExpRand(ugn.UGen):
    # // Exponential distribution.
    _default_rate = None

    @classmethod
    def new(cls, lo=0.01, hi=1.0):
        return cls._multi_new('scalar', lo, hi)


class TExpRand(ugn.UGen):
    # // Exponential distribution.  # NOTE: sclang sais 'uniform'.
    @classmethod
    def ar(cls, lo=0.01, hi=1.0, trig=0.0):
        return cls._multi_new('audio', lo, hi, trig)

    @classmethod
    def kr(cls, lo=0.01, hi=1.0, trig=0.0):
        return cls._multi_new('control', lo, hi, trig)


class CoinGate(ugn.UGen):
    @classmethod
    def ar(cls, prob, input):
        return cls._multi_new('audio', prob, input)

    @classmethod
    def kr(cls, prob, input):
        return cls._multi_new('control', prob, input)


class TWindex(ugn.UGen):
    @classmethod
    def ar(cls, input, lst, normalize=0):
        return cls._multi_new('audio', input, normalize, *lst)

    @classmethod
    def kr(cls, input, lst, normalize=0):
        return cls._multi_new('control', input, normalize, *lst)


class WhiteNoise(ugn.UGen):
    @classmethod
    def ar(cls):
        return cls._multi_new('audio')

    @classmethod
    def kr(cls):
        return cls._multi_new('control')


class BrownNoise(WhiteNoise):
    pass


class PinkNoise(WhiteNoise):
    pass


class ClipNoise(WhiteNoise):
    pass


class GrayNoise(WhiteNoise):
    pass


# NoahNoise, commented ugen.


class Crackle(ugn.UGen):
    @classmethod
    def ar(cls, chaos_param=1.5):
        return cls._multi_new('audio', chaos_param)

    @classmethod
    def kr(cls, chaos_param=1.5):
        return cls._multi_new('control', chaos_param)


class Logistic(ugn.UGen):
    @classmethod
    def ar(cls, chaos_param=3.0, freq=1000.0, init=0.5):
        return cls._multi_new('audio', chaos_param, freq, init)

    @classmethod
    def kr(cls, chaos_param=3.0, freq=1000.0, init=0.5):
        return cls._multi_new('control', chaos_param, freq, init)


# Rossler, commented ugen.


class LFNoise0(ugn.UGen):
    @classmethod
    def ar(cls, freq=500.0):
        return cls._multi_new('audio', freq)

    @classmethod
    def kr(cls, freq=500.0):
        return cls._multi_new('control', freq)


class LFNoise1(LFNoise0):
    pass


class LFNoise2(LFNoise0):
    pass


class LFClipNoise(LFNoise0):
    pass


class LFDNoise0(LFNoise0):
    pass


class LFDNoise1(LFNoise0):
    pass


class LFDNoise3(LFNoise0):
    pass


class LFDClipNoise(LFNoise0):
    pass


class Hasher(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0):
        return cls._multi_new('audio', input)

    @classmethod
    def kr(cls, input=0.0):
        return cls._multi_new('control', input)

    def _check_inputs(self):
        if self.rate == 'audio':
            return self._check_sr_as_first_input()
        else:
            return self._check_valid_inputs()


class MantissaMask(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, bits=3):
        return cls._multi_new('audio', input, bits)

    @classmethod
    def kr(cls, input=0.0, bits=3):
        return cls._multi_new('control', input, bits)


class Dust(ugn.UGen):
    @classmethod
    def ar(cls, density=0.0):
        return cls._multi_new('audio', density)

    @classmethod
    def kr(cls, density=0.0):
        return cls._multi_new('control', density)

    @classmethod
    def signal_range(cls):  # override
        return 'unipolar'


class Dust2(ugn.UGen):
    @classmethod
    def ar(cls, density=0.0):
        return cls._multi_new('audio', density)

    @classmethod
    def kr(cls, density=0.0):
        return cls._multi_new('control', density)
