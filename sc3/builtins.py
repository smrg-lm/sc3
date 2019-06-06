"""
builtins.py

Builtin functions from ugens/sclang.

Son los operadores unarios/binarios/enarios de las
AbstractFunction y las UGen que también se aplican a otros
tipos de datos básico dentro de la librería de clases.

De no tener equivalentes estas funciones deberían implementarse
en CPython?

Ver:
/include/plugin_interface/SC_InlineUnaryOp.h
/include/plugin_interface/SC_InlineBinaryOp.h

Son, en gran parte, las funciones de _specialindex.py. Agregué
las que no están implementadas como interfaz para las ugens
pero sí están en sclang.
"""

import math

from . import functions as fn # TODO: desde la terminal, funciona solo si el otro módulo fue cargado antes.


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

# Decorator
def scbuiltin(func):
    def scbuiltin_(*args):
        # TODO: ver qué hacer con las listas de Python. UNA RTA: EN PYTHON SE USA MAP Y
        # LISTCOMPREHENSION, TRATAR DE HACERLA PYTÓNICA. PERO SCLANG SOPORTA ESE COMPORTAMIENTO Y ES MUY COMÚN.
        # EL PROBLEMA ES QUE SI SE IMPLEMENTA PARA ESTAS FUNCIONES, EL RESTO DE LAS COSAS PITÓNICAS QUEDA TRUNCO?
        # _MSG = "bad operand type for {}: '{}'"
        # try: # TODO: Ahora el único problema es que quede la cosa demasiado sobrecargada, y si agrego collections más.
        # except TypeError as e: raise TypeError(_MSG.format('midicps()', type(note).__name__)) from e
        return func(*args)
    scbuiltin_.__scbuiltin__ = True # TODO: VER, podría ser None, solo se comprueba si tiene el atributo.
    scbuiltin_.__name__ = func.__name__ # Este es el nombre que se usa para obtener special_index.
    scbuiltin_.__qualname__ += func.__name__
    return scbuiltin_

# Unary

# TODO: Ver AbstractFunction y la documentación de Operators en SuperCollider.

# // this is a function for preventing pathological math operations in ugens.
# // can be used at the end of a block to fix any recirculating filter values.
@scbuiltin
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

@scbuiltin
def log2(x):
    return math.log2(x)

@scbuiltin
def log10(x):
    return math.log10(x)

# TODO: faltantes agregadas, no se usan como builtins abajo pero si en AbstractFunction
@scbuiltin
def log(x, base=math.e): # BUG: ES BINARIO.
    return math.log(x, base)
@scbuiltin
def exp(x):
    return math.exp(x)
@scbuiltin
def sin(x):
    return math.sin(x)
@scbuiltin
def cos(x):
    return math.cos(x)
@scbuiltin
def tan(x):
    return math.tan(x)
@scbuiltin
def asin(x):
    return math.asin(x)
@scbuiltin
def acos(x):
    return math.acos(x)
@scbuiltin
def atan(x):
    return math.atan(x)
@scbuiltin
def sinh(x):
    return math.sinh(x)
@scbuiltin
def cosh(x):
    return math.cosh(x)
@scbuiltin
def tanh(x):
    return math.tanh(x)
# TODO: no están en _specialindex
# @scbuiltin
# def log1p(x):
#     return math.log1p(x)
# @scbuiltin
# def asinh(x):
#     return math.asinh(x)
# @scbuiltin
# def acosh(x):
#     return math.acosh(x)
# @scbuiltin
# def atanh(x):
#     return math.atanh(x)

_ONETWELFTH = 1. / 12.
_ONE440TH = 1. / 440.

@scbuiltin
def midicps(note):
    # return (float64)440. * std::pow((float64)2., (note - (float64)69.) * (float64)0.08333333333333333333333333);
    return 440. * pow(2., (note - 69.) * _ONETWELFTH)

@scbuiltin
def cpsmidi(freq):
    # return sc_log2(freq * (float64)0.002272727272727272727272727) * (float64)12. + (float64)69.;
    return log2(freq * _ONE440TH) * 12. + 69.

@scbuiltin
def midiratio(midi):
    #return std::pow((float32)2. , midi * (float32)0.083333333333);
    return pow(2., midi * _ONETWELFTH)

@scbuiltin
def ratiomidi(ratio):
    #return (float32)12. * sc_log2(ratio);
    return 12. * log2(ratio)

@scbuiltin
def octcps(note):
    # return (float32)440. * std::pow((float32)2., note - (float32)4.75);
    return 440. * pow(2., note - 4.75)

@scbuiltin
def cpsoct(freq):
    # return sc_log2(freq * (float32)0.0022727272727) + (float32)4.75;
    return log2(freq * _ONE440TH + 4.75)

@scbuiltin
def ampdb(amp):
    # return std::log10(amp) * (float32)20.;
    return log10(amp) * 20.

@scbuiltin
def dbamp(db):
    # return std::pow((float32)10., db * (float32).05);
    return pow(10., db * .05)

@scbuiltin
def squared(x):
    return x * x;

@scbuiltin
def cubed(x):
    return x * x * x;

@scbuiltin
def sqrt(x):
    if x < 0.:
        return -math.sqrt(-x)
    else:
        return math.sqrt(x)

@scbuiltin
def hanwindow(x):
    # if (x < (float32)0. || x > (float32)1.) return (float32)0.;
    # return (float32)0.5 - (float32)0.5 * static_cast<float32>(cos(x * (float32)twopi));
    if x < 0. or x > 1.: return 0.
    return 0.5 - 0.5 * cos(x * twopi)

@scbuiltin
def welwindow(x):
    # if (x < (float32)0. || x > (float32)1.) return (float32)0.;
    # return static_cast<float32>(sin(x * pi));
    if x < 0. or x > 1.: return 0.
    return sin(x * pi)

@scbuiltin
def triwindow(x):
    # if (x < (float32)0. || x > (float32)1.) return (float32)0.;
    # if (x < (float32)0.5) return (float32)2. * x;
    # else return (float32)-2. * x + (float32)2.;
    if x < 0. or x > 1.: return 0.
    if x < 0.5: return 2. * x
    return -2. * x + 2.

@scbuiltin
def bitriwindow(x):
    # float32 ax = (float32)1. - std::abs(x);
    # if (ax <= (float32)0.) return (float32)0.;
    # return ax;
    ax = 1. - abs(x)
    if ax <= 0.: return 0.
    return ax

@scbuiltin
def rectwindow(x):
    # if (x < (float32)0. || x > (float32)1.) return (float32)0.;
    # return (float32)1.;
    if x < 0. or x > 1.: return 0.
    return 1.

@scbuiltin
def scurve(x):
    # if (x <= (float32)0.) return (float32)0.;
    # if (x >= (float32)1.) return (float32)1.;
    # return x * x * ((float32)3. - (float32)2. * x);
    if x <= 0.: return 0.
    if x >= 1.: return 1.
    return x * x * (3. - 2. * x)

@scbuiltin
def scurve0(x):
    # // assumes that x is in range
    # return x * x * ((float32)3. - (float32)2. * x);
    return x * x * (3. - 2. * x)

@scbuiltin
def ramp(x):
    # if (x <= (float32)0.) return (float32)0.;
    # if (x >= (float32)1.) return (float32)1.;
    # return x;
    if x <= 0.: return 0.
    if x >= 1.: return 1.
    return x

@scbuiltin
def sign(x):
    # return x < (float32)0. ? (float32)-1. : (x > (float32)0. ? (float32)1.f : (float32)0.f);
    if x < 0.: return -1.
    if x > 0.: return 1.
    return 0.

@scbuiltin
def distort(x): # TODO: para mi, qué otras funciones de distorsión hay y cómo generan parciales agudos?
    # return x / ((float32)1. + std::abs(x));
    return x / (1. + abs(x))

@scbuiltin
def distortneg(x):
    # if (x < (float32)0.)
    #     return x/((float32)1. - x);
    # else
    #     return x;
    if x < 0.: return x / (1. - x)
    return x

@scbuiltin
def softclip(x):
    # float32 absx = std::abs(x);
    # if (absx <= (float32)0.5) return x;
    # else return (absx - (float32)0.25) / x;
    absx = abs(x)
    if absx <= 0.5: return x
    return (absx - 0.25) / x

# // Taylor expansion out to x**9/9! factored  into multiply-adds
# // from Phil Burk.
@scbuiltin
def taylorsin(x):
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

@scbuiltin
def trunc(x):
    return math.trunc(x);

@scbuiltin
def ceil(x):
    return math.ceil(x)

@scbuiltin
def floor(x):
    return math.floor(x)

@scbuiltin
def reciprocal(x):
    return 1 / x

@scbuiltin
def bitnot(x):
    #return (float32) ~ (int)x;
    return float(~int(x))

@scbuiltin
def frac(x):
    # return x - sc_floor(x);
    return x - floor(x)

_ONESIXTH = 1. / 6.

@scbuiltin
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

@scbuiltin
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

@scbuiltin
def wrap1(x):
    # if (x >= (float32) 1.) return x + (float32)-2.;
    # if (x <  (float32)-1.) return x + (float32) 2.;
    # return x;
    if x >= 1.: return x - 2.
    if x < -1.: return x + 2.
    return x

@scbuiltin
def fold1(x):
    # if (x >= (float32) 1.) return (float32) 2. - x;
    # if (x <  (float32)-1.) return (float32)-2. - x;
    # return x;
    if x >= 1.: return 2 - x
    if x < -1.: return -2 - x
    return x

@scbuiltin
def graycode(x): # grayCode, está abajo de todo y es para int32
    # return x ^ (x >> 1);
    x = int(x)
    return x ^ (x >> 1)

# Binary

@scbuiltin
def mod(a, b): # TODO: en Python se usa __mod__ para el símbolo. Y no sé que tanto afecta el comportamiento esta implementación.
               # TODO: en sclang para números enteros negativos devuelve distintos dependiendo si son iguales mayores o menores,
               # TODO: mod(-3, -2) es -3, mod(-7, -3) es -4, mod(-7, -3) es -5
               # TODO: en Python devuleve el módulo negativo, e.g. -3 % -2 es -1, -7 % -3 es -1, -8 % -3 es -2
               # TODO: en el caso que el operando es positivo y el operador negativo ambos se comportan igual (de mal?) e.g. 1 % -6 es -5, 10 % -8 es -6
    # DOUBLE/FLOAT
    # // avoid the divide if possible
	# const double lo = (double)0.;
	# if (in >= hi) {
	# 	in -= hi;
	# 	if (in < hi) return in;
	# } else if (in < lo) {
	# 	in += hi;
	# 	if (in >= lo) return in;
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

@scbuiltin
def wrap(x, lo, hi, range=None): # TODO: tiene dos firmas, sin y con range, la implementación varía sutilmente.
# INT: abajo define wrap para int sin range como:
# return sc_mod(in - lo, hi - lo + 1) + lo;
    if type(x) is int:
        lo = int(lo)
        hi = int(hi)
        return mod(x - lo, hi - lo + 1) + lo
	# // avoid the divide if possible
	# if (in >= hi) {
# range = hi - lo; # sin range
	# 	in -= range;
	# 	if (in < hi) return in;
	# } else if (in < lo) {
# range = hi - lo; # sin range
	# 	in += range;
	# 	if (in >= lo) return in;
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

@scbuiltin
def fold(x, lo, hi, range=None, range2=None): # TODO: ídem wrap con range y range2
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
	# 	in = hi + hi - in;
	# 	if (in >= lo) return in;
	# } else if (in < lo) {
	# 	in = lo + lo - in;
	# 	if (in < hi) return in;
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

@scbuiltin
def div(a, b): # TODO: define div para int devolviendo el dividendo si el divisor es cero, en sclang es el comportamiento de 1 div: 0, en Python 1 // 0 es error.
               # TODO: ver si se usa para las ugens o qué cómo, lo mismo con mod.
               # TODO: si lo sargumentos son float sclang realiza las operaciones y castead el valor de retorno.
	# int c;
	# if (b) {
	# 	if (a<0) c = (a+1)/b - 1;
	# 	else c = a/b;
	# } else c = a;
	# return c;
    if b:
        if a < 0: c = (a + 1) / b - 1
        else: c = a / b
    else:
        c = a
    return int(c)

@scbuiltin
def round(x, quant):
    # return quant==0. ? x : sc_floor(x/quant + .5) * quant;
    # INT return quant==0 ? x : sc_div(x + quant/2, quant) * quant;
    if type(x) is int:
        quant = int(quant)
        if quant == 0:
            return x
        else:
            return div(x + quant // 2, quant) * quant
    if quant == 0.:
        return x
    else:
        return floor(x / quant + .5) * quant

@scbuiltin
def roundup(x, quant):
    # return quant==0. ? x : sc_ceil(x/quant) * quant;
    # INT return quant==0 ? x : sc_div(x + quant - 1, quant) * quant;
    if type(x) is int:
        quant = int(quant)
        if quant == 0:
            return x
        else:
            return div(x + quant - 1, quant) * quant
    if quant == 0.:
        return x
    else:
        return ceil(x / quant) * quant

@scbuiltin
def trunc(x, quant): # BUG: TODO: esta ya la definió en unary pero con otra firma.
    # return quant==0. ? x : sc_floor(x/quant) * quant;
    # INT: return quant==0 ? x : sc_div(x, quant) * quant;
    if type(x) is int:
        quant = int(quant)
        if quant == 0:
            return x
        else:
            return div(x, quant) * quant
    if quant == 0.:
        return x
    else:
        return floor(x / quant) * quant

@scbuiltin
def atan2(a, b): # TODO: Solo la define para float. Pero creo que no define sin/cos y las demás.
    # return std::atan2(a, b);
    return math.atan2(a, b)

_SQRT2M1 = math.sqrt(2.) - 1.;

#./common/SC_BoundsMacros.h:
#define sc_abs(a) std::abs(a) # Use Python's
#define sc_max(a,b) (((a) > (b)) ? (a) : (b)) # Use Python's
#define sc_min(a,b) (((a) < (b)) ? (a) : (b)) # Use Python's
#inline T sc_clip(T x, U lo, V hi) return std::max(std::min(x, (T)hi), (T)lo);
@scbuiltin
def clip(x, lo, hi):
    T = type(x)
    return max(min(x, T(hi)), T(lo))

@scbuiltin
def hypotx(x, y):
	# double minxy;
	# x = std::abs(x);
	# y = std::abs(y);
	# minxy = sc_min(x,y);
	# return x + y - kDSQRT2M1 * minxy;
    x = abs(x)
    y = abs(y)
    minxy = min(x, y)
    return x + y - SQRT2M1 * minxy

@scbuiltin
def gcd(a, b):
# FLOAT: abajo define para float gcd(u, v)
# return (float) sc_gcd((long) std::trunc(u), (long) std::trunc(v));
    # if (a == 0)
    # 	return b;
    # if (b == 0)
    # 	return a;
    # const bool negative = (a <= 0 && b <= 0);
    # a = sc_abs(a);
    # b = sc_abs(b);
    # if (a == 1 || b == 1) {
    # 	if(negative) {
    # 		return (long) -1;
    # 	} else {
    # 		return (long) 1;
    # 	}
    # }
    # if (a < b) {
    # 	long t = a;
    # 	a = b;
    # 	b = t;
    # }
    # while (b > 0) {
    # 	long t = a % b;
    # 	a = b;
    # 	b = t;
    # }
    # if(negative) {
    # 	a = 0 - a;
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

@scbuiltin
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

@scbuiltin
def bitand(a, b): # BUG: estoy viendo que al pasar todo a minúsculas no me va a coincidir el nombre con la lista de símbolos...
    return a & b

@scbuiltin
def bitor(a, b):
    return a | b

@scbuiltin
def leftshift(a, b):
    return a << b

@scbuiltin
def rightshift(a, b):
    return a >> b

# @scbuiltin # TODO: VER
# def unsignedRightShift(a, b):
    # return (uint32)a >> b;

# @scbuiltin # TODO: VER: se usa solo en /server/plugins/LFUGens.cpp y hay un ejemplo en ServerPluginAPI.schelp
             # TODO: pero no creo que se use para nada más en ninguna otra parte.
# def powi(x, n):
#     # F z = 1;
#     # while (n != 0)
#     # {
#     # 	if ((n & 1) != 0)
#     # 	{
#     # 		z *= x;
#     # 	}
#     # 	n >>= 1;
#     # 	x *= x;
#     # }
#     # return z;
#     pass

@scbuiltin
def thresh(a, b): # sc_thresh(T a, U b)
    # return a < b ? (T)0 : a;
    T = type(a)
    if a < b: return T(0)
    return a

@scbuiltin
def clip2(a, b): # sc_clip2(T a, T b) # Estas son las que usa como operadores integrados de las UGens.
    # return sc_clip(a, -b, b);
    return clip(a, -b, b)

@scbuiltin
def wrap2(a, b): # wrap2(T a, T b)
    # return sc_wrap(a, -b, b);
    return wrap(a, -b, b)

@scbuiltin
def fold2(a, b): # sc_fold2(T a, T b)
    # return sc_fold(a, -b, b);
    return fold(a, -b, b)

@scbuiltin
def excess(a, b): # sc_excess(T a, T b)
    # return a - sc_clip(a, -b, b);
    return a - clip(a, -b, b)

@scbuiltin
def scaleneg(a, b):
    # template: T a, T b
	# if (a < 0)
	# 	return a*b;
	# else
	# 	return a;
    # DOUBLE/FLOAT
    # b = 0.5 * b + 0.5;
	# return (std::abs(a) - a) * b + a;
    if type(a) is int and type(b) is int:
        if a < 0: return a * b
        return a
    b = 0.5 * b + 0.5
    return (abs(a) - a) * b + a

@scbuiltin
def amclip(a, b):
    # template: T a, T b
	# if (b < 0)
	# 	return 0;
	# else
	# 	return a*b;
    # DOUBLE/FLOAT
    # return a * 0.5 * (b + std::abs(b));
    if type(a) is int and type(b) is int:
        if b < 0: return 0
        return a * b
    return a * 0.5 * (b + abs(b))

@scbuiltin
def ring1(a, b):
    return a * b + a

@scbuiltin
def ring2(a, b):
    return a * b + a + b

@scbuiltin
def ring3(a, b):
    return a * a * b

@scbuiltin
def ring4(a, b):
    return a * a * b - a * b * b

@scbuiltin
def difsqr(a, b):
    return a * a - b * b

@scbuiltin
def sumsqr(a, b):
    return a * a + b * b

@scbuiltin
def sqrsum(a, b):
    z = a + b
    return z * z

@scbuiltin
def sqrdif(a, b):
    z = a - b
    return z * z


# TODO: En AbstractFunction
#linrand
#bilinrand
#sum3rand # hay otras comentadas alrededor.
#coin
#digitValue
#thru ??

# complex y cartesian
#rho
#theta
#rotate
#dist

# Nary
# ...
