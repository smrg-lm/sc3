"""
Non-linear Dynamic Sound Generators
-----------------------------------

Lance Putnam 2004 | lance@uwalumni.com

This is a set of iterative functions and differential equations that
are known to exhibit chaotic behavior.  Internal calculations are
done with 64-bit words to ensure greater accuracy.

The name of the function is followed by one of N (none), L (linear),
or C (cubic). These represent the interpolation method used between
function iterations.
"""

from .. import ugen as ugn
from . import infougens as ifu


class ChaosGen(ugn.UGen):
    '''Base class for chaos generators.'''

    @staticmethod
    def _check_freq(freq):
        return ifu.SampleRate.ir() * 0.5 if freq is None else freq


### General Quadratic Map ###

class QuadN(ChaosGen):
    '''
    x1 = a * x0 ** 2 + b * x0 + c
    '''

    @classmethod
    def ar(cls, freq=None, a=1, b=-1, c=-0.75, xi=0):
        freq = cls._check_freq(freq)
        return cls._multi_new('audio', freq, a, b, c, xi)


class QuadL(QuadN):
    pass


class QuadC(QuadN):
    pass


### Cusp Map ###

class CuspN(ChaosGen):
    '''
    x1 = a - b * sqrt(abs(x0))
    '''

    @classmethod
    def ar(cls, freq=None, a=1, b=1.9, xi=0):
        freq = cls._check_freq(freq)
        return cls._multi_new('audio', freq, a, b, xi)


class CuspL(CuspN):
    pass


### Gingerbreadman Map ###

class GbmanN(ChaosGen):
    '''
    x1 = 1 - y0 + abs(x0)
    y1 = x0
    '''

    @classmethod
    def ar(cls, freq=None, xi=1.2, yi=2.1):
        freq = cls._check_freq(freq)
        return cls._multi_new('audio', freq, xi, yi)


class GbmanL(GbmanN):
    pass


### Henon Map ###

class HenonN(ChaosGen):
    '''
    x2 = 1 - a * (x1 ** 2) + b * x0
    '''

    @classmethod
    def ar(cls, freq=None, a=1.4, b=0.3, x0=0, x1=0):
        freq = cls._check_freq(freq)
        return cls._multi_new('audio', freq, a, b, x0, x1)


class HenonL(HenonN):
    pass


class HenonC(HenonN):
    pass


### Latoocarfian ###

class LatoocarfianN(ChaosGen):
    '''
    x1 = sin(b * y0) + c * sin(b * x0)
    y1 = sin(a * x0) + d * sin(a * y0)
    '''

    @classmethod
    def ar(cls, freq=None, a=1, b=3, c=0.5, d=0.5, xi=0.5, yi=0.5):
        freq = cls._check_freq(freq)
        return cls._multi_new('audio', freq, a, b, c, d, xi, yi)


class LatoocarfianL(LatoocarfianN):
    pass


class LatoocarfianC(LatoocarfianN):
    pass


### Linear Congruential ###

class LinCongN(ChaosGen):
    '''
    x1 = (a * x0 + c) % m
    '''

    @classmethod
    def ar(cls, freq=None, a=1.1, c=0.13, m=1.0, xi=0):
        freq = cls._check_freq(freq)
        return cls._multi_new('audio', freq, a, c, m, xi)


class LinCongL(LinCongN):
    pass


class LinCongC(LinCongN):
    pass


### Standard Map ###

class StandardN(ChaosGen):
    '''
    x1 = (x0 + y1) % (2 * pi)
    y1 = (y0 + k * sin(x0)) % (2 * pi)
    '''

    @classmethod
    def ar(cls, freq=None, k=1.0, xi=0.5, yi=0):
        freq = cls._check_freq(freq)
        return cls._multi_new('audio', freq, k, xi, yi)


class StandardL(StandardN):
    pass


### Feedback Sine with Linear Congruential Phase Indexing ###

class FBSineN(ChaosGen):
    '''
    x1 = sin(im * y0 + fb * x0)
    y1 = (a * y0 + c) % (2 * pi)
    '''

    @classmethod
    def ar(cls, freq=None, im=1, fb=0.1, a=1.1, c=0.5, xi=0.1, yi=0.1):
        freq = cls._check_freq(freq)
        return cls._multi_new('audio', freq, im, fb, a, c, xi, yi)


class FBSineL(FBSineN):
    pass


class FBSineC(FBSineN):
    pass


### ODEs ###

class LorenzL(ChaosGen):
    '''LorenzL(freq=None, s=10, r=28, b=2.667, h=0.05, xi=0.1, yi=0, zi=0)

    Lorenz chaotic generator.

    Rates
    -----
    * ar (default)

    Parameters
    ----------
    freq:
        Iteration frequency in Hertz, defaults to SampleRate.ir() / 2
    s:
        Equation variable, defaults to 10
    r:
        Equation variable, defaults to 28
    b:
        Equation variable, defaults to 2.667
    h:
        Integration time step, defaults to 0.05
    xi:
        Initial value of x, defaults to 0.1
    yi:
        Initial value of y, defaults to 0
    zi:
        Initial value of z, defaults to 0

    Notes
    -----
    A strange attractor discovered by Edward N. Lorenz while
    studying mathematical models of the atmosphere. The system
    is composed of three ordinary differential equations:

    ::

      x' = s * (y - x)
      y' = x * (r - z) - y
      z' = x * y - b * z

    The time step amount h determines the rate at which the ODE
    is evaluated. Higher values will increase the rate, but cause
    more instability. A safe choice is the default amount of 0.05.
    '''

    @classmethod
    def ar(cls, freq=None, s=10, r=28, b=2.667, h=0.05, xi=0.1, yi=0, zi=0):
        freq = cls._check_freq(freq)
        return cls._multi_new('audio', freq, s, r, b, h, xi, yi, zi)
