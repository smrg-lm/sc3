"""
builtins.py

Builtin functions from sclang.

Son los operadores unarios/(¿binarios?)/enarios de las
AbstractFunction y las UGen que también se aplican a otros
tipos de datos básico dentro de la librería de clases.

Son las funciones de _specialindex.py.

De no tener equivalentes estas funciones deberían implementarse
en CPython. En SuperCollider están implementadas a bajo nivel.

Ver:
/include/plugin_interface/SC_InlineUnaryOp.h
/include/plugin_interface/SC_InlineBinaryOp.h
"""

import math
#import inspect
#from functools import singledispatch

from . import functions as fn # TODO: desde la terminal, funciona solo si el otro módulo fue cargado antes.


# DONE: ver qué hacer con las listas de Python. RTA: EN PYTHON SE USA MAP Y
# LISTCOMPREHENSION, TRATAR DE HACERLA PYTÓNICA.

# DONE: ver qué hacer con los métodos mágicos de AbstractFucntion. RTA: EL PROBLEMA NO ES ABSTRACTFUNCTION
# SINO LOS TIPOS NUMÉRICOS INTEGRADOS, ABFUNC FUNCIONA CON LOS MÉTODOS INTEGRADOS NUMÉRICOS PERO LOS
# NÚMEROS NO VAN A FUNCIONAR CON MIDICPS, POR EJEMPLO. NO REIMPLEMENTAR LAS OPERACIONES PARA LOST TIPOS INTEGRADOS,
# NO REIMPLEMENTAR LOS MÉTODOS PARA LOS TIPOS INTEGRADOS (E.G. NEG).

# DONE: VER: https://docs.python.org/3/library/numbers.html#numbers.Integral
# implementa como if isinstance elif isinstance, tal vez @singledispatch
# genera una sobrecarga importante. Pero @singledispatch es relativamente
# nuevo, v3.4 o .5. En todo caso se puede cambiar después (o medir ahora...)

# TODO: ver módulo operator: https://docs.python.org/3/library/operator.html
# No estoy implementando los métodos inplace (e.g. a += b). Además el módulo
# provee funciones para las operaciones sobre tipos integrados, ver cuáles
# sí implementa y sin funcionan mediante los métodos mágicos.

# Decorator
def scbuiltin(func):
    def scbuiltin_(*args):
        # _MSG = "bad operand type for {}: '{}'"
        # try: # TODO: Ahora el único problema es que quede la cosa demasiado sobrecargada, y si agrego collections más.
        # except TypeError as e: raise TypeError(_MSG.format('midicps()', type(note).__name__)) from e
        if isinstance(args[0], fn.AbstractFunction):
            return fn.ValueOpFunction(func, *args)
        else:
            return func(*args)
    scbuiltin_.__qualname__ += func.__name__
    return scbuiltin_

# Unary

# TODO: es para denormals en ugens, pero el nombre está bueno.
# // this is a function for preventing pathological math operations in ugens.
# // can be used at the end of a block to fix any recirculating filter values.
# def zapgremlins(x):
#     float32 absx = std::abs(x);
#     // very small numbers fail the first test, eliminating denormalized numbers
#     //    (zero also fails the first test, but that is OK since it returns zero.)
#     // very large numbers fail the second test, eliminating infinities
#     // Not-a-Numbers fail both tests and are eliminated.
#     return (absx > (float32)1e-15 && absx < (float32)1e15) ? x : (float32)0.;

@scbuiltin
def log(x, base=math.e):
    return math.log(x, base)

@scbuiltin
def log2(x):
    return math.log2(x)

@scbuiltin
def log10(x):
    return math.log10(x)

@scbuiltin
def log1p(x): # VER: Creo que no existe como UGen
    return math.log1p(x)

# TODO: faltan sin/cos/etc.

_ONETWELFTH = 1/12
_ONE440TH = 1/440

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

# include/plugin_interface/SC_Constants.h
pi = math.pi # usa std::acos(-1.), en Python math.acos(-1.) == math.pi es True
pi2  = pi * 0.5
twopi = pi * 2

@scbuiltin
def hanwindow(x):
    # if (x < (float32)0. || x > (float32)1.) return (float32)0.;
    # return (float32)0.5 - (float32)0.5 * static_cast<float32>(cos(x * (float32)twopi));
    if x < 0. or x > 1.: return 0. # BUG: ver qué pasa si x es AbstractFunction en todas las comparaciones...
                                   # BUG: les tengo que implementar la lógica del tronco a todas estas funciones y las de arriba.
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

_ONESIXTH = 1/6

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

# SC_Constants.h # TODO: tal vez debería hacer un archivo a parte, o ponerlas todas arriba aunque no se usen.
log001 = math.log(0.001)

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

# TODO: ver el módulo operator: https://docs.python.org/3/library/operator.html VER NOTAS ARRIBA.
# ...
#lcm
#gcd
#...

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
