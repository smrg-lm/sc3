"""
Utility functions from sclang style.
"""

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
    if isinstance(obj, list) and len(obj) is 1:
        return obj[0]
    else:
        return obj


# to avoid flat -> reshapeLike in SynthDef:_build_controls
def perform_in_shape(inlist, obj, selector):
    '''Takes an inlist, maybe containing sub lists, and performs
    a selector of obj with each item in the list as argument
    returning a new list of values with the shape of inlist'''
    outlist = []
    for item in inlist:
        if isinstance(item, list):
            outlist.append(perform_in_shape(item, obj, selector))
        else:
            if not isinstance(item, tuple): item = (item,)
            outlist.append(getattr(obj, selector)(*item))
    return outlist

def wrap_extend(inlist, n):
    '''Create a new list by extending inlist with its
    own elements cyclically.'''
    return [inlist[i % len(inlist)] for i in range(n)]

#def reshape_like(this, that); # or that this like sclang?

# flop [(a[i], b[i]) for i in range(len(a))] pero len(a) >= len(b)
# select [x for x in self.control_names if x.rate is 'noncontrol']
# reject [x for x in self.control_names if x.rate is not 'noncontrol']
# any with predicate (a generator) como en sclang any(x > 10 for x in l)

# clump [l[i:i + n] for i in range(0, len(l), n)] https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
# dup [UGen] * n
# collect if else ['todo' if isinstance(x, A) else 'nada' for x in arr]
#[0] * (len(names) - len(rates)) # VER: sclang extend, pero no trunca
# [l[i%len(l)] for i in range(8)] # wrapExtend
# VER si la cantidad y necesidad en distintos lugares crece, si no sacar.
