"""Operand.sc"""

import operator

from . import functions as fn


class Operand(fn.AbstractFunction):
    def __init__(self, value=None):
        if isinstance(value, Operand):
            self.value = value.value
        else:
            self.value = value

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        self.__value = value


    ### AbstractFunction interface ###

    def compose_unop(self, selector):
        if hasattr(selector, '__scbuiltin__'):
            return type(self)(selector(self.value))
        else:
            return type(self)(getattr(operator, selector)(self.value))

    def compose_binop(self, selector, other):
        a = self.value
        b = other.value if isinstance(other, Operand) else other
        if hasattr(selector, '__scbuiltin__'):
            return type(self)(selector(a, b))
        else:
            return type(self)(getattr(operator, selector)(a, b))

    def rcompose_binop(self, selector, other):
        a = other.value if isinstance(other, Operand) else other
        b = self.value
        if hasattr(selector, '__scbuiltin__'):
            return type(self)(selector(a, b))
        else:
            return type(self)(getattr(operator, selector)(a, b))

    def compose_narop(self, selector, *args):
        if hasattr(selector, '__scbuiltin__'):
            return type(self)(selector(self.value, *args))
        else:
            raise Exception(f'*** BUG: nary op {selector} is not in builtins')
            # return type(self)(getattr(self.value)(*args))  # *** BUG: narop would be just Python methods.

    def __hash__(self):
        return self.value.__hash__()

    def __eq__(self, value):
        if isinstance(value, Operand):
            return self.value.__eq__(value.value)
        else:
            return self.value.__eq__(value)

    def __repr__(self):
        return f'{type(self).__name__}({self.value})'

    # printOn
    # storeOn
