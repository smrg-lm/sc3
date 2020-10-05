"""
Functions used to process lists as in sclang.
At the moment they are mostly for internal use.
"""

import itertools
import operator


def as_list(obj):
    '''
    Bubble non iterable objects, tuples and strings in a list. If obj is None
    returns an empty list. For the rest of iterators is the same as list(obj).
    '''
    if isinstance(obj, (tuple, str)):
        return [obj]
    elif hasattr(obj, '__iter__'):
        return list(obj)
    else:
        return [obj]


def unbubble(obj):
    '''If obj is a list of one item or any other object unbubble(obj)
    returns the item, otherwise returns the list or object unchanged.'''
    if isinstance(obj, list) and len(obj) == 1:  # only one level
        return obj[0]
    else:
        return obj

# TODO: replace all inlist by lst for convention.

def flat(inlist):
    def _(inlist, outlist):
        for item in inlist:
            if isinstance(item, list):
                _(item[:], outlist)  # TODO: Not sure if has to be a copy.
            else:
                outlist.append(item)
    outlist = []
    _(inlist, outlist)
    return outlist


def flatten(inlist, n_levels=1):
    def _(inlist, outlist, n):
        for item in inlist:
            if n < n_levels:
                if isinstance(item, list):
                    _(item[:], outlist, n + 1)  # TODO: Not sure if has to be a copy.
                else:
                    outlist.append(item)
            else:
                outlist.append(item)
    outlist = []
    _(inlist, outlist, 0)
    return outlist


def shape(lst):
    if isinstance(lst, (list, tuple)):
        size = len(lst)
        if size > 0:
            # // This assumes every element has the same shape.
            sub_shape = shape(lst[0])
            if len(sub_shape) > 0:
                ret = [size]
                ret.extend(sub_shape)
                return tuple(ret)
            else:
                return (size, )
        else:
            return (0,)
    else:
        return tuple()


def reshape_like(one, another):
    index = 0
    one_flat = flat(one)

    def func(*discard):
        nonlocal index
        item = one_flat[index % len(one_flat)]
        index += 1
        return item
    return deep_collect(another, 0x7FFFFFFF, func)


def deep_collect(inlist, depth, func, index=0, rank=0):
    if depth is None:
        rank += 1
        if isinstance(inlist, list):
            return [
                deep_collect(item, depth, func, i, rank)
                for i, item in enumerate(inlist)]
        else:
            return func(inlist, index, rank)
    if depth <= 0:
        if func:
            return func(inlist, index, rank)
        else:
            return None
    depth -= 1
    rank += 1
    if isinstance(inlist, list):
        return [
            deep_collect(item, depth, func, i, rank)
            for i, item in enumerate(inlist)]
    else:
        return func(inlist, index, rank)


def extend(lst, n, item):
    '''
    Create a new list by extending lst with item.
    '''
    l = len(lst)
    if l == 0 or n <= 0: return []
    return (lst + [item] * (n - l))[:n]


def wrap_extend(lst, n):
    '''
    Create a new list by extending lst with its own elements cyclically.
    '''
    l = len(lst)
    if l == 0 or n <= 0: return []
    return lst * (n // l) + lst[:n % l]


def list_unop(op, a, t=None):
    t = t or list
    t_seq = (list, tuple)  # TODO: check.
    if isinstance(a, t_seq):
        if any(isinstance(i, t_seq) for i in a):
            return t(list_unop(op, i, type(i)) for i in a)
        return t(op(i) for i in a)
    else:
        return op(a)


def list_binop(op, a, b, t=None):
    '''
    Operate on sequences element by element and return a sequence of type t
    (default to list) if any argument a or b is sequence. Arguments a and b may
    be types or a sequence of types compatible with operator op. Nested
    sequences are processed recursively. Recursion uses tuple type cast if any
    is tuple or type(a) if is a is sequence else type(b) if b is sequence.
    Tuples are termporary converted to lists to process. All this is needed
    because multichannel expansion behaviour (e.g. in Env).
    '''
    # NOTE: The other option is to leave tuples as tuples, could be
    # better, the problem is outside UGen operations as in Env.
    t = t or list
    t_seq = (list, tuple)  # TODO: check.
    if isinstance(a, t_seq) and isinstance(b, t_seq):
        if len(a) >= len(b):
            b = wrap_extend(list(b), len(a))
        else:
            a = wrap_extend(list(a), len(b))
        if any(isinstance(i, t_seq) for i in a)\
        or any(isinstance(i, t_seq) for i in b):
            ret = []
            a2 = b2 = t2 = None
            for i in range(len(a)):
                if isinstance(a[i], tuple):
                    t2 = tuple
                    a2 = list(a[i])
                if isinstance(b[i], tuple):
                    t2 = tuple
                    b2 = list(b[i])
                if t2 is None:
                    if isinstance(a[i], t_seq):
                        t2 = list
                    elif isinstance(b[i], t_seq):
                        t2 = list
                a2 = a2 or a[i]
                b2 = b2 or b[i]
                t2 = t2 or type(...)  # if neither is t_seq type doesn't matter but can't be None.
                ret.append(list_binop(op, a2, b2, t2))
                a2 = b2 = t2 = None
            return t(ret)
        else:
            return t(op(i[0], i[1]) for i in zip(a, b))
    elif isinstance(a, t_seq):
        return t(list_binop(op, item_a, b, type(item_a)) for item_a in a)
    elif isinstance(b, t_seq):
        return t(list_binop(op, a, item_b, type(item_b)) for item_b in b)
    else:
        return op(a, b)


def list_narop(op, a, *args, t=None):
    t = t or list
    t_seq = (list, tuple)  # TODO: check.
    if isinstance(a, t_seq):
        if any(isinstance(i, t_seq) for i in a):
            return t(list_narop(op, i, *args, t=type(i)) for i in a)
        return t(op(i, *args) for i in a)
    else:
        return op(a, *args)


def list_sum(lst, t=None):
    res = 0
    for item in lst:
        res = list_binop(operator.add, res, item, t)
    return res

# NOTE: maxItem used in Env.duration gives the clue that only one level of
# nesting is supported by multichannels graphs. Same happens when building
# controls in SynthDef.
# [1, 2, 3, 4].maxItem // ok
# 3 > [3, 4] // ok
# [3, 4] > 3 // ok
# [1, 2, [3, 4]].maxItem // not ok
# [[1, 2], [3, 4]].maxItem // not ok

def list_min(lst, t=None):
    t_seq = (list, tuple)
    min_item = lst[0]
    if isinstance(min_item, t_seq):
        min_item = list_min(min_item, t)
    for item in lst[1:]:
        if isinstance(item, t_seq):
            item = list_min(item, t)
        if list_binop(operator.lt, item, min_item, t):
            min_item = item
    return min_item


def list_max(lst, t=None):
    t_seq = (list, tuple)
    max_item = lst[0]
    if isinstance(max_item, t_seq):
        max_item = list_max(max_item, t)
    for item in lst[1:]:
        if isinstance(item, t_seq):
            item = list_max(item, t)
        if list_binop(operator.gt, item, max_item, t):
            max_item = item
    return max_item


#def reshape_like(this, that); # or that this like sclang?

# flop [(a[i], b[i]) for i in range(len(a))] but len(a) >= len(b)
# filter() y itertools.filterfalse() are select/reject.
# select [x for x in self.control_names if x.rate == 'noncontrol']
# reject [x for x in self.control_names if x.rate != 'noncontrol']
# any with predicate (a generator) como en sclang any(x > 10 for x in l)
# Python's all()

# detect could be:
# for item in sequence:
#     if item == something:
#         return item

# clump [l[i:i + n] for i in range(0, len(l), n)] https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
# ver también grouper en Itertools Recipes
# def gen_clumps(l, n=1):
#    return (l[i:i + n] for i in range(0, len(l), n))


def clump(lst, n):
    return [lst[i:i + n] for i in range(0, len(lst), n)]


# para pairsDo:
def gen_cclumps(l, n=1):
    '''return n items as pairsDo does (with n=2) for iteration, cclump stands
    for complete clump, it discards possible non full clump at the end'''
    return (l[i:i + n] for i in range(0, len(l) - (n - 1), n))


# doAdjacentPairs, Itertools Recipes: https://docs.python.org/3/library/itertools.html#itertools-recipes
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


# dup [UGen] * n
# collect if else ['todo' if isinstance(x, A) else 'nada' for x in arr]
# [0] * (len(names) - len(rates)) # VER: sclang extend, pero no trunca
# [l[i%len(l)] for i in range(8)] # wrapExtend

# Cartesian product, is combinatorial (itertools.product).
# https://stackoverflow.com/questions/10973766/understanding-the-map-function
# [(a, b) for a in iterable_a for b in iterable_b]

# map as collect
# map(función, iterable)
# [f(x) for x in iterable]


def lace(lst, size=None):
    if size is None:
        return [x for sub in zip(*lst) for x in sub]
    else:
        gen = itertools.cycle(x for sub in zip(*lst) for x in sub)
        return [next(gen) for _ in range(0, size)]


def flop(lst):
    lst = [[None] if x is None else as_list(x) for x in lst]  # NOTE: as_list converts None in []
    n = len(lst)
    if n == 0:
        return [[]]  # NOTE: empty column as in sclang.
    length = max(len(l) for l in lst)
    ret = [[None for _ in range(n)] for _ in range(length)]
    for i in range(length):
        for j in range(n):
            try:
                ret[i][j] = lst[j][i % len(lst[j])]  # NOTE: i % 0 == 0 in sclang, and is also empty list.
            except ZeroDivisionError:
                ret[i][j] = []  # NOTE: a = []; a[0] is nil, 0 or nil is [].
    return ret


# # other flop.
# # [[None] * length] * n
# def flop(lst):
#     # agregar lst = [as_list(x) for x in lst]
#     n = len(lst)
#     length = max(len(l) for l in lst)
#     aux = []
#     ret = []
#     for i in range(length):
#         for j in range(n):
#             aux.append(lst[j][i % len(lst[j])])
#         ret.append(aux)
#         aux = []
#     return ret
# # lst = [[1, 2], [10, 20, 30], [100, 200, 300, 400]]
# # [[lst[j][i % len(lst[j])] for j in range(len(lst))] for i in range(max(len(l) for l in lst))]


def flop_together(*lsts):  # BUG: in sclang, modifies the original list with garbage.
    max_size = 0
    for sub_list in lsts:
        for each in sub_list:
            if isinstance(each, list):
                max_size = max(max_size, len(each))
    stand_in = [None] * max_size
    ret = []
    for i, sub_list in enumerate(lsts):
        sub_list = sub_list[:]
        sub_list.append(stand_in)
        ret.append([])
        for each in flop(sub_list):
            each.pop()  # // remove stand-in
            ret[i].append(each)
    return ret


def max_depth(lst):
    def find_max(lst, max_rank=1):
        ret = max_rank
        for item in lst:
            if isinstance(item, list):
                ret = max(ret, find_max(item, max_rank + 1))
        return ret
    return find_max(lst)


def max_size_at_depth(lst, rank):
    if rank <= 0:  # BUG: in sclang recursive condition is wrong.
        return len(lst)
    max_size = 0
    for item in lst:
        if isinstance(item, list):
            sz = max_size_at_depth(item, rank - 1)
        else:
            sz = 1
        if sz > max_size:
            max_size = sz
    return max_size


def wrap_at_depth(lst, rank, index):
    if rank <= 0:  # BUG: in sclang recursive condition is wrong.
        return lst[index % len(lst)]
    ret = []
    for item in lst:  # BUG: in sclang i is not used
        if isinstance(item, list):
            ret.append(wrap_at_depth(item, rank - 1, index))
        else:
            ret.append(item)
    return ret


def flop_deep(lst, rank):
    if rank is None:
        rank = max_depth(lst) - 1
    if rank <= 1:
        return flop(lst)
    size = len(lst)
    max_size = max_size_at_depth(lst, rank)
    ret = []
    for i in range(max_size):
        ret.append(wrap_at_depth(lst, rank, i))
    return ret


def multichannel_expand_tuple(tpl, rank):
    # // Allow to multichannel expand ugen specs, like those of Klank,
    # // in the case of which two is the rank, but could be otherwise.
    lst = list(tpl)
    if max_size_at_depth(lst, rank) <= 1:
        return tpl
    lst = flop_deep(lst, rank)
    return unbubble([tuple(item) for item in lst])  # why unbubble?
