"""
functions tal vez sería un sub paquete

AbstractFunction es el corazón de todos
los comportamientos de las UGens. Así está
integrado en sclang y es lo que posibilita
lazyeval/proxy como si fuera un parser de las
definiciones. Los patterns, las rutinas, las
funciones también son AbstractFunctions. Las
rutinas además son streams.

Las indicación para emular tipos numéricos están
en https://docs.python.org/3/reference/datamodel.html
por ejemplo (#object.__rmul__)
"""

import inspect


# ver abstract base clases in python
class AbstractFunction(object):
    # callable
    def __call__(self, *args): # no se llama
        raise NotImplementedError('AbstractFunction is an abstract class.')

    # OC: function compositions
    # override these in subclasses to perform
    # different kinds of function compositions
    def compose_unop(self, selector):
        return UnaryOpFunction(selector, self)
    def compose_binop(self, selector, other):
        return BinaryOpFunction(selector, self, other)
    # def compose_rbinop(self, selector, other): # puede que no sea necesario, salvo otras operaciones de sclang, pero BinaryOpFunction usa rmethod y habría que cambiarlo también
    #     return BinaryOpFunction(selector, other, self)
    def compose_narop(self, selector, *args): # , **kwargs): # si? no? no, si? si, no, no, si, si?
        return NAryOpFunction(selector, self, *args) #, **kwargs)

    # https://docs.python.org/3/library/operator.html
    # Categories: object comparison, logical operations, mathematical operations and sequence operations

    # Leyendo: https://docs.python.org/3/reference/datamodel.html#objects veo que no debería usar is
    # para la comparación de leng() con int o entre strings. "after a = 1; b = 1, a and b may or may not refer to the same object with the value one"
    # semánticamente == e is son diferentes, aunque x is y implies x == y viceversa no es verdad.

    # Values comparison:
    # https://docs.python.org/3/reference/expressions.html#comparisons
    # Rich comparison:
    # https://docs.python.org/3/reference/datamodel.html#object.__lt__

    # Basic custimization:
    # https://docs.python.org/3/reference/datamodel.html#customization

    # unary operators

    def __neg__(self):
        return self.compose_unop('__neg__') # -
    def __pos__(self):
        return self.compose_unop('__pos__') # +
    def __abs__(self):
        return self.compose_unop('__abs__') # abs() # TODO: ver builtins
    def __invert__(self):
        return self.compose_unop('__invert__') # ~ bitwise inverse, depende de la representación

    # conversion
    # def __complex__(self): # builtin complex() # TODO: acá las builtins llamam directamente al método mágico, pero estas funciones tienen que retornar un objeto del tipo, no pueden retornar una función abstracta, y deberían evaluar la función perdiendo su lazzyness
    #     return self.compose_unop('__complex__')
    # def __int__(self): # builtin int()
    #     return self.compose_unop('__int__')
    # def __float__(self): # builtin float()
    #     return self.compose_unop('__float__')
    # object.__index__(self) # tiene que retornar int

    def __round__(self): # TODO: object.__round__(self[, ndigits]) OPERADOR UNARIO QUE RECIBE ARGUMENTOS.
        return self.compose_unop('__round__')
    def __trunc__(self):
        return self.compose_unop('__trunc__')
    def __floor__(self):
        return self.compose_unop('__floor__')
    def __ceil__(self):
        return self.compose_unop('__ceil__')

    # binary operators

    # Mathematical operations
    # https://docs.python.org/3/reference/expressions.html#binary-arithmetic-operations
    # https://docs.python.org/3/reference/datamodel.html#emulating-numeric-types
    def __add__(self, other): # +
        return self.compose_binop('__add__', other)
    def __radd__(self, other):
        return self.compose_binop('__radd__', other)
    def __sub__(self, other): # -
        return self.compose_binop('__sub__', other)
    def __rsub__(self, other):
        return self.compose_binop('__rsub__', other)
    def __mul__(self, other): # *
        return self.compose_binop('__mul__', other)
    def __rmul__(self, other):
        return self.compose_binop('__rmul__', other)
    def __matmul__(self, other): # @
        return self.compose_binop('__matmul__', other)
    def __rmatmul__(self, other):
        return self.compose_binop('__rmatmul__', other)
    def __truediv__(self, other): # /
        return self.compose_binop('__truediv__', other)
    def __rtruediv__(self, other):
        return self.compose_binop('__rtruediv__', other)
    def __floordiv__(self, other): # //
        return self.compose_binop('__floordiv__', other)
    def __rfloordiv__(self, other):
        return self.compose_binop('__rfloordiv__', other)
    def __mod__(self, other): # %
        return self.compose_binop('__mod__', other)
    def __rmod__(self, other):
        return self.compose_binop('__rmod__', other)
    def __divmod__(self, other): # divmod() # __floordiv__() and __mod__()
        return self.compose_binop('__divmod__', other)
    def __rdivmod__(self, other):
        return self.compose_binop('__rdivmod__', other)
    def __pow__(self, other): # pow(), **, object.__pow__(self, other[, modulo])
        return self.compose_binop('__pow__', other)
    def __rpow__(self, other):
        return self.compose_binop('__rpow__', other)
    def __lshift__(self, other): # <<
        return self.compose_binop('__lshift__', other)
    def __rlshift__(self, other):
        return self.compose_binop('__rlshift__', other)
    def __rshift__(self, other): # >>
        return self.compose_binop('__rshift__', other)
    def __rrshift__(self, other):
        return self.compose_binop('__rrshift__', other)
    def __and__(self, other): # &
        return self.compose_binop('__and__', other)
    def __rand__(self, other):
        return self.compose_binop('__rand__', other)
    def __xor__(self, other): # ^
        return self.compose_binop('__xor__', other)
    def __rxor__(self, other):
        return self.compose_binop('__rxor__', other)
    def __or__(self, other): # |
        return self.compose_binop('__or__', other)
    def __ror__(self, other):
        return self.compose_binop('__ror__', other)

    # nary operators

    # TODO: los operadores enarios deberían ser implementados por duplicado
    # como las funciones incluidas para los tipos numéricos.
    def clip(self, lo, hi):
        return self.compose_narop('clip', lo, hi)
    def wrap(self, lo, hi):
        return self.compose_narop('wrap', lo, hi)
    def fold(self, lo, hi):
        return self.compose_narop('fold', lo, hi)
    # ...


class UnaryOpFunction(AbstractFunction):
    def __init__(self, selector, a):
        self.selector = selector
        self.a = a

    def __call__(self, *args): # los parámetros solo pueden ser posicionales
        #if callable(a): a siempre va a ser una AbstractFunction no usar rbinop
        return getattr(self.a(*args), self.selector)() # qué pasa con los tipos de retorno de a() ... (ver NotImplementedError)


class BinaryOpFunction(AbstractFunction):
    def __init__(self, selector, a, b):
        self.selector = selector
        self.a = a
        self.b = b

    def __call__(self, *args):
        if callable(self.b):
            return getattr(self.a(*args), self.selector)(self.b(*args))
        else:
            # BUG: int.__mul__(float) devuelve NotImplemented, deberíá llamar float.__mul__(int)
            # BUG: proque int.__rmul__(float) tampoco funciona, y supongo que otras operaciones lo mismo.
            # BUG: entonces tengo que hacer un catch de NotImplemented en cada OpFunction y/o comprobar
            # BUG: los tipos. ¿Cómo implementa '*' Python?
            return getattr(self.a(*args), self.selector)(self.b)


class NAryOpFunction(AbstractFunction):
    def __init__(self, selector, a, *args): # **kwargs?
        self.selector = selector
        self.a = a
        self.args = args

    def __call__(self, *args):
        return getattr(self.a(*args), self.selector)(*self.args)


# class FunctionList(AbstractFunction):
#     pass


# sería un docorador, tal vez es lo mejor, lo mismo con
# routine y task, y tal vez patterns y, por qué no, ugens
# si logro idear el modelo de más alto nivel.
# esto tal vez va en otro archivo, y ver eso de FunctionList,
# por qué está en el mismo archivo sc que AbstractFunction.
# Y ver qué otros recursos de la programación funcional
# podrían ser aplicables, por ejemplo de functools.
class function(AbstractFunction):
    # VER: https://docs.python.org/3/library/inspect.html#inspect.Signature
    def __init__(self, func):
        if inspect.isfunction(func):
            self._nargs = len(inspect.signature(func).parameters)
            self.func = func
        else:
            msg = '@function decorator can not be applied to classes'
            raise TypeError(msg)

    def __call__(self, *args): # no kwargs
        '''Parameters can only be positional (no keywords), remnant
        is discarded, more or less like sclang valueArray.'''
        return self.func(*args[:self._nargs])


# Caso:
# @function
# def f1():
#      return 100
#
# @function
# def f2():
#     return "oa"
#
# g = f1 + f2
# g -> <supercollie.functions.BinaryOpFunction at 0x...>
# g() -> NotImplemented
#
# No queda claro quién no implementa qué. Y los errores
# de xopfunctions anidados van a return getattr(self.a(), self.selector)()
# y similares sin mayor explicación. Hay que implementar un mecanismo
# de excepciones.

# Visto: qué pasa cuando las funciones tiene argumentos
# sin parámetros por defecto en sclang. Respuesta:
# se los pasa posicionalmente a todas las funciones
# por igual. Acá si no coincide la cantidad de argumentos
# tira takes n error. Pero, se podría agregar en __call__
# de cada XOpFunciton checkeando? O, solo por kwords?
# ejemplo:
# h = f + g
# h(100)
# como está, sin *args ni **kwargs evita que se le pasen
# argumentos porque solo 1 (self) es esperado en XOpFunction.__call__
# Creo que por eso sclang usa valueArray, pero no le veo
# un sentido muy concreto si hay cadena/anidameiento
# de varios XOpFunction.
