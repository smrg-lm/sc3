"""AbstractFunction.sc"""

import inspect
import operator

from . import builtins as bi # TODO: TEST, ver abajo.
from . import graphparam as gpp


class AbstractFunction(gpp.UGenParameter):
    def __init__(self):
        pass  # Don't call GraphParameter.__init__

    def __call__(self, *args):
        raise NotImplementedError(
            f'callable interface has no use for {type(self).__name__}')


    ### AbstractFunction interface ###
    # // override these in subclasses to perform
    # // different kinds of function compositions

    def compose_unop(self, selector):
        return UnaryOpFunction(selector, self)

    def compose_binop(self, selector, other):
        return BinaryOpFunction(selector, self, other)

    def rcompose_binop(self, selector, other):
        return BinaryOpFunction(selector, other, self)

    def compose_narop(self, selector, *args):
        return NAryOpFunction(selector, self, *args)


    # TODO: ver módulo operator: https://docs.python.org/3/library/operator.html
    # No estoy implementando los métodos inplace (e.g. a += b), por defecto
    # cae en la implementación de __add__ y __radd__, por ejemplo.
    # Además el módulo provee funciones para las operaciones sobre tipos integrados,
    # ver cuáles sí implementa y sin funcionan mediante los métodos mágicos.

    # https://docs.python.org/3/library/operator.html
    # Categories: object comparison, logical operations, mathematical operations and sequence operations


    # unary operators

    def __neg__(self):
        return self.compose_unop('neg') # -

    def __pos__(self):
        return self.compose_unop('pos') # + # BUG: no está en _specialindex

    def __abs__(self):
        return self.compose_unop('abs') # abs()

    def __invert__(self):
        return self.compose_unop('invert') # ~ bitwise inverse, depende de la representación

    # conversion
    # def __complex__(self): # builtin complex() # TODO: acá las builtins llamam directamente al método mágico, pero estas funciones tienen que retornar un objeto del tipo, no pueden retornar una función abstracta, y deberían evaluar la función perdiendo su lazzyness
    #     return self.compose_unop('__complex__')
    # def __int__(self): # builtin int()
    #     return self.compose_unop('__int__')
    # def __float__(self): # builtin float()
    #     return self.compose_unop('__float__')
    # object.__index__(self) # tiene que retornar int
    # Python's builtin round and math trunc/floor/ceil
    # def __round__(self): # TODO: object.__round__(self[, ndigits]) OPERADOR UNARIO QUE RECIBE ARGUMENTOS.
    #     return self.compose_unop('__round__')
    # def __trunc__(self):
    #     return self.compose_unop('__trunc__')
    # def __floor__(self):
    #     return self.compose_unop('__floor__')
    # def __ceil__(self):
    #     return self.compose_unop('__ceil__')

    def log(self): # BUG [,base] ES BINARIO, LO MISMO QUE PASA CON POW
        return self.compose_unop(bi.log)

    def log2(self):
        return self.compose_unop(bi.log2)

    def log10(self):
        return self.compose_unop(bi.log10)

    # def log1p(self):
    #     return self.compose_unop(bi.log1p)

    def exp(self):
        return self.compose_unop(bi.exp)

    def sin(self):
        return self.compose_unop(bi.sin)

    def cos(self):
        return self.compose_unop(bi.cos)

    def tan(self):
        return self.compose_unop(bi.tan)

    def asin(self):
        return self.compose_unop(bi.asin)

    def acos(self):
        return self.compose_unop(bi.acos)

    def atan(self):
        return self.compose_unop(bi.atan)

    def sinh(self):
        return self.compose_unop(bi.sinh)

    def cosh(self):
        return self.compose_unop(bi.cosh)

    def tanh(self):
        return self.compose_unop(bi.tanh)

    # def asinh(x):
    #     return self.compose_unop(bi.asinh)

    # def acosh(x):
    #     return self.compose_unop(bi.acosh)

    # def atanh(x):
    #     return self.compose_unop(bi.atanh)

    def midicps(self):
        return self.compose_unop(bi.midicps)

    def cpsmidi(self):
        return self.compose_unop(bi.cpsmidi)

    def midiratio(self):
        return self.compose_unop(bi.midiratio)

    def ratiomidi(self):
        return self.compose_unop(bi.ratiomidi)

    def octcps(self):
        return self.compose_unop(bi.octcps)

    def cpsoct(self):
        return self.compose_unop(bi.cpsoct)

    def ampdb(self):
        return self.compose_unop(bi.ampdb)

    def dbamp(self):
        return self.compose_unop(bi.dbamp)

    def squared(self):
        return self.compose_unop(bi.squared)

    def cubed(self):
        return self.compose_unop(bi.cubed)

    def sqrt(self):
        return self.compose_unop(bi.sqrt)

    # TODO: FALTA, SEGUIR LA INTERFAZ DE ABSTRACTFUNCTION EN SCLANG,
    # E IR COMPROBANDO LOS MÉTODOS.


    # binary operators

    # Mathematical operations
    # https://docs.python.org/3/reference/expressions.html#binary-arithmetic-operations
    # https://docs.python.org/3/reference/datamodel.html#emulating-numeric-types
    def __add__(self, other): # +
        return self.compose_binop('add', other)

    def __radd__(self, other):
        return self.rcompose_binop('add', other)

    def __sub__(self, other): # -
        return self.compose_binop('sub', other)

    def __rsub__(self, other):
        return self.rcompose_binop('sub', other)

    def __mul__(self, other): # *
        return self.compose_binop('mul', other)

    def __rmul__(self, other):
        return self.rcompose_binop('mul', other)

    # def __matmul__(self, other): # @
    #     return self.compose_binop('matmul', other)

    # def __rmatmul__(self, other):
    #     return self.rcompose_binop('matmul', other)

    def __truediv__(self, other): # /
        return self.compose_binop('truediv', other)

    def __rtruediv__(self, other):
        return self.rcompose_binop('truediv', other)

    def __floordiv__(self, other): # //
        return self.compose_binop('floordiv', other)

    def __rfloordiv__(self, other):
        return self.rcompose_binop('floordiv', other)

    def __mod__(self, other): # %
        return self.compose_binop(bi.mod, other)

    def __rmod__(self, other):
        return self.rcompose_binop(bi.mod, other)

    # def __divmod__(self, other): # divmod(), método integrado
    #     return self.compose_binop('divmod', other)

    # def __rdivmod__(self, other):
    #     return self.rcompose_binop('divmod', other)

    def __pow__(self, other): # pow(), **, object.__pow__(self, other[, modulo])
        return self.compose_binop('pow', other)

    def __rpow__(self, other):
        return self.rcompose_binop('pow', other)

    def __lshift__(self, other): # <<
        return self.compose_binop('lshift', other)

    def __rlshift__(self, other):
        return self.rcompose_binop('lshift', other)

    def __rshift__(self, other): # >>
        return self.compose_binop('rshift', other)

    def __rrshift__(self, other):
        return self.rcompose_binop('rshift', other)

    def __and__(self, other): # &
        return self.compose_binop('and', other)

    def __rand__(self, other):
        return self.rcompose_binop('and', other)

    def __xor__(self, other): # ^
        return self.compose_binop('xor', other)

    def __rxor__(self, other):
        return self.rcompose_binop('xor', other)

    def __or__(self, other): # |
        return self.compose_binop('or', other)

    def __ror__(self, other):
        return self.rcompose_binop('or', other)

    # Values comparison:
    # https://docs.python.org/3/reference/expressions.html#comparisons
    # Rich comparison:
    # https://docs.python.org/3/reference/datamodel.html#object.__lt__
    # hashable
    # https://docs.python.org/3/glossary.html#term-hashable
    # "Hashable objects which compare equal must have the same hash value." (__hash__ y __eq__)

    def __lt__(self, other): # <
        return self.compose_binop('__lt__', other)

    def __le__(self, other): # <=
        return self.compose_binop('__le__', other)

    # def __eq__(self, other): # == # ESTE MÉTODO NO SE IMPLEMENTA NI EN AbstractFunction NI EN UGen. Aunque está en la tabla de ops.
    #     return self.compose_binop('__eq__', other)

    # def __ne__(self, other): # != # ESTE MÉTODO NO SE IMPLEMENTA NI EN AbstractFunction NI EN UGen. Aunque está en la tabla de ops.
    #     return self.compose_binop('__ne__', other)

    def __gt__(self, other): # >
        return self.compose_binop('__gt__', other)

    def __ge__(self, other): # >=
        return self.compose_binop('__ge__', other)


    # nary operators

    # TODO: los operadores enarios deberían ser implementados por duplicado
    # como las funciones incluidas para los tipos numéricos. VER MIDICPS Y MOD ARRIBA.

    def clip(self, lo, hi):
        return self.compose_narop(bi.clip, lo, hi)

    def wrap(self, lo, hi):
        return self.compose_narop(bi.wrap, lo, hi)

    def fold(self, lo, hi):
        return self.compose_narop(bi.fold, lo, hi)

    # TODO...


    ### UGen graph parameter interface ###

    def is_valid_ugen_input(self):
        return True

    def as_ugen_input(self, *ugen_cls):
        return self(*ugen_cls)

    def as_control_input(self):
        return self()

    def as_audio_rate_input(self, *args):
        res = self(*args)
        if gpp.ugen_param(res).as_ugen_rate() != 'audio':
            return xxx.K2A.ar(res)
        return res


class UnaryOpFunction(AbstractFunction):
    def __init__(self, selector, a):
        self.selector = selector
        self.a = a

    def __call__(self, *args, **kwargs):
        if hasattr(self.selector, '__scbuiltin__'):
            return self.selector(self.a(*args, **kwargs))
        else:
            return getattr(operator, self.selector)(self.a(*args, **kwargs))


class BinaryOpFunction(AbstractFunction):
    def __init__(self, selector, a, b):
        self.selector = selector
        self.a = a
        self.b = b

    def __call__(self, *args, **kwargs):
        a_value = self.a(*args, **kwargs) if callable(self.a) else self.a
        b_value = self.b(*args, **kwargs) if callable(self.b) else self.b
        if hasattr(self.selector, '__scbuiltin__'):
            return self.selector(a_value, b_value) # los scbuiltins se encargan de los tipos, incluso AbstractFunction (problema para posible cythonización)
        else:
            return getattr(operator, self.selector)(a_value, b_value)


class NAryOpFunction(AbstractFunction):
    def __init__(self, selector, a, *args):
        self.selector = selector
        self.a = a
        self.args = args

    def __call__(self, *args, **kwargs):
        evaluated_args = [x(*args, **kwargs) if isinstance(x, Function) else x\
                          for x in self.args]
        if hasattr(self.selector, '__scbuiltin__'):
            return self.selector(self.a(*args, **kwargs), *evaluated_args)
        else:
            raise Exception(f'*** BUG: nary op {self.selector} is not in builtins')
            # return getattr(self.a(*args, **kwargs), self.selector)(*evaluated_args)  # *** BUG: narop would be just Python methods.


# class FunctionList(AbstractFunction):
#     pass


# *** TODO: completar las operaciones que faltan e ir haciendo los test con
# *** TODO: Function teniendo en cuenta la próxima cythonización.


### Function.sc ###

class Function(AbstractFunction):
    def __init__(self, func):
        if inspect.isfunction(func):
            parameters = inspect.signature(func).parameters
            self._nargs = len(parameters)
            self._kwords = parameters.keys()
            self.func = func
        else:
            raise TypeError(
                'Function wrapper only apply to user-defined functions')

    def __call__(self, *args, **kwargs):
        kwargs = {k: kwargs[k] for k in kwargs.keys() & self._kwords}
        return self.func(*args[:self._nargs], **kwargs)

    def __awake__(self, beats, seconds, clock):  # Function, Routine, PauseStream, (Nil, Object).
        return self(beats, seconds, clock)


# decorator syntax
def function(func):
    return Function(func)


# Thunk
# UGenThunk
