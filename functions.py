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

import supercollie.builtins as bi # TODO: TEST, ver abajo.


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

    # TODO: ver módulo operator: https://docs.python.org/3/library/operator.html
    # No estoy implementando los métodos inplace (e.g. a += b), por defecto
    # cae en la implementación de __add__ y __radd__, por ejemplo.
    # Además el módulo provee funciones para las operaciones sobre tipos integrados,
    # ver cuáles sí implementa y sin funcionan mediante los métodos mágicos.

    # https://docs.python.org/3/library/operator.html
    # Categories: object comparison, logical operations, mathematical operations and sequence operations

    # Leyendo: https://docs.python.org/3/reference/datamodel.html#objects veo que no debería usar is
    # para la comparación de leng() con int o entre strings. "after a = 1; b = 1, a and b may or may not refer to the same object with the value one"
    # semánticamente == e is son diferentes, aunque x is y implies x == y viceversa no es verdad.

    # Basic custimization:
    # https://docs.python.org/3/reference/datamodel.html#customization

    # unary operators

    def __neg__(self):
        return self.compose_unop('__neg__') # -
    def __pos__(self):
        return self.compose_unop('__pos__') # + # BUG: no está en _specialindex
    def __abs__(self):
        return self.compose_unop('__abs__') # abs()
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
    def exp(x):
        return self.compose_unop(bi.exp)
    def sin(x):
        return self.compose_unop(bi.sin)
    def cos(x):
        return self.compose_unop(bi.cos)
    def tan(x):
        return self.compose_unop(bi.tan)
    def asin(x):
        return self.compose_unop(bi.asin)
    def acos(x):
        return self.compose_unop(bi.acos)
    def atan(x):
        return self.compose_unop(bi.atan)
    def sinh(x):
        return self.compose_unop(bi.sinh)
    def cosh(x):
        return self.compose_unop(bi.cosh)
    def tanh(x):
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
    # def __matmul__(self, other): # @
    #     return self.compose_binop('__matmul__', other)
    # def __rmatmul__(self, other):
    #     return self.compose_binop('__rmatmul__', other)
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
    # def __divmod__(self, other): # divmod(), método integrado
    #     return self.compose_binop('__divmod__', other)
    # def __rdivmod__(self, other):
    #     return self.compose_binop('__rdivmod__', other)
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


    def mod(self, other):
        return self.compose_binop(bi.mod, other)

    # nary operators

    # TODO: los operadores enarios deberían ser implementados por duplicado
    # como las funciones incluidas para los tipos numéricos. VER MIDICPS Y MOD ARRIBA.
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

    def __call__(self, *args): # TODO: los parámetros solo pueden ser posicionales, supongo que se podrían agregar palabras clase si se hace el filtrado.
        if hasattr(self.selector, '__scbuiltin__'):
            return self.selector(self.a(*args))
        else:
            return getattr(self.a(*args), self.selector)() # TODO: qué pasa con los tipos de retorno de a() ... (ver NotImplementedError)

class BinaryOpFunction(AbstractFunction):
    def __init__(self, selector, a, b):
        self.selector = selector
        self.a = a
        self.b = b

    def __call__(self, *args):
        a_value = self.a(*args)
        if callable(self.b): # TODO: puede ser cualquier función, pero podría restringirse a AbstractFunction, en sclang todo es AbstractFunction
            b_value = self.b(*args)

        if hasattr(self.selector, '__scbuiltin__'):
            return self.selector(a_value, b_value) # los scbuiltins se encargan de los tipos.

        ret_value = getattr(a_value, self.selector)(b_value)
        if ret_value is NotImplemented and type(a_value) is int and type(self.b) is float: # TODO: ver qué pasa con otros operadores integrados.
            return getattr(float(a_value), self.selector)(self.b)

        return ret_value


class NAryOpFunction(AbstractFunction):
    def __init__(self, selector, a, *args): # **kwargs?
        self.selector = selector
        self.a = a
        self.args = args

    def __call__(self, *args):
        evaluated_args = [x(*args) if isinstance(x, AbstractFunction) else x for x in self.args]
        if hasattr(self.selector, '__scbuiltin__'):
            return self.selector(self.a(*args), *evaluated_args)
        else:
            return getattr(self.a(*args), self.selector)(*evaluated_args)


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
