"""Operand.sc"""

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
        return type(self)(getattr(self.value, selector)())

    def compose_binop(self, selector, value):
        if isinstance(value, Operand):
            return type(self)(getattr(self.value, selector)(value.value))
        else:
            return type(self)(getattr(self.value, selector)(value))

    def compose_narop(self, selector, *args):
        return type(self)(getattr(self.value, selector)(*args))


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
