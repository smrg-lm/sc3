"""Operand.sc"""

from . import absobject as aob


__all__ = ['Operand']


class Operand(aob.AbstractObject):
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


    ### AbstractObject interface ###

    def _compose_unop(self, selector):
        return type(self)(selector(self.value))

    def _compose_binop(self, selector, other):
        a = self.value
        b = other.value if isinstance(other, Operand) else other
        return type(self)(selector(a, b))

    def _rcompose_binop(self, selector, other):
        a = other.value if isinstance(other, Operand) else other
        b = self.value
        return type(self)(selector(a, b))

    def _compose_narop(self, selector, *args):
        return type(self)(selector(self.value, *args))


    def __hash__(self):
        return self.value.__hash__()

    def __eq__(self, value):
        if isinstance(value, Operand):
            return self.value.__eq__(value.value)
        else:
            return self.value.__eq__(value)

    def __repr__(self):
        return f'{type(self).__name__}({repr(self.value)})'


    def __int__(self):
        return int(self.value)

    def __float__(self):
        return float(self.value)

    def __str__(self):
        return str(self.value)

    # printOn
    # storeOn
