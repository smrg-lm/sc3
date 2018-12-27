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
#from functools import singledispatch


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

# TODO: OTRA COSA, se puede asignar una función a una variable
# de instancia al declarar la clase. por ejemplo midicps = builtins.midicps.
# en ese caso tendría que pensar en los argumentos self y los nombres que
# se crean al usar singledispatch.

# Unary

_MSG = "bad operand type for {}: '{}'"

# TODO: Ver si realmente vale la pena implementar todo como función, tal vez
# lo pueda evitar por ahora.
# # Python unary '-' # Es usada como método de UGen. sig.neg()
# @singledispatch
# def neg(obj):
#     raise TypeError(_MSG.format('neg()', type(obj).__name__))
# @neg.register(AbstractFunction)
# @neg.register(float)
# @neg.register(int)
# def _(obj):
#     return obj.__neg__()
# # Python unary '+'
# @singledispatch
# def pos(obj):
#     raise TypeError(_MSG.format('pos()', type(obj).__name__))
# @pos.register(AbstractFunction)
# @pos.register(float)
# @pos.register(int)
# def _(obj):
#     return obj.__pos__()
# # __abs__ ya es builtin de Python
# # Python __invert__
# @singledispatch
# def bitnot(obj):
#     raise TypeError(_MSG.format('bitnot()', type(obj).__name__))
# @bitnot.register(AbstractFunction)
# @bitnot.register(float)
# @bitnot.register(int)
# def _(obj):
#     return obj.__invert__()
# # ...

_ONETWELFTH = 1/12
_ONE440TH = 1/440

def midicps(note):
    try: # TODO: VER: try evita dependencia cíclica, la otra es dejar que tiere el error de tipo que tira por defecto.
        # return (float64)440. * std::pow((float64)2., (note - (float64)69.) * (float64)0.08333333333333333333333333);
        return 440. * pow(2., (note - 69.) * _ONETWELFTH) # TODO: la múltiplicación de opfunc no funciona para floats? pow anda bien.
    except TypeError as e:
        raise TypeError(_MSG.format('midicps()', type(note).__name__)) from e

def cpsmidi(freq):
    try:
        # return sc_log2(freq * (float64)0.002272727272727272727272727) * (float64)12. + (float64)69.;
        return math.log2(freq * _ONE440TH) * 12. + 69.
    except TypeError as e:
        raise TypeError(_MSG.format('cpsmidi()', type(freq).__name_)) from e

# @singledispatch
# def __(obj):
#     raise TypeError(_msg.format(obj.__class__.__name__, '__()'))
# @__.register(AbstractFunction)
# @__.register(float)
# @__.register(int)
# def _(obj):
#     return
#

# @singledispatch
# def __(obj):
#     raise TypeError(_msg.format(obj.__class__.__name__, '__()'))
# @__.register(AbstractFunction)
# @__.register(float)
# @__.register(int)
# def _(obj):
#     return
#


# Binary
# TODO: ver el módulo operator: https://docs.python.org/3/library/operator.html


# Nary

#@singledispatch
def clip():
    pass
#@singledispatch
def wrap():
    pass
#@singledispatch
def fold():
    pass
# @singledispatch
# def __(obj):
#     raise TypeError(_msg.format(obj.__class__.__name__, '__()'))
# @__.register(AbstractFunction)
# @__.register(float)
# @__.register(int)
# def _(obj):
#     return
#
