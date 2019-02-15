"""
Utility classes and functions from sclang style.
"""

# VER Itertools Recipes
# ver https://docs.python.org/3/library/itertools.html#itertools-recipes
import itertools as _itertools


# decorador
class initclass():
    def __new__(_, cls):
        cls.__init_class__(cls) # TODO: solo para métodos comunes, ver test_init_class.py
        return cls


class UniqueID(): # TODO: en sclang está en Common/Collections/ObjectTable.sc
    _id = 1000
    @classmethod
    def next(cls):
        cls._id += 1
        return cls._id


# lists

def as_list(obj):
    '''Bubble the object in a list unless it is a list.
    If obj is None returns an empty list.'''
    if obj is None:
        return []
    else:
        return obj if isinstance(obj, list) else [obj]

def unbubble(obj): # only one level
    '''If obj is a list of one item or any other object unbubble(obj)
    returns the item, otherwise returns the list or object unchanged.'''
    if isinstance(obj, list) and len(obj) == 1:
        return obj[0]
    else:
        return obj

def flat(inlist):
    def _(inlist, outlist):
        for item in inlist:
            if isinstance(item, list):
                _(item[:], outlist) # TODO: no estoy seguro si es copia, la dejo por si las dudas
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
                    _(item[:], outlist, n+1) # TODO: no estoy seguro si es copia, la dejo por si las dudas
                else:
                    outlist.append(item)
            else:
                outlist.append(item)
    outlist = []
    _(inlist, outlist, 0)
    return outlist

# nota: también hay flatten2 y flatBelow

def reshape_like(one, another):
    index = 0
    one_flat = flat(one)
    def func(*discard):
        nonlocal index
        item = one_flat[index % len(one_flat)] # indexing='wrapAt'
        index += 1
        return item
    return deep_collect(another, 0x7FFFFFFF, func)

def deep_collect(inlist, depth, func, index=0, rank=0):
    if depth is None:
        rank += 1
        if isinstance(inlist, list):
            return [deep_collect(item, depth, func, i, rank) for i, item in enumerate(inlist)]
        else:
            return func(inlist, index, rank)
    if depth <= 0:
        if func:
            return func(inlist, index, rank) # inlist es un objeto no lista en este caso, creo.
        else:
            return None
    depth -= 1
    rank += 1
    if isinstance(inlist, list):
        return [deep_collect(item, depth, func, i, rank) for i, item in enumerate(inlist)]
    else:
        return func(inlist, index, rank)

def wrap_extend(inlist, n):
    '''Create a new list by extending inlist with its
    own elements cyclically.'''
    return [inlist[i % len(inlist)] for i in range(n)]

#def reshape_like(this, that); # or that this like sclang?

# flop [(a[i], b[i]) for i in range(len(a))] pero len(a) >= len(b)
# select [x for x in self.control_names if x.rate == 'noncontrol']
# reject [x for x in self.control_names if x.rate != 'noncontrol']
# any with predicate (a generator) como en sclang any(x > 10 for x in l)
# también está la función all en Python.

# detect sería:
# control = None
# for item in self.controls:
#     if item.index == (b.output_index + b.source_ugen.special_index):
#         control = item
#         break
# pero no es nada compacto, tal vez haya un truco

# clump [l[i:i + n] for i in range(0, len(l), n)] https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
# ver también grouper en Itertools Recipes
# def gen_clumps(l, n=1):
#    return (l[i:i + n] for i in range(0, len(l), n))

# para pairsDo:
def gen_cclumps(l, n=1):
    '''return n items as pairsDo does (with n=2) for iteration, cclump stands
    for complete clump, it discards possible non full clump at the end'''
    return (l[i:i + n] for i in range(0, len(l), n) if len(l[i:i + n]) == n)

# para doAdjacentPairs, de Python Itertools Recipes: https://docs.python.org/3/library/itertools.html#itertools-recipes
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = _itertools.tee(iterable)
    next(b, None)
    return zip(a, b)

# dup [UGen] * n
# collect if else ['todo' if isinstance(x, A) else 'nada' for x in arr]
#[0] * (len(names) - len(rates)) # VER: sclang extend, pero no trunca
# [l[i%len(l)] for i in range(8)] # wrapExtend
# VER si la cantidad y necesidad en distintos lugares crece, si no sacar.

# producto cartesiano, es combinatoria
# https://stackoverflow.com/questions/10973766/understanding-the-map-function
#[(a, b) for a in iterable_a for b in iterable_b]

# map sirve como collect
#map(función, iterable)

# pero también se puede usar list comprehensions como sugiere el link
#[f(x) for x in iterable]
