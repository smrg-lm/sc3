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
        'neg',
        'not',
        'isNil',
        'notNil',
        'bitNot',
        'abs',
        'asFloat',
        'asInt',
        'ceil',
        'floor',
        'frac',
        'sign',
        'squared',
        'cubed',
        'sqrt',
        'exp',
        'reciprocal',
        'midicps',
        'cpsmidi',

        'midiratio',
        'ratiomidi',
        'dbamp',
        'ampdb',
        'octcps',
        'cpsoct',
        'log',
        'log2',
        'log10',
        'sin',
        'cos',
        'tan',
        'asin',
        'acos',
        'atan',
        'sinh',
        'cosh',
        'tanh',
        'rand',
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
        '+',
        '-',
        '*',
        'div', # Python //
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
        'round',
        'roundUp',
        'trunc',
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
