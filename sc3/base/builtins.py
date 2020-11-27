"""SC_InlineUnaryOp.h, SC_InlineBinaryOp.h"""

# Note: Functions in this module are quite slow. They are Python
# implementations of sc server opcodes to obtain special index symbols and
# conform AbstractObject interface. A few are also wrappers to match
# sclang's behaviour too (e.g. mod and random functions). They will need to be
# optimized along with events, patterns and streams. However, when running the
# library on pypy all unoptimized code at least matches sclang.

import math
import builtins

from . import classlibrary as clb


clb.ClassLibrary.late_imports(__name__, ('sc3.base.main', '_libsc3'))


# Module Constants
# /include/plugin_interface/SC_Constants.h
pi = math.acos(-1.)
pi2 = pi * .5
pi32 = pi * 1.5
twopi = pi * 2.
rtwopi = 1. / twopi
log001 = math.log(0.001)
log01 = math.log(0.01)
log1 = math.log(0.1)
rlog2 = 1. / math.log(2.)
sqrt2 = math.sqrt(2.)
rsqrt2 = 1. / sqrt2


# There is a thing, some operators are unary or binary with argument, some are
# math functions with arguments, the problem is that when declared as binops
# they will use rcompose but unops and narops will not. That creates a possible
# behaviour inconsistency problem.
class scbuiltin():
    # def __new__(cls, func):
    #     def scbuiltin_(*args):
    #         return func(*args)
    #
    #     scbuiltin_.__name__ = func.__name__  # used to obtain special_index.
    #     scbuiltin_.__qualname__ += func.__name__
    #     return scbuiltin_

    @staticmethod
    def unop(func):
        def scbuiltin_(x):
            try:
                return x._compose_unop(func)
            except AttributeError:
                try:
                    return func(x)
                except TypeError:
                    pass
            raise TypeError(f"scbuiltin '{func.__name__}' function is not "
                            f"supported for type '{type(x).__name__}'")

        scbuiltin_.__name__ = func.__name__  # used to obtain special_index.
        scbuiltin_.__qualname__ += func.__name__
        return scbuiltin_

    @staticmethod
    def binop(func):
        def scbuiltin_(a, *b):
            try:
                return a._compose_binop(func, *b)
            except AttributeError:
                try:
                    return b._rcompose_binop(func, a)
                except AttributeError:
                    try:
                        return func(a, *b)
                    except TypeError:
                        pass
            if len(b) > 0:
                raise TypeError(
                    f"scbuiltin '{func.__name__}' function is not "
                    f"supported between types '{type(a).__name__}' "
                    f"and '{type(*b).__name__}'")
            else:
                raise TypeError(
                    f"scbuiltin '{func.__name__}' function is not "
                    f"supported for type '{type(a).__name__}' ")

        scbuiltin_.__name__ = func.__name__  # used to obtain special_index.
        scbuiltin_.__qualname__ += func.__name__
        return scbuiltin_

    @staticmethod
    def narop(func):
        def scbuiltin_(x, *args):
            try:
                return x._compose_narop(func, *args)
            except AttributeError:
                try:
                    return func(x, *args)
                except TypeError:
                    pass
            raise TypeError(f"scbuiltin '{func.__name__}' function is not "
                            f"supported for type '{type(x).__name__}' "
                            f"with parameteres {args}")

        scbuiltin_.__name__ = func.__name__  # used to obtain special_index.
        scbuiltin_.__qualname__ += func.__name__
        return scbuiltin_


### Random ###

# Have special index.

@scbuiltin.unop
def rand(x):
    # *** TODO: See the actual implementations.
    if type(x) is float:
        return _libsc3.main._rgen.random() * x
    elif type(x) is int:
        if x >= 1:
            return _libsc3.main._rgen.randrange(0, x, 1)
        elif x <= -1:
            return _libsc3.main._rgen.randrange(0, x, -1)
        else:
            return 0
    raise TypeError

@scbuiltin.unop
def rand2(x):
    if type(x) is float:
        return _libsc3.main._rgen.random() * x * 2 - x  # random.uniform
    elif type(x) is int:
        if x >= 0:
            return _libsc3.main._rgen.randint(-x, x)
        else:
            return _libsc3.main._rgen.randint(x, -x)
    raise TypeError

@scbuiltin.unop
def linrand(x):
    if type(x) is float:
        a = _libsc3.main._rgen.random()
        b = _libsc3.main._rgen.random()
        return min(a, b) * x
    elif type(x) is int:
        if x >= 1:
            a = _libsc3.main._rgen.randrange(0, x, 1)
            b = _libsc3.main._rgen.randrange(0, x, 1)
            return min(a, b)
        elif x <= -1:
            a = _libsc3.main._rgen.randrange(0, x, -1)
            b = _libsc3.main._rgen.randrange(0, x, -1)
            return min(a, b)
        else:
            return 0
    raise TypeError

@scbuiltin.unop
def bilinrand(x):
    if type(x) is float:
        a = _libsc3.main._rgen.random()
        b = _libsc3.main._rgen.random()
        return a - b
    elif type(x) is int:
        if x >= 1:
            a = _libsc3.main._rgen.randrange(0, x, 1)
            b = _libsc3.main._rgen.randrange(0, x, 1)
            return a - b
        elif x <= -1:
            a = _libsc3.main._rgen.randrange(0, x, -1)
            b = _libsc3.main._rgen.randrange(0, x, -1)
            return a - b
        else:
            return 0
    raise TypeError

@scbuiltin.unop
def sum3rand(x):
    # // Larry Polansky's poor man's gaussian generator.
    return (
        (_libsc3.main._rgen.random() +
        _libsc3.main._rgen.random() +
        _libsc3.main._rgen.random() - 1.5) *
        0.666666667 * x)

@scbuiltin.unop
def coin(x):
    if type(x) is float:  # sclang Float method.
        return _libsc3.main._rgen.random() < x
    elif type(x) is int:  # sclang SimpleNumber behaviour.
        if x == 0:
            return False
        else:
            return True
    raise TypeError

@scbuiltin.binop
def rrand(a, b):
    if type(a) is float or type(b) is float:
        return a + _libsc3.main._rgen.random() * (b - a)
    elif type(a) is type(b) is int:
        if a <= b:
            if b - a >= 1:
                return _libsc3.main._rgen.randrange(a, b, 1)
            else:
                return a
        else:
            return _libsc3.main._rgen.randrange(a, b, -1)
    raise TypeError

@scbuiltin.binop
def exprand(a, b):  # exprandrng
    return a * exp(log(b / a) * _libsc3.main._rgen.random())

# Don't have special index.

@scbuiltin.binop
def xrand(x, exclude=0):
    if type(x) is type(exclude) is int:
        return mod(exclude + rand(x - 1) + 1, x);
    raise TypeError

@scbuiltin.binop
def xrand2(x, exclude=0):
    if type(x) is float:
        return rand2(x)
    elif type(x) is type(exclude) is int:
        res = rand(x * 2) - x
        return x if res == exclude else res
    raise TypeError


### Unary ###

# // this is a function for preventing pathological math operations in ugens.
# // can be used at the end of a block to fix any recirculating filter values.
@scbuiltin.unop
def zapgremlins(x):
    # float32 absx = std::abs(x);
    # // very small numbers fail the first test, eliminating denormalized numbers
    # //    (zero also fails the first test, but that is OK since it returns zero.)
    # // very large numbers fail the second test, eliminating infinities
    # // Not-a-Numbers fail both tests and are eliminated.
    # return (absx > (float32)1e-15 && absx < (float32)1e15) ? x : (float32)0.;
    absx = math.abs(x)
    if absx > 1e-15 and absx < 1e15: return x
    return 0.

@scbuiltin.unop
def log2(x):
    if x == 0: return float('-inf')
    return math.log2(x)

@scbuiltin.unop
def log10(x):
    if x == 0: return float('-inf')
    return math.log10(x)

@scbuiltin.unop
def log(x):  #, base=math.e):  # In SI is unary, can't change the base.
    if x == 0: return float('-inf')
    return math.log(x)

@scbuiltin.unop
def exp(x):
    return math.exp(x)

@scbuiltin.unop
def sin(x):
    return math.sin(x)

@scbuiltin.unop
def cos(x):
    return math.cos(x)

@scbuiltin.unop
def tan(x):
    return math.tan(x)

@scbuiltin.unop
def asin(x):
    return math.asin(x)

@scbuiltin.unop
def acos(x):
    return math.acos(x)

@scbuiltin.unop
def atan(x):
    return math.atan(x)

@scbuiltin.unop
def sinh(x):
    return math.sinh(x)

@scbuiltin.unop
def cosh(x):
    return math.cosh(x)

@scbuiltin.unop
def tanh(x):
    return math.tanh(x)

# Python math module.
# @scbuiltin.unop
# def log1p(x):
#     return math.log1p(x)
# @scbuiltin.unop
# def asinh(x):
#     return math.asinh(x)
# @scbuiltin.unop
# def acosh(x):
#     return math.acosh(x)
# @scbuiltin.unop
# def atanh(x):
#     return math.atanh(x)

_ONETWELFTH = 1. / 12.
_ONE440TH = 1. / 440.

@scbuiltin.unop
def midicps(note):
    # return (float64)440. * std::pow((float64)2., (note - (float64)69.) * (float64)0.08333333333333333333333333);
    return 440. * pow(2., (note - 69.) * _ONETWELFTH)

@scbuiltin.unop
def cpsmidi(freq):
    # return sc_log2(freq * (float64)0.002272727272727272727272727) * (float64)12. + (float64)69.;
    return log2(freq * _ONE440TH) * 12. + 69.

@scbuiltin.unop
def midiratio(midi):
    #return std::pow((float32)2. , midi * (float32)0.083333333333);
    return pow(2., midi * _ONETWELFTH)

@scbuiltin.unop
def ratiomidi(ratio):
    #return (float32)12. * sc_log2(ratio);
    return 12. * log2(ratio)

@scbuiltin.unop
def octcps(note):
    # return (float32)440. * std::pow((float32)2., note - (float32)4.75);
    return 440. * pow(2., note - 4.75)

@scbuiltin.unop
def cpsoct(freq):
    # return sc_log2(freq * (float32)0.0022727272727) + (float32)4.75;
    return log2(freq * _ONE440TH + 4.75)

@scbuiltin.unop
def ampdb(amp):
    # return std::log10(amp) * (float32)20.;
    return log10(amp) * 20.

@scbuiltin.unop
def dbamp(db):
    # return std::pow((float32)10., db * (float32).05);
    return pow(10., db * .05)

@scbuiltin.unop
def squared(x):
    return x * x;

@scbuiltin.unop
def cubed(x):
    return x * x * x;

@scbuiltin.unop
def sqrt(x):
    if x < 0.:
        return -math.sqrt(-x)
    else:
        return math.sqrt(x)

@scbuiltin.unop
def hanwindow(x):
    # if (x < (float32)0. || x > (float32)1.) return (float32)0.;
    # return (float32)0.5 - (float32)0.5 * static_cast<float32>(cos(x * (float32)twopi));
    if x < 0. or x > 1.: return 0.
    return 0.5 - 0.5 * cos(x * twopi)

@scbuiltin.unop
def welwindow(x):
    # if (x < (float32)0. || x > (float32)1.) return (float32)0.;
    # return static_cast<float32>(sin(x * pi));
    if x < 0. or x > 1.: return 0.
    return sin(x * pi)

@scbuiltin.unop
def triwindow(x):
    # if (x < (float32)0. || x > (float32)1.) return (float32)0.;
    # if (x < (float32)0.5) return (float32)2. * x;
    # else return (float32)-2. * x + (float32)2.;
    if x < 0. or x > 1.: return 0.
    if x < 0.5: return 2. * x
    return -2. * x + 2.

@scbuiltin.unop
def bitriwindow(x):  # not used in sclang
    # float32 ax = (float32)1. - std::abs(x);
    # if (ax <= (float32)0.) return (float32)0.;
    # return ax;
    ax = 1. - abs(x)
    if ax <= 0.: return 0.
    return ax

@scbuiltin.unop
def rectwindow(x):
    # if (x < (float32)0. || x > (float32)1.) return (float32)0.;
    # return (float32)1.;
    if x < 0. or x > 1.: return 0.
    return 1.

@scbuiltin.unop
def scurve(x):
    # if (x <= (float32)0.) return (float32)0.;
    # if (x >= (float32)1.) return (float32)1.;
    # return x * x * ((float32)3. - (float32)2. * x);
    if x <= 0.: return 0.
    if x >= 1.: return 1.
    return x * x * (3. - 2. * x)

@scbuiltin.unop
def scurve0(x):  # not used in sclang
    # // assumes that x is in range
    # return x * x * ((float32)3. - (float32)2. * x);
    return x * x * (3. - 2. * x)

@scbuiltin.unop
def ramp(x):
    # if (x <= (float32)0.) return (float32)0.;
    # if (x >= (float32)1.) return (float32)1.;
    # return x;
    if x <= 0.: return 0.
    if x >= 1.: return 1.
    return x

@scbuiltin.unop
def sign(x):
    # return x < (float32)0. ? (float32)-1. : (x > (float32)0. ? (float32)1.f : (float32)0.f);
    if x < 0.: return -1.
    if x > 0.: return 1.
    return 0.

@scbuiltin.unop
def distort(x):
    # return x / ((float32)1. + std::abs(x));
    return x / (1. + abs(x))

@scbuiltin.unop
def distortneg(x):  # not used in sclang
    # if (x < (float32)0.)
    #     return x/((float32)1. - x);
    # else
    #     return x;
    if x < 0.: return x / (1. - x)
    return x

@scbuiltin.unop
def softclip(x):
    # float32 absx = std::abs(x);
    # if (absx <= (float32)0.5) return x;
    # else return (absx - (float32)0.25) / x;
    absx = abs(x)
    if absx <= 0.5: return x
    return (absx - 0.25) / x

@scbuiltin.unop
def even(x):
    return int(x) & 1 == 0

@scbuiltin.unop
def odd(x):
    return int(x) & 1 == 1

@scbuiltin.unop
def taylorsin(x):
    # // Taylor expansion out to x**9/9! factored  into multiply-adds
    # // from Phil Burk.
    # // valid range from -pi/2 to +3pi/2
    # x = static_cast<float32>((float32)pi2 - std::abs(pi2 - x));
    # float32 x2 = x * x;
    # return static_cast<float32>(x*(x2*(x2*(x2*(x2*(1.0/362880.0)
    #         - (1.0/5040.0))
    #         + (1.0/120.0))
    #         - (1.0/6.0))
    #         + 1.0));
    x = pi2 - abs(pi2 - x)
    x2 = x * x
    return (x*(x2*(x2*(x2*(x2*(1.0/362880.0)\
        - (1.0/5040.0))\
        + (1.0/120.0))\
        - (1.0/6.0))\
        + 1.0))

# @scbuiltin.unop
# def trunc(x):  # duplicated as unary and binary, AbstractFunction use binary, see below.
#     return math.trunc(x);

@scbuiltin.unop
def ceil(x):
    return math.ceil(x)

@scbuiltin.unop
def floor(x):
    return math.floor(x)

@scbuiltin.unop
def reciprocal(x):
    return 1. / x

@scbuiltin.unop
def bitnot(x):
    #return (float32) ~ (int)x;
    return float(~int(x))

@scbuiltin.unop
def frac(x):
    # return x - sc_floor(x);
    # return math.fmod(x)[0]
    return x - floor(x)

_ONESIXTH = 1. / 6.

@scbuiltin.narop
def lg3interp(x1, a, b, c, d): # sc_lg3interp solo la define para float32
    # // cubic lagrange interpolator
    # float32 x0 = x1 + 1.f;
    # float32 x2 = x1 - 1.f;
    # float32 x3 = x1 - 2.f;
    #
    # float32 x03 = x0 * x3 * 0.5f;
    # float32 x12 = x1 * x2 * 0.16666666666666667f;
    #
    # return x12 * (d * x0 - a * x3) + x03 * (b * x2 - c * x1);
    x0 = x1 + 1.
    x2 = x1 - 1.
    x3 = x1 - 2.
    x03 = x0 * x3 * 0.5
    x12 = x1 * x2 * _ONESIXTH
    return x12 * (d * x0 - a * x3) + x03 * (b * x2 - c * x1)

@scbuiltin.binop
def calcfeedback(delaytime, decaytime):  # CalcFeedback, solo la define para float32
    # if (delaytime == 0.f || decaytime == 0.f)
    #     return 0.f;
    #
    # float32 absret = static_cast<float32>( std::exp(log001 * delaytime / std::abs(decaytime)));
    # float32 ret = std::copysign(absret, decaytime);
    # return ret;
    if delaytime == 0. or decaytime == 0.:
        return 0.
    absret = math.exp(log001 * delaytime / abs(decaytime))
    return math.copysign(absret, decaytime)

@scbuiltin.unop
def wrap1(x):
    # if (x >= (float32) 1.) return x + (float32)-2.;
    # if (x <  (float32)-1.) return x + (float32) 2.;
    # return x;
    if x >= 1.: return x - 2.
    if x < -1.: return x + 2.
    return x

@scbuiltin.unop
def fold1(x):
    # if (x >= (float32) 1.) return (float32) 2. - x;
    # if (x <  (float32)-1.) return (float32)-2. - x;
    # return x;
    if x >= 1.: return 2 - x
    if x < -1.: return -2 - x
    return x

@scbuiltin.unop
def graycode(x): # grayCode, está abajo de todo y es para int32
    # return x ^ (x >> 1);
    x = int(x)
    return x ^ (x >> 1)

@scbuiltin.unop
def degrad(x):
    return x * pi / 180.

@scbuiltin.unop
def raddeg(x):
    return x * 180. / pi

@scbuiltin.unop
def next_power_of_two(x):  # Integer _NextPowerOfTwo
    return 2 ** ceil(log(x) / log(2))

@scbuiltin.binop
def next_near_power(x, base=2):  # SimpleNumber.nextPowerOf
    return base ** ceil(log(x) / log(base))

@scbuiltin.binop
def previous_near_power(x, base=2):  # SimpleNumber.previousPowerOf
    return base ** (ceil(log(x) / log(base)) - 1)


### Binary ###

@scbuiltin.binop
def mod(a, b):
    # NOTE: Has a different behaviour from Python's %.
    # DOUBLE/FLOAT
    # // avoid the divide if possible
    # const double lo = (double)0.;
    # if (in >= hi) {
    #     in -= hi;
    #     if (in < hi) return in;
    # } else if (in < lo) {
    #     in += hi;
    #     if (in >= lo) return in;
    # } else return in;
    #
    # if (hi == lo) return lo;
    # FLOAT
    # return in - hi*sc_floor(in/hi);
    # INT
    # int c;
    # c = in % hi;
    # if (c<0) c += hi;
    # return c;
    zero = 0
    if a >= b:
        a -= b
        if a < b: return a
    elif a < zero:
        a += b
        if a >= zero: return a
    else:
        return a

    if b == zero: return zero

    if type(a) is float or type(b) is float:
        return a - b * floor(a/b)

    c = int(math.fmod(a, b))
    if c < 0: c += b
    return c

@scbuiltin.narop
def wrap(x, lo, hi, range=None): # *** BUG: AbstractFunction usa sin range. tiene dos firmas, sin y con range, la implementación varía sutilmente.
# INT: abajo define wrap para int sin range como:
# return sc_mod(in - lo, hi - lo + 1) + lo;
    if type(x) is int:
        lo = int(lo)
        hi = int(hi)
        return mod(x - lo, hi - lo + 1) + lo
    # // avoid the divide if possible
    # if (in >= hi) {
# range = hi - lo; # sin range
    #     in -= range;
    #     if (in < hi) return in;
    # } else if (in < lo) {
# range = hi - lo; # sin range
    #     in += range;
    #     if (in >= lo) return in;
    # } else return in;
    #
    # if (hi == lo) return lo;
    # return in - range * sc_floor((in - lo)/range);
    if x >= hi:
        if range is None:
            range = hi - lo
        x -= range
        if x < hi: return x
    elif x < lo:
        if range is None:
            range = hi - lo
        x += range
        if x >= lo: return x
    else:
        return x

    if hi == lo: return lo
    return x - range * floor((x - lo) / range)

@scbuiltin.narop
def fold(x, lo, hi, range=None, range2=None): # *** BUG: ídem wrap con range y range2
# INT: abajo define fold para int sin range ni range2
# int b = hi - lo;
# int b2 = b+b;
# int c = sc_mod(in - lo, b2);
# if (c>b) c = b2-c;
# return c + lo;
    if type(x) is int:
        lo = int(lo)
        hi = int(hi)
        b = hi - lo
        b2 = b + b
        c = mod(x - lo, b2)
        if c > b: c = b2 - c
        return c + lo
    # double x, c;
    # x = in - lo;
    #
    # // avoid the divide if possible
    # if (in >= hi) {
    #     in = hi + hi - in;
    #     if (in >= lo) return in;
    # } else if (in < lo) {
    #     in = lo + lo - in;
    #     if (in < hi) return in;
    # } else return in;
    #
    # if (hi == lo) return lo;
    # // ok do the divide
# range = hi - lo; # sin range
# range2 = range + range; # sin range2
    # c = x - range2 * sc_floor(x / range2);
    # if (c>=range) c = range2 - c;
    # return c + lo;
    x2 = x - lo
    if x >= hi:
        x = hi + hi - x
        if x >= lo: return x
    elif x < lo:
        x = lo + lo - x
        if x < hi: return x
    else:
        return x

    if hi == lo: return lo
    if range is None:
        range = hi - lo
        range2 = range + range
    c = x2 - range2 * floor(x2 / range2)
    if c >= range:
        c = range2 - c
    return c + lo

# TODO: define pow, eso no es bueno para mi. *********************************
# @scbuiltin
# def pow(a, b):
#     # return a >= 0.f ? std::pow(a, b) : -std::pow(-a, b);
#     pass

@scbuiltin.binop
def div(a, b): # TODO: define div para int devolviendo el dividendo si el divisor es cero, en sclang es el comportamiento de 1 div: 0, en Python 1 // 0 es error.
               # TODO: ver si se usa para las ugens o qué cómo, lo mismo con mod.
               # TODO: si lo sargumentos son float sclang realiza las operaciones y castead el valor de retorno.
    # int c;
    # if (b) {
    #     if (a<0) c = (a+1)/b - 1;
    #     else c = a/b;
    # } else c = a;
    # return c;
    if b:
        if a < 0: c = (a + 1) / b - 1
        else: c = a / b
    else:
        c = a
    return int(c)

@scbuiltin.binop
def min(a, b):
    return builtins.min(a, b)

@scbuiltin.binop
def max(a, b):
    return builtins.max(a, b)

@scbuiltin.binop
def round(x, quant=1):
    # return quant==0. ? x : sc_floor(x/quant + .5) * quant;
    # INT return quant==0 ? x : sc_div(x + quant/2, quant) * quant;
    if type(x) is int:
        quant = int(quant)
        if quant == 0:
            return float(x)
        else:
            return float(div(x + quant // 2, quant) * quant)
    if quant == 0.:
        return float(x)
    else:
        return float(floor(x / quant + .5) * quant)

@scbuiltin.binop
def roundup(x, quant=1):
    # return quant==0. ? x : sc_ceil(x/quant) * quant;
    # INT return quant==0 ? x : sc_div(x + quant - 1, quant) * quant;
    if type(x) is int:
        quant = int(quant)
        if quant == 0:
            return float(x)
        else:
            return float(div(x + quant - 1, quant) * quant)
    if quant == 0.:
        return float(x)
    else:
        return float(ceil(x / quant) * quant)

@scbuiltin.binop
def trunc(x, quant=1):
    # return quant==0. ? x : sc_floor(x/quant) * quant;
    # INT: return quant==0 ? x : sc_div(x, quant) * quant;
    if type(x) is int:
        quant = int(quant)
        if quant == 0:
            return float(x)
        else:
            return float(div(x, quant) * quant)
    if quant == 0.:
        return float(x)
    else:
        return float(floor(x / quant) * quant)

@scbuiltin.binop
def atan2(a, b): # TODO: Solo la define para float. Pero creo que no define sin/cos y las demás.
    # return std::atan2(a, b);
    return math.atan2(a, b)

_SQRT2M1 = math.sqrt(2.) - 1.;

@scbuiltin.narop
def clip(x, lo, hi):
    #./common/SC_BoundsMacros.h:
    #inline T sc_clip(T x, U lo, V hi) return std::max(std::min(x, (T)hi), (T)lo);
    T = type(x)
    return max(min(x, T(hi)), T(lo))

@scbuiltin.binop
def hypot(x, y):
    return math.hypot(x, y)

@scbuiltin.binop
def hypotx(x, y):  # hypotenuse aproximation C name, hypotApx in sclang.
    # double minxy;
    # x = std::abs(x);
    # y = std::abs(y);
    # minxy = sc_min(x,y);
    # return x + y - kDSQRT2M1 * minxy;
    x = abs(x)
    y = abs(y)
    minxy = min(x, y)
    return x + y - _SQRT2M1 * minxy

@scbuiltin.binop
def gcd(a, b):
# FLOAT: abajo define para float gcd(u, v)
# return (float) sc_gcd((long) std::trunc(u), (long) std::trunc(v));
    # if (a == 0)
    #     return b;
    # if (b == 0)
    #     return a;
    # const bool negative = (a <= 0 && b <= 0);
    # a = sc_abs(a);
    # b = sc_abs(b);
    # if (a == 1 || b == 1) {
    #     if(negative) {
    #         return (long) -1;
    #     } else {
    #         return (long) 1;
    #     }
    # }
    # if (a < b) {
    #     long t = a;
    #     a = b;
    #     b = t;
    # }
    # while (b > 0) {
    #     long t = a % b;
    #     a = b;
    #     b = t;
    # }
    # if(negative) {
    #     a = 0 - a;
    # }
    # return a;
    if type(a) is float or type(b) is float:
        a = int(a)
        b = int(b)
    T = type(a)

    if a == 0: return b
    if b == 0: return a
    negative = a <= 0 and b <=0
    a = abs(a)
    b = abs(b)
    if a == 1 or b == 1:
        if negative: return -1
        else: return 1
    if a < b:
        t = a
        a = b
        b = t
    while b > 0:
        t = a % b
        a = b
        b = t
    if negative:
        a = 0 - a

    return T(a)

@scbuiltin.binop
def lcm(a, b):
# FLOAT: abajo define para float lcm(u, v)
# return (float) sc_lcm((long) std::trunc(u), (long) std::trunc(v));
    # if (a == 0 || b == 0)
    #     return (long)0;
    # else
    #     return (a * b) / sc_gcd(a, b);
    if type(a) is float or type(b) is float:
        a = int(a)
        b = int(b)

    if a == 0 or b == 0:
        return 0
    else:
        return (a * b) // gcd(a, b)

# @scbuiltin.binop
# def bitand(a, b):  # has special index
#     return a & b
#
# @scbuiltin.binop
# def bitor(a, b):  # has special index
#     return a | b

# bitxor  # missing
# bitHammingDistance  # missing

# @scbuiltin.binop
# def leftshift(a, b):  # has special index
#     return a << b
#
# @scbuiltin.binop
# def rightshift(a, b):  # has special index
#     return a >> b
#
# @scbuiltin.binop
# def urightshift(a, b):  # has special index
#     return (uint32)a >> b;

# @scbuiltin.binop # only used in /server/plugins/LFUGens.cpp and example in ServerPluginAPI.schelp
# def powi(x, n):
#     # F z = 1;
#     # while (n != 0)
#     # {
#     #     if ((n & 1) != 0)
#     #     {
#     #         z *= x;
#     #     }
#     #     n >>= 1;
#     #     x *= x;
#     # }
#     # return z;
#     pass

@scbuiltin.binop
def thresh(a, b): # sc_thresh(T a, U b)
    # return a < b ? (T)0 : a;
    T = type(a)
    if a < b: return T(0)
    return a

@scbuiltin.binop
def clip2(a, b): # sc_clip2(T a, T b) # Estas son las que usa como operadores integrados de las UGens.
    # return sc_clip(a, -b, b);
    return clip(a, -b, b)

@scbuiltin.binop
def wrap2(a, b): # wrap2(T a, T b)
    # return sc_wrap(a, -b, b);
    return wrap(a, -b, b)

@scbuiltin.binop
def fold2(a, b): # sc_fold2(T a, T b)
    # return sc_fold(a, -b, b);
    return fold(a, -b, b)

@scbuiltin.binop
def excess(a, b): # sc_excess(T a, T b)
    # return a - sc_clip(a, -b, b);
    return a - clip(a, -b, b)

@scbuiltin.binop
def first_arg(a, b):
    return a

@scbuiltin.binop
def scaleneg(a, b):
    # template: T a, T b
    # if (a < 0)
    #     return a*b;
    # else
    #     return a;
    # DOUBLE/FLOAT
    # b = 0.5 * b + 0.5;
    # return (std::abs(a) - a) * b + a;
    if type(a) is int and type(b) is int:
        if a < 0: return a * b
        return a
    b = 0.5 * b + 0.5
    return (abs(a) - a) * b + a

@scbuiltin.binop
def amclip(a, b):
    # template: T a, T b
    # if (b < 0)
    #     return 0;
    # else
    #     return a*b;
    # DOUBLE/FLOAT
    # return a * 0.5 * (b + std::abs(b));
    if type(a) is int and type(b) is int:
        if b < 0: return 0
        return a * b
    return a * 0.5 * (b + abs(b))

@scbuiltin.binop
def ring1(a, b):
    return a * b + a

@scbuiltin.binop
def ring2(a, b):
    return a * b + a + b

@scbuiltin.binop
def ring3(a, b):
    return a * a * b

@scbuiltin.binop
def ring4(a, b):
    return a * a * b - a * b * b

@scbuiltin.binop
def difsqr(a, b):
    return a * a - b * b

@scbuiltin.binop
def sumsqr(a, b):
    return a * a + b * b

@scbuiltin.binop
def sqrsum(a, b):
    z = a + b
    return z * z

@scbuiltin.binop
def sqrdif(a, b):
    z = a - b
    return z * z

@scbuiltin.binop
def absdif(a, b):
    return abs(a - b)


### Nary ###

@scbuiltin.narop
def blend(a, b, frac=0.5):
    # // frac should be from zero to one
    return a + (frac * (b - a))

@scbuiltin.narop
def snap(x, resolution=1.0, margin=0.05, strength=1.0):
    round_ = round(x, resolution)
    diff = round_ - x
    if abs(diff) < margin:
        return x + strength * diff
    else:
        return x

@scbuiltin.narop
def softround(x, resolution=1.0, margin=0.05, strength=1.0):
    round_ = round(x, resolution)
    diff = round_ - x
    if abs(diff) > margin:
        return x + strength * diff
    else:
        return x

@scbuiltin.narop
def linlin(x, inmin, inmax, outmin, outmax, clip='minmax'):
    if clip == 'minmax':
        if x <= inmin: return outmin
        if x >= inmax: return outmax
    elif clip == 'min':
        if x <= inmin: return outmin
    elif clip == 'max':
        if x >= inmax: return outmax
    return (x - inmin) / (inmax - inmin) * (outmax - outmin) + outmin

@scbuiltin.narop
def linexp(x, inmin, inmax, outmin, outmax, clip='minmax'):
    if clip == 'minmax':
        if x <= inmin: return outmin
        if x >= inmax: return outmax
    elif clip == 'min':
        if x <= inmin: return outmin
    elif clip == 'max':
        if x >= inmax: return outmax
    return math.pow(outmax / outmin, (x - inmin) / (inmax - inmin)) * outmin

@scbuiltin.narop
def explin(x, inmin, inmax, outmin, outmax, clip='minmax'):
    if clip == 'minmax':
        if x <= inmin: return outmin
        if x >= inmax: return outmax
    elif clip == 'min':
        if x <= inmin: return outmin
    elif clip == 'max':
        if x >= inmax: return outmax
    return log(x / inmin, math.e) / log(inmax / inmin, math.e)\
           * (outmax - outmin) + outmin

@scbuiltin.narop
def expexp(x, inmin, inmax, outmin, outmax, clip='minmax'):
    if clip == 'minmax':
        if x <= inmin: return outmin
        if x >= inmax: return outmax
    elif clip == 'min':
        if x <= inmin: return outmin
    elif clip == 'max':
        if x >= inmax: return outmax
    return math.pow(
        outmax / outmin,
        log(x / inmin, math.e) / log(inmax / inmin, math.e)
    ) * outmin

@scbuiltin.narop
def lincurve(x, inmin, inmax, outmin, outmax, curve=-4, clip='minmax'):
    if clip == 'minmax':
        if x <= inmin: return outmin
        if x >= inmax: return outmax
    elif clip == 'min':
        if x <= inmin: return outmin
    elif clip == 'max':
        if x >= inmax: return outmax
    if abs(curve) < 0.001:
        # // If the value should be clipped, it has already been clipped (above).
        # // If we got this far, then linlin does not need to do any clipping.
        # // Inlining the formula here makes it even faster.
        return (x - inmin) / (inmax - inmin) * (outmax - outmin) + outmin
    grow = math.exp(curve)
    a = (outmax - outmin) / (1.0 - grow)
    b = outmin + a
    scaled = (x - inmin) / (inmax - inmin)
    return b - a * math.pow(grow, scaled, math.e)

@scbuiltin.narop
def curvelin(x, inmin, inmax, outmin, outmax, curve=-4, clip='minmax'):
    if clip == 'minmax':
        if x <= inmin: return outmin
        if x >= inmax: return outmax
    elif clip == 'min':
        if x <= inmin: return outmin
    elif clip == 'max':
        if x >= inmax: return outmax
    if abs(curve):
        # // If the value should be clipped, it has already been clipped (above).
        return (x - inmin) / (inmax - inmin) * (outmax - outmin) + outmin
    grow = math.exp(curve)
    a = (inmax - inmin) / (1.0 - grow)
    b = inmin + a
    return log((b - x) / a, math.e) * (outmax - outmin) / curve + outmin

@scbuiltin.narop
def bilin(x, incenter, inmin, inmax, outcenter, outmin, outmax, clip='minmax'):
    if clip == 'minmax':
        if x <= inmin: return outmin
        if x >= inmax: return outmax
    elif clip == 'min':
        if x <= inmin: return outmin
    elif clip == 'max':
        if x >= inmax: return outmax
    if x >= incenter:
        return linlin(x, incenter, inmax, outcenter, outmax, None)
    else:
        return linlin(inmin, incenter, outmin, outcenter, None)

@scbuiltin.narop
def biexp(x, incenter, inmin, inmax, outcenter, outmin, outmax, clip='minmax'):
    if clip == 'minmax':
        if x <= inmin: return outmin
        if x >= inmax: return outmax
    elif clip == 'min':
        if x <= inmin: return outmin
    elif clip == 'max':
        if x >= inmax: return outmax
    if x >= incenter:
        return explin(incenter, inmax, outcenter, outmax, None)
    else:
        return explin(inmin, incenter, outmin, outcenter, None)

@scbuiltin.narop
def moddif(a, b, mod=1.0):
    diff = mod(absdif(a, b), mod)
    modhalf = mod * 0.5
    return modhalf - absdif(diff, modhalf)

@scbuiltin.narop
def lcurve(x, a=1.0, m=0.0, n=1.0, tau=1.0):
    x = -x
    if tau == 1.0:
        return a * (m * exp(x) + 1) / (n * exp(x) + 1)
    else:
        rtau = 1. / tau
        return a * (m * exp(x) * rtau + 1) / (n * exp(x) * rtau + 1)

@scbuiltin.narop  # binop
def gauss(x, stdev):  # standard_deviation
    return sqrt(-2 * log(rand(1.0))) * sin(rand(twopi)) * stdev + x

@scbuiltin.narop
def gauss_curve(x, a=1.0, b=0.0, c=1.0):
    return a * exp(squared(x - b) / (-2.0 * squared(c)))

# digitValue  # ?
# thru ??  # ?

# complex and cartesian
# rho
# theta
# rotate
# dist


### Array ###

# The next sclang functios operate over lists and don't map to server opcodes.
# They are Routine's state aware, i.e. random operatons use rgen state.

import operator
import itertools


def normalize(lst, min=0.0, max=1.0):
    min = itertools.repeat(min)
    max = itertools.repeat(max)
    outmin = itertools.repeat(builtins.min(lst))
    outmax = itertools.repeat(builtins.max(lst))
    return list(map(linlin, lst, outmin, outmax, min, max))

def normsum(lst):  # normalizeSum/normalize_sum
    return list(map(operator.truediv, lst, itertools.repeat(sum(lst))))

def shuffle(lst, random=None):  # scramble
    return _libsc3.main._rgen.shuffle(lst, random)  # In place.

# mirror, mirror1, mirror2  # one mirror with mode.
# stutter, rotate, pyramid, pyramidg, sputter(rand), etc.

def blend_at(lst, index):
    imin = int(roundup(index)) - 1
    imax = len(lst) - 1
    a = lst[clip(imin, 0, imax)]
    b = lst[clip(imin + 1, 0, imax)]
    return blend(a, b, abs(index - imin))

def resamp0(lst, new_size):
    factor = (len(lst) - 1) / builtins.max(new_size - 1, 1)
    return list(lst[int(round(i * factor))] for i in range(new_size))

def resamp1(lst, new_size):
    factor = (len(lst) - 1) / builtins.max(new_size - 1, 1)
    return list(blend_at(lst, i * factor) for i in range(new_size))

def index_of_greater_than(lst, val, start=0):
    for i, n in enumerate(lst[start:]):
        if n > val:
            return i + start
    return len(lst) - 1

def index_in_between(lst, val):
    # // Collection is sorted, returns linearly interpolated index.
    i = index_of_greater_than(lst, val)
    if i == 0:
        return 0
    if i == len(lst):
        return len(lst) - 1
    a = lst[i - 1]
    b = lst[i]
    div = b - a
    if div == 0:
        return i
    return ((val - a) / div) + i - 1

def as_random_table(lst, size=None):
    if size is None:
        size = len(lst)
    else:
        lst = resamp1(lst, size)
    acc = list(itertools.accumulate(lst))  # // Incrementally integrate.
    norm = normalize(acc, 0.0, size - 1.0)  # // Normalize and scale by max index.
    lasti = 0
    res = []
    for i in range(size):
        # indexInBetween wit start and rescale to 0..1
        lasti = index_of_greater_than(norm, i, lasti)
        a = norm[lasti-1]
        div = norm[lasti] - a
        if div == 0:
            res.append(lasti / size)
        else:
            res.append( (((i - a) / div) + lasti - 1) / size )
    return res

def table_rand(lst):
    return blend_at(lst, rand(float(len(lst) - 1)))


### SequenceableCollection ###

def choice(lst):  # choose
    return _libsc3.main._rgen.choice(lst)

def choices(lst, weights=None, *, cum_weights=None, k=1):  # wchoose
    return _libsc3.main._rgen.choices(
        lst, weights, cum_weights=cum_weights, k=k)

# ...


### Utilities ###


_uid_counter = itertools.count()

def uid():
    '''Library wise counter used to get unique ids for server replies.'''
    return next(_uid_counter)


def counter(stop):
    '''Possibly infinite counter, range replacement for patterns.'''
    if stop == float('inf'):
        return itertools.count()
    else:
        return range(stop)
