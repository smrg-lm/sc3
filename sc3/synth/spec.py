"""Spec.sc"""

from collections import namedtuple

from ..base import builtins as bi


__all__ = ['spec']


class Warp():
    _specifier = None
    __slots__ = ('_spec',)

    def __init__(self, spec):
        self._spec = spec

    @property
    def specifier(self):
        return type(self)._specifier

    def map(self, value):
        return value

    def unmap(self, value):
        return value

    def __eq__(self, other):
        if type(self) == type(other):
            return True
        else:
            return False

    def __hash__(self):
        return hash(type(self))


class LinearWarp(Warp):
    _specifier = 'lin'

    def map(self, value):
        return value * self._spec.range + self._spec.minval

    def unmap(self, value):
        return (value - self._spec.minval) / self._spec.range


class ExponentialWarp(Warp):
    # // Both minval and maxval must be non zero and have the same sign.

    _specifier = 'exp'

    def map(self, value):
        return self._spec.ratio ** value * self._spec.minval

    def unmap(self, value):
        return bi.log(value / self._spec.minval) / bi.log(self._spec.ratio)


class CurveWarp(Warp):
    __slots__ = ('_spec', '_curve', '_a', '_b', '_grow')

    def __new__(cls, spec, curve):
        # // Prevent math blow up.
        if abs(curve) < 0.001:
            return LinearWarp(spec)
        return super().__new__(cls)

    def __init__(self, spec, curve):
        self._spec = spec
        if curve > -0.001 and curve < 0.001:
            self._curve = 0.001
        else:
            self._curve = curve
        self._grow = bi.exp(self._curve)
        self._a = spec.range / (1.0 - self._grow)
        self._b = spec.minval + self._a

    @property
    def specifier(self):
        return self._curve

    @property
    def curve(self):
        return self._curve

    def map(self, value):
        return self._b - self._a * pow(self._grow, value)

    def unmap(self, value):
        return bi.log((self._b - value) / self._a) / self._curve

    def __eq__(self, other):
        if type(self) == type(other):
            return self.curve == other.curve
        else:
            return False

    def __hash__(self):
        return hash(type(self))


class CosineWarp(LinearWarp):
    _specifier = 'cos'

    def map(self, value):
        return super().map(0.5 - bi.cos(bi.pi * value) * 0.5)

    def unmap(self, value):
        return bi.acos(1.0 - super().unmap(value) * 2.0) / bi.pi


class SineWarp(LinearWarp):
    _specifier = 'sin'

    def map(self, value):
        return super().map(bi.sin(bi.pi2 * value))

    def unmap(self, value):
        return bi.asin(super().unmap(value)) / bi.pi2


class AmpWarp(Warp):
    _specifier = 'amp'

    def map(self, value):
        if self._spec.range >= 0:
            return value ** 2 * self._spec.range + self._spec.minval
        else:
            # // The formula can be reduced to (2*v) - v.squared
			# // but the 2 subtractions would be faster.
            return (1 - (1 - value) ** 2) * self._spec.range + self._spec.minval

    def unmap(self, value):
        if self._spec.range >= 0:
            return bi.sqrt((value - self._spec.minval) / self._spec.range)
        else:
            return (
                1 - bi.sqrt(1 - (value - self._spec.minval) / self._spec.range))


class DbWarp(Warp):
    _specifier = 'db'

    def map(self, value):
        dbamp = bi.dbamp
        range = dbamp(self._spec.maxval) - dbamp(self._spec.minval)
        if self._spec.range >= 0:
            return bi.ampdb(value ** 2 * range + dbamp(self._spec.minval))
        else:
            return bi.ampdb(
                (1 - (1 - value) ** 2) * range + dbamp(self._spec.minval))

    def unmap(self, value):
        dbamp = bi.dbamp
        if self._spec.range >= 0:
            return bi.sqrt(
                (dbamp(value) - dbamp(self._spec.minval)) /
                (dbamp(self._spec.maxval) - dbamp(self._spec.minval)))
        else:
            return 1 - bi.sqrt(
                1 - (dbamp(value) - dbamp(self._spec.minval)) /
                (dbamp(self._spec.maxval) - dbamp(self._spec.minval)))


# Warp *initClass

_WARPS = {
    LinearWarp._specifier: LinearWarp,
    ExponentialWarp._specifier: ExponentialWarp,
    SineWarp._specifier: SineWarp,
    CosineWarp._specifier: CosineWarp,
    AmpWarp._specifier: AmpWarp,
    DbWarp._specifier: DbWarp
    # // CurveWarp is specified by a number.
}

def _as_warp(warp, spec):
    if isinstance(warp, str):
        try:
            return _WARPS[warp](spec)
        except KeyError:
            raise ValueError(f"invalid warp '{warp}'")
    elif isinstance(warp, (int, float)):
        return CurveWarp(spec, warp)
    elif isinstance(warp, Warp):
        return warp
    else:
        raise TypeError(f"can't create a warp from {type(warp).__name__}")


class ControlSpec():
    def __init__(self, minval=0.0, maxval=1.0, warp='lin',
                 step=None, default=None, units=None):  #, grid=None):
        self._minval = minval
        self._maxval = maxval
        self._step = 0.0 if step is None else step
        self._default = minval if default is None else default
        self._units = '' if units is None else units
        self._range = maxval - minval
        self._ratio = maxval / minval if minval != 0 else float('inf')
        self._cliplo = min(minval, maxval)
        self._cliphi = max(minval, maxval)
        self._warp = _as_warp(warp, self)
        # self.grid = grid
        self._hash = hash((type(self), *vars(self).values()))

    # newFrom
    # copy

    @property
    def minval(self):
        return self._minval

    @property
    def maxval(self):
        return self._maxval

    @property
    def warp(self):
        return self._warp

    @property
    def step(self):
        return self._step

    @property
    def default(self):
        return self._default

    @property
    def units(self):
        return self._units

    @property
    def range(self):
        return self._range

    @property
    def ratio(self):
        return self._ratio

    def map(self, value):
        # // Maps a value from [0..1] to spec range.
        return self._warp.map(bi.round(bi.clip(value, 0.0, 1.0), self._step))

    def unmap(self, value):
        # // Maps a value from spec range to [0..1].
        return self._warp.unmap(
            bi.clip(bi.round(value, self._step), self._cliplo, self._cliphi))

    # GUI specific methods:
    # constrain
    # guessNumberStep
    # grid
    # looseRange
    # normalize
    # roundRange
    # gridValues
    # zoom
    # shift
    # setFrom

    def __eq__(self, other):
        if type(self) == type(other):
            return vars(self) == vars(other)
        else:
            return False

    def __hash__(self):
        return self._hash

    def __repr__(self):
        return (
            f"{type(self).__name__}({self._minval}, {self._maxval}, "
            f"{repr(self._warp.specifier)}, {self._step}, {self._default}, "
            f"'{self._units}')")


# ControlSpec *initClass

_SPECS = {
    'unipolar': ControlSpec(0, 1),
    'bipolar': ControlSpec(-1, 1, default=0),

    'freq': ControlSpec(20, 20000, 'exp', 0, 440, units='Hz'),
    'lofreq': ControlSpec(0.1, 100, 'exp', 0, 6, units='Hz'),
    'midfreq': ControlSpec(25, 4200, 'exp', 0, 440, units='Hz'),
    'widefreq': ControlSpec(0.1, 20000, 'exp', 0, 440, units='Hz'),
    'phase': ControlSpec(0, bi.twopi),
    'rq': ControlSpec(0.001, 2, 'exp', 0, 0.707),

    'midi': ControlSpec(0, 127, default=64),
    'midinote': ControlSpec(0, 127, default=60),
    'midivelocity': ControlSpec(1, 127, default=64),

    'db': ControlSpec(bi.ampdb(0), bi.ampdb(1), 'db', units='dB'),
    'amp': ControlSpec(0, 1, 'amp', 0, 0),
    'boostcut': ControlSpec(-20, 20, units='dB', default=0),

    'pan': ControlSpec(-1, 1, default=0),
    'detune': ControlSpec(-20, 20, default=0, units='Hz'),
    'rate': ControlSpec(0.125, 8, 'exp', 0, 1),
    'beats': ControlSpec(0, 20, units='Hz'),

    'delay': ControlSpec(0.0001, 1, 'exp', 0, 0.3, units='secs')
}

def spec(spc):
    if isinstance(spc, ControlSpec):
        return spc
    elif isinstance(spc, str):
        try:
            return _SPECS[spc]
        except KeyError:
            raise ValueError(f"invalid spec '{spc}'") from None
    elif isinstance(spc, (int, float)):
        return ControlSpec(warp=spc)
    elif isinstance(spc, (list, tuple)):
        return ControlSpec(*spc)
    else:
        raise TypeError(f"can't create a spec from {type(spc).__name__}")

# add_spec/remove_spec might not be a good idea.


### Metadata support ###

def key_encoder(dct):
    # Receives a dict of ControlSpecs, the 'specs' key of SynthDef
    # metadata and return JSON serializable Python objects.
    return {
        k: [v._minval, v._maxval, v._warp.specifier,
            v._step, v._default, v._units]
        for k, v in dct.items()}

def key_decoder(dct):
    # Receives a dict of lists (from a JSON file) for the 'specs'
    # key of SynthDef and return a dict of ControlSpecs.
    return {k: spec(v) for k, v in dct.items()}

SpecCodec = namedtuple('SpecCodec', ['key', 'encoder', 'decoder'])
spec_codec = SpecCodec('specs', key_encoder, key_decoder)
