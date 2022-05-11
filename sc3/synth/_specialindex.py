"""
Special Index and Symbols

Indexes from enum in Opcodes.h, maps to Symbol in PyrParseNode.cpp
initSpecialSelectors(). Names  of index opcodes (Opcodes.h) are selectors names
(PyrParseNode). Used by BasicOpUGens to get an ID number for the operator.

The leftmost string in the table is the actual opcode name, the rest are
synonyms or replacements used in Python (dunder methods or operator module
function names).

"""


### Unary opcodes ###

_unops_list = [
    ('neg', '__neg__'),  # '-' unary
    ('not', 'not_'),  # boolean not
    ('isNil',),  # nil/obj in sclang, not accessible as opcode
    ('notNil',),  # nil/obj in sclang, not accessible as opcode
    ('bitNot', '__invert__', 'invert'),  # ~
    ('abs', '__abs__'),  # abs()
    ('asFloat', 'as_float'),
    ('asInteger', 'as_int'),
    ('ceil', '__ceil__'),
    ('floor', '__floor__'),
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
    #'exprand',
    #'biexprand',
    ('sum3rand',),
    #'gammarand',
    #'gaussrand',
    #'poirand',
    ('distort',),
    ('softclip',),
    ('coin',),
    ('digitValue',),  # Unused in sclang.
    ('silence',),  # Unused in sclang.
    ('thru',),  # Unused in sclang.
    ('rectWindow', 'rectwindow'),
    ('hanWindow', 'hanwindow'),
    ('welWindow', 'welwindow'),
    ('triWindow', 'triwindow'),
    ('ramp',),
    ('scurve',),
    #opNumUnarySelectors
]


### Binary opcodes ###

_binops_list = [
    ('+', '__add__', '__radd__', 'add'),
    ('-', '__sub__', '__rsub__', 'sub'),
    ('*', '__mul__', '__rmul__', 'mul'),
    ('div', '__floordiv__', '__rfloordiv__', 'floordiv'),  # //
    ('/', '__truediv__', '__rtruediv__', 'truediv'),
    ('mod', '__mod__', '__rmod__'),
    ('==', '__eq__', 'eq'),  # Unused in sclang, added.
    ('!=', '__ne__', 'ne'),  # Unused in sclang, added.
    ('<', '__lt__', 'lt'),
    ('>', '__gt__', 'gt'),
    ('<=', '__le__', 'le'),
    ('>=', '__ge__', 'ge'),
    #'===', # Python is
    #'!==', # Python is not
    ('min',),
    ('max',),
    ('bitAnd', 'bitand', '__and__', '__rand__', 'and_'),  # &
    ('bitOr', 'bitor', '__or__', '__ror__', 'or_'),  # |
    ('bitXor', 'bitxor', '__xor__', '__rxor__', 'xor'),  # ^
    ('lcm',),
    ('gcd',),
    ('round', '__round__'),  # Is round(x, quant), in Python __round__ is unary with arg.
    ('roundUp', 'roundup'),
    ('trunc', '__trunc__'),  # Is trunc(x, quant), in Python __truc__ is unary, default op for int(x).
    ('atan2',),
    ('hypot',),
    ('hypotApx', 'hypotx'),
    ('pow', '__pow__', '__rpow__'),  # **
    ('leftShift', '__lshift__', '__rlshift__', 'lshift'),  # <<
    ('rightShift', '__rshift__', '__rrshift__', 'rshift'),  # >>
    ('unsignedRightShift', 'urshift'),
    ('fill',),  # Unused in sclang.
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
