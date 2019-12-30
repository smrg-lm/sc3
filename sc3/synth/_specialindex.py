"""
Special Index and Symbols

Indexes from enum in Opcodes.h, maps to Symbol in PyrParseNode.cpp
initSpecialSelectors(). Names  of index opcodes (Opcodes.h) are selectors names
(PyrParseNode). Used by BasicOpUGens to get an ID number for the operator.
"""

# TODO: special_index se usa en BasicOpUGen pero, además, creo, el atributo
# operator tiene que ser uno de estos símbolos (porque un y bin comparten
# números). Estos atributos special_index y name se usan en write_def de UGen.

# TODO: Verify precise behavior and synonyms

# unary opcodes list
_unops_list = [
    ('neg', '__neg__'),  # '-' unary
    ('not',),  # boolean not buleano in sclang
    ('isNil',),  # nil/obj in sclang
    ('notNil',),  # nil/obj in sclang
    ('bitNot', '__invert__', 'invert'),  # ~
    ('abs', '__abs__'),  # abs()
    ('asFloat',),
    ('asInt',),
    ('ceil', '__ceil__'),  # underscores?
    ('floor', '__floor__'),  # underscores?
    ('frac',),  # is math.modf(x)[0], not same behavior, returns tuple
    ('sign',),
    ('squared',),
    ('cubed',),
    ('sqrt',),  # math.sqrt(x), radix e
    ('exp',),  # e to the power of the receiver, math.exp(x)
    ('reciprocal',),
    ('midicps',),
    ('cpsmidi',),
    ('midiratio',),
    ('ratiomidi',),
    ('dbamp',),
    ('ampdb',),
    ('octcps',),
    ('cpsoct',),
    ('log',),  # math.log
    ('log2',),
    ('log10',),
    ('sin',),  # math.sin
    ('cos',),  # etc...
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
    ('rectWindow', 'rectwindow'),
    ('hanWindow', 'hanwindow'),
    ('welWindow', 'welwindow'),
    ('triWindow', 'triwindow'),
    ('ramp',),
    ('scurve',),
    #opNumUnarySelectors
]

# binary opcodes list
_binops_list = [
    ('+', '__add__', '__radd__', 'add'),
    ('-', '__sub__', '__rsub__', 'sub'),
    ('*', '__mul__', '__rmul__', 'mul'),
    ('div', '__floordiv__', '__floordiv__', 'floordiv'),  # Python's '//'
    ('/', '__truediv__', '__rtruediv__', 'truediv'),
    ('mod', '__mod__', '__rmod__'),
    ('==', '__eq__', 'eq'),
    ('!=', '__ne__', 'ne'),
    ('<', '__lt__', 'lt'),
    ('>', '__gt__', 'gt'),
    ('<=', '__le__', 'le'),
    ('>=', '__ge__', 'ge'),
    #'===', # Python is
    #'!==', # Python is not
    ('min',),
    ('max',),
    ('bitAnd', 'bitand', '__and__', '__rand__', 'and'),
    ('bitOr', 'bitor', '__or__', '__ror__', 'or'),
    ('bitXor', 'bitxor', '__xor__', '__rxor__', 'xor'),
    ('lcm',),
    ('gcd',),
    ('round',), # Es trunc(x, quant) En Python __round__ es Unario con argumento
    ('roundUp', 'roundup'),
    ('trunc',), # BUG: Es trunc(x, quant) # En Python __truc__ es Unario, es la operación por defecto para int(x)
    ('atan2',),
    ('hypot',),
    ('hypotApx', 'hypotx'),
    ('pow', '__pow__', '__rpow__'),  # **
    ('leftShift', 'leftshift', '__lshift__', '__rlshift__', 'lshift'),
    ('rightShift', 'rightshift', '__rshift__', '__rrshift__', 'rshift'),
    ('unsignedRightShift', 'urightshift'),
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
    ('firstArg', 'first_arg'),
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
    '''
    Returns (special_index, sc_opname) or (-1, None). operator is a str.
    '''
    try: return _unops[operator]
    except KeyError: pass
    try: return _binops[operator]
    except KeyError: pass
    return (-1, None)


def special_index(operator):
    '''Returns server operators special index or -1.'''
    ret = sc_spindex_opname(operator)
    return ret[0]


def sc_opname(operator):
    '''Returns server operator name or None.'''
    ret = sc_spindex_opname(operator)
    return ret[1]


def sc_opname_from_index(index, arity='unary'):
    if arity == 'unary':
        return _unops_list[index][0]
    elif arity == 'binary':
        return _binops_list[index][0]
    else:
        raise ValueError(f'arity {arity} not supported by special index')
