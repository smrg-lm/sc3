"""Operand.sc"""

import sc3.functions as fn


class Operand(fn.AbstractFunction):
    def __call__(self, *args):
        return self.value

    def __init__(self, value=None):
        if isinstance(value, type(Operand)): # NOTE: es dereferenceOperand que solo se usa para este caso, igual me falta ver el uso global de esta clase y Rest.
            self.value = value.value
        else:
            self.value = value

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        self.__value = value

    # TODO: sigue ... Rest hereda de esta clase
