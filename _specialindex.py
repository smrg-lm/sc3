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
    ('neg', '__neg__'),  # __neg__ TODO: FALTAN COMLPETAR SINÓNIMOS Y COMPROBAR EL MISMO COMPORTAMIENTO.
    ('not', '__not__'), # es not buleano, operator.not_(obj)/operator.__not__(obj)
    ('isNil',),
    ('notNil',),
    ('bitNot', '__invert__'),
    ('abs', '__abs__'),
    ('asFloat',),
    ('asInt',),
    ('ceil', '__ceil__'),
    ('floor', '__floor__'),
    ('frac',), # math.modf, no se comporta igual
    ('sign',), # no existe
    ('squared',), # no existe
    ('cubed',), # no existe
    ('sqrt',), # math.sqrt(x), VER: se comporta raro en sclang, no entiendo.
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
    ('rand',), # VER que hay en Python
    ('rand2',),
    ('linrand',),
    ('bilinrand',),
    #'exprand',
    #'biexprand',
    ('sum3rand',),
    #'gammarand',
    #'gaussrand',
    #'poirand',
    ('distort',),
    ('softclip',),
    ('coin',),
    ('digitValue',),
    ('silence',),
    ('thru',),
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
    ('+', '__add__', '__radd__', '__iadd__'), # TODO: COMPROBAR
    ('-',),
    ('*', '__mul__', '__rmul__', '__imul__'),
    ('div', '__floordiv__'), # Python '//
    ('/',),
    ('mod',),
    ('==',),
    ('!=',),
    ('<',),
    ('>',),
    ('<=',),
    ('>=',),
    #'===', # Python is
    #'!==', # Python is not
    ('min',),
    ('max',),
    ('bitAnd',),
    ('bitOr',),
    ('bitXor',),
    ('lcm',),
    ('gcd',),
    ('round',), # __round__ es Unario con argumento
    ('roundUp',),
    ('trunc',), # __truc__ es Unario, es la operación por defecto para int(x)
    ('atan2',),
    ('hypot',),
    ('hypotApx',),
    ('pow',),
    ('leftShift',),
    ('rightShift',),
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
    'Returns [special_index, sc_opname] or None'
    try: return _unops[operator]
    except KeyError: pass
    try: return _binops[operator]
    except KeyError: pass
    return None # ***************** TODO: OJO, esto era -1 pero no tiene seitndo retornar distintos tipos de valores, ver si afecta.

def special_index(operator):
    'Returns server operators special index or None'
    ret = sc_spindex_opname(operator)
    if ret: return ret[0]
    return ret

def sc_opname(operator):
    'Returns server operator name or None'
    ret = sc_spindex_opname(operator)
    if ret: return ret[1]
    return ret
