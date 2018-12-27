"""
Special Index and Symbols

El índice sale de las enum en Opcodes.h y se mapean a símbolos en
PyrParseNode.cpp initSpecialSelectors().

Acá los nombres de los índices opcodes (en Opcodes.h) son los
nombres de los selectores (en PyrParseNode).

Used by BasicOpUGens to get an ID number for the operator.
"""

from enum import Enum


UnaryOpcodes = Enum(
    'UnaryOpcodes',
    [
        'neg', # __neg__
        'not', # es not buleano, operator.not_(obj)/operator.__not__(obj)
        'isNil',
        'notNil',
        'bitNot', # __invert__
        'abs', # __abs__, es builtin
        'asFloat',
        'asInt',
        'ceil', # __ceil__
        'floor', # __floor__
        'frac', # math.modf, no se comporta igual
        'sign', # no existe
        'squared', # no existe
        'cubed', # no existe
        'sqrt', # math.sqrt(x), VER: se comporta raro en sclang, no entiendo.
        'exp', # e to the power of the receiver. math.exp(x)
        'reciprocal', # 1 / this

        'midicps',
        'cpsmidi',
        'midiratio',
        'ratiomidi',
        'dbamp',
        'ampdb',
        'octcps',
        'cpsoct',
        'log', # math.log
        'log2',
        'log10',
        'sin', # math
        'cos', # etc...
        'tan',
        'asin',
        'acos',
        'atan',
        'sinh',
        'cosh',
        'tanh',
        'rand', # VER que hay en Python
        'rand2',
        'linrand',
        'bilinrand',

        #'exprand',
        #'biexprand',
        'sum3rand',
        #'gammarand',
        #'gaussrand',
        #'poirand',

        'distort',
        'softclip',
        'coin',

        'digitValue',
        'silence',
        'thru',
        'rectWindow',
        'hanWindow',
        'welWindow',
        'triWindow',

        'ramp',
        'scurve',

        #opNumUnarySelectors
    ],
    start=0
)


BinaryOpcodes = Enum(
    'UnaryOpcodes',
    [
        '+', # TODO: __add__ __radd__ __iadd__ y no van a funcionar porque en Enum son métodos.
        '-',
        '*', # __mul__ __rmul__ __imul__
        'div', # Python '//' (__floordiv__)
        '/',
        'mod',
        '==',
        '!=',
        '<',
        '>',
        '<=',
        '>=',
        #'===', # Python is
        #'!==', # Python is not

        'min',
        'max',
        'bitAnd',
        'bitOr',
        'bitXor',
        'lcm',
        'gcd',
        'round', # __round__ es Unario con argumento
        'roundUp',
        'trunc', # __truc__ es Unario, es la operación por defecto para int(x)
        'atan2',
        'hypot',
        'hypotApx',
        'pow',
        'leftShift',
        'rightShift',
        'unsignedRightShift',
        'fill',
        'ring1', # a * (b + 1) == a * b + a
        'ring2', # a * b + a + b
        'ring3', # a*a*b
        'ring4', # a*a*b - a*b*b
        'difsqr', # a*a - b*b
        'sumsqr', # a*a + b*b
        'sqrsum', # (a + b)^2
        'sqrdif', # (a - b)^2
        'absdif', # |a - b|
        'thresh',
        'amclip',
        'scaleneg',
        'clip2',
        'excess',
        'fold2',
        'wrap2',
        'firstArg',
        'rrand',
        'exprand',

        #opNumBinarySelectors
    ],
    start=0
)


def special_index(operator):
    try:
        return UnaryOpcodes[operator].value
    except KeyError:
        pass
    try:
        return BinaryOpcodes[operator].value
    except KeyError:
        pass
    return -1
