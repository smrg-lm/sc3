"""
builtins.py

Builtin functions from sclang.

Son los operadores unarios/(¿binarios?)/enarios de las
AbstractFunction y las UGen que también se aplican a otros
tipos de datos básico dentro de la librería de clases.

Son las funciones de _specialindex.py.

De no tener equivalentes estas funciones deberían implementarse
en CPython. En SuperCollider están implementadas a bajo nivel.
"""

from functools import singledispatch


# TODO: ver qué hacer con los métodos mágicos de AbstractFucntion.
# TODO: ver qué hacer con las listas de Python.
# TODO: ver módulo operator: https://docs.python.org/3/library/operator.html

# TODO: VER: https://docs.python.org/3/library/numbers.html#numbers.Integral
# implementa como if isinstance elif isinstance, tal vez @singledispatch
# genera una sobrecarga importante.

# Unary

_MSG = "bad operand type for {}: '{}'"

# Python unary '-' # TODO: Es usada como método de UGen. sig.neg()
@singledispatch
def neg(obj):
    raise TypeError(_MSG.format('neg()', type(obj).__name__))
@neg.register(AbstractFunction)
@neg.register(int)
@neg.register(float)
def _(obj):
    return obj.__neg__()

# Python unary '+'
@singledispatch
def pos(obj):
    raise TypeError(_MSG.format('pos()', type(obj).__name__))
@pos.register(AbstractFunction)
@pos.register(int)
@pos.register(float)
def _(obj):
    return obj.__pos__()

# __abs__ ya es builtin de Python

# Python __invert__
@singledispatch
def bitnot(obj):
    raise TypeError(_MSG.format('bitnot()', type(obj).__name__))
@bitnot.register(AbstractFunction)
@bitnot.register(int)
@bitnot.register(float)
def _(obj):
    return obj.__invert__()

# @singledispatch
# def __(obj):
#     raise TypeError(_msg.format(obj.__class__.__name__, '__()'))
# @__.register( type )
# @__.register( type )
# def _(obj):
#     return
#
# @singledispatch
# def __(obj):
#     raise TypeError(_msg.format(obj.__class__.__name__, '__()'))
# @__.register( type )
# @__.register( type )
# def _(obj):
#     return
#
# @singledispatch
# def __(obj):
#     raise TypeError(_msg.format(obj.__class__.__name__, '__()'))
# @__.register( type )
# @__.register( type )
# def _(obj):
#     return


# Binary
# TODO: ver el módulo operator: https://docs.python.org/3/library/operator.html


# Nary

@singledispatch
def clip():
    pass
@singledispatch
def wrap():
    pass
@singledispatch
def fold():
    pass
# @singledispatch
# def __(obj):
#     raise TypeError(_msg.format(obj.__class__.__name__, '__()'))
# @__.register( type )
# @__.register( type )
# def _(obj):
#     return
#
# @singledispatch
# def __(obj):
#     raise TypeError(_msg.format(obj.__class__.__name__, '__()'))
# @__.register( type )
# @__.register( type )
# def _(obj):
#     return
