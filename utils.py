"""
Utility classes and functions from sclang style.
"""

# VER Itertools Recipes
# ver https://docs.python.org/3/library/itertools.html#itertools-recipes
import itertools as _itertools


# decorador
class initclass():
    def __new__(_, cls):
        print('+ initclass for {} in {}'.format(cls.__name__, cls.__module__))
        cls.__init_class__(cls) # TODO: solo para métodos comunes, ver test_init_class.py
        return cls


class UniqueID(): # TODO: en sclang está en Common/Collections/ObjectTable.sc
    _id = 1000
    @classmethod
    def next(cls):
        cls._id += 1
        return cls._id


# Lists

# NOTE: asArray tiene implementación especial varias clases, que no están
# directamente relacionadas con las ugens, en particular, Env implemenenta
# asArray para as_control_input (ver ugen.as_control_input y
# node.as_osc_arg_list). La idea es no implemetar esa funcionalidad tan
# específica y dispersa en la librería de clases sino pasarlas a las
# funciones que lo requieran para la construcción de synthdefs u omitirlas.
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


# nota: también hay flatten2 y flatBelow
def flatten(inlist, n_levels=1):
    def _(inlist, outlist, n):
        for item in inlist:
            if n < n_levels:
                if isinstance(item, list):
                    _(item[:], outlist, n + 1) # TODO: no estoy seguro si es copia, la dejo por si las dudas
                else:
                    outlist.append(item)
            else:
                outlist.append(item)
    outlist = []
    _(inlist, outlist, 0)
    return outlist


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

def flop(lst):
    lst = [[None] if x is None else as_list(x) for x in lst] # NOTE: as_list convierte None en []
    n = len(lst)
    if n == 0:
        return [[]] # NOTE: es una columna vacía, así es en sclang.
    lenght = max(len(l) for l in lst)
    ret = [[None for _ in range(0, n)] for _ in range(0, lenght)]
    for i in range(0, lenght):
        for j in range(0, n):
            try:
                ret[i][j] = lst[j][i % len(lst[j])] # NOTE: *** en sclang i % 0 es cero *** es el caso de listas vacías acá.
            except ZeroDivisionError:
                ret[i][j] = [] # NOTE: *** y a = []; a[0] es nil, pero este método está implementado a bajo nivel y no lo miré, 0 o nil es [] acá.
    return ret

# # otras implementaciones de flop, comparar
# #[[None] * lenght] * n # al multiplicar copia la misma lista n veces
# def flop(lst):
#     # agregar lst = [as_list(x) for x in lst]
#     n = len(lst)
#     lenght = max(len(l) for l in lst)
#     aux = []
#     ret = []
#     for i in range(0, lenght):
#         for j in range(0, n):
#             aux.append(lst[j][i % len(lst[j])])
#         ret.append(aux)
#         aux = []
#     return ret
# # lst = [[1, 2], [10, 20, 30], [100, 200, 300, 400]]
# # [[lst[j][i % len(lst[j])] for j in range(0, len(lst))] for i in range(max(len(l) for l in lst))]

def flop_together(*lsts):
    max_size = 0
    for sub_list in lsts:
        for each in sub_list:
            if isinstance(each, list):
                max_size = max(max_size, len(each))
    stand_in = [0] * max_size
    for sub_list in lsts:
        sub_list.append(stand_in)
    ret = []
    for i, sub_list in enumerate(lsts):
        ret.append([])
        for each in flop(sub_list):
            each.pop()
            ret[i].append(each)
    return ret
