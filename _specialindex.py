"""
Special Index and Symbols

El índice sale de las enum en Opcodes.h y se mapean a símbolos en
PyrParseNode.cpp initSpecialSelectors().

Acá los nombres de los índices opcodes (en Opcodes.h) son los
nombres de los selectores (en PyrParseNode).

Used by BasicOpUGens to get an ID number for the operator.
"""

# TODO: special_index se usa en BasicOpUGen pero, además, creo, el atributo
# operator tiene que ser uno de estos símbolos (porque un y bin comparten
# números). Estos atributos special_index y name se usan en write_def de UGen.

# unary opcodes list
_unops_list = [
    ('neg', '__neg__'), # '-' unario # TODO: FALTAN COMLPETAR SINÓNIMOS Y COMPROBAR EL MISMO COMPORTAMIENTO.
    ('not',), # es not buleano en sclang
    ('isNil',), # nil/obj en sclang
    ('notNil',), # nil/obj en sclang
    ('bitNot', '__invert__'), # ~
    ('abs', '__abs__'), # abs()
    ('asFloat',),
    ('asInt',),
    ('ceil', '__ceil__'),
    ('floor', '__floor__'),
    ('frac',), # es math.modf(x)[0], no se comporta igual, devuelve una tupla
    ('sign',),
    ('squared',),
    ('cubed',),
    ('sqrt',), # math.sqrt(x), raíz e
    ('exp',), # e to the power of the receiver. math.exp(x)
    ('reciprocal',),
    ('midicps',),
    ('cpsmidi',),
    ('midiratio',),
    ('ratiomidi',),
    ('dbamp',),
    ('ampdb',),
    ('octcps',),
    ('cpsoct',),
    ('log',), # math.log
    ('log2',),
    ('log10',),
    ('sin',), # math
    ('cos',), # etc...
    ('tan',),
    ('asin',),
    ('acos',),
    ('atan',),
    ('sinh',),
    ('cosh',),
    ('tanh',),
    ('rand',),
    ('rand2',),
    ('linrand',),
    ('bilinrand',),
    #'exprand', # existe en AbstractFunction, está comentado acá.
    #'biexprand',
    ('sum3rand',),
    #'gammarand',
    #'gaussrand',
    #'poirand',
    ('distort',),
    ('softclip',),
    ('coin',),
    ('digitValue',), # no existe en sclang
    ('silence',), # no existe en sclang
    ('thru',), # no existe en sclang
    ('rectWindow',),
    ('hanWindow',),
    ('welWindow',),
    ('triWindow',),
    ('ramp',),
    ('scurve',),
    #opNumUnarySelectors
]

# binary opcodes list
_binops_list = [
    ('+', '__add__', '__radd__'),
    ('-', '__sub__', '__rsub__'),
    ('*', '__mul__', '__rmul__'),
    ('div', '__floordiv__', '__floordiv__'), # Python '//'
    ('/', '__truediv__', '__rtruediv__'),
    ('mod', '__mod__', '__rmod__'),
    ('==', '__eq__'),
    ('!=', '__ne__'),
    ('<', '__lt__'),
    ('>', '__gt__'),
    ('<=', '__le__'),
    ('>=', '__ge__'),
    #'===', # Python is
    #'!==', # Python is not
    ('min',),
    ('max',),
    ('bitAnd', '__and__', '__rand__'),
    ('bitOr', '__or__', '__ror__'),
    ('bitXor', '__xor__', '__rxor__'),
    ('lcm',),
    ('gcd',),
    ('round',), # Es trunc(x, quant) En Python __round__ es Unario con argumento
    ('roundUp',),
    ('trunc',), # BUG: Es trunc(x, quant) # En Python __truc__ es Unario, es la operación por defecto para int(x)
    ('atan2',),
    ('hypot',),
    ('hypotApx',), # BUG: está en AbstractFunction, no encontré una implementación con el mismo nombre.
    ('pow', '__pow__', '__rpow__'),
    ('leftShift', '__lshift__', '__rlshift__'),
    ('rightShift', '__rshift__', '__rrshift__'),
    ('unsignedRightShift',),
    ('fill',),
    ('ring1',), # a * (b + 1) == a * b + a
    ('ring2',), # a * b + a + b
    ('ring3',), # a*a*b
    ('ring4',), # a*a*b - a*b*b
    ('difsqr',), # a*a - b*b
    ('sumsqr',), # a*a + b*b
    ('sqrsum',), # (a + b)^2
    ('sqrdif',), # (a - b)^2
    ('absdif',), # |a - b|
    ('thresh',),
    ('amclip',),
    ('scaleneg',),
    ('clip2',),
    ('excess',),
    ('fold2',),
    ('wrap2',),
    ('firstArg',),
    ('rrand',),
    ('exprand',),
    #opNumBinarySelectors
]

def _build_op_dict(oplist):
    ret = dict()
    for i, item in enumerate(oplist):
        for name in item:
            ret[name] = [i, item[0]] # key: [special_index, sc_name]
    return ret

_unops = _build_op_dict(_unops_list)
_binops = _build_op_dict(_binops_list)

# Interface

def sc_spindex_opname(operator):
    '''Returns [special_index, sc_opname] or [-1, None].
    operator can be a str or scbuiltin function.'''
    if hasattr(operator, '__scbuiltin__'):
        operator = operator.__name__
    try: return _unops[operator]
    except KeyError: pass
    try: return _binops[operator]
    except KeyError: pass
    return [-1, None]

def special_index(operator):
    'Returns server operators special index or -1.'
    ret = sc_spindex_opname(operator)
    return ret[0]

def sc_opname(operator):
    'Returns server operator name or None.'
    ret = sc_spindex_opname(operator)
    return ret[1]
