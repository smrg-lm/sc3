"""Engine.sc"""

import math

import supercollie.builtins as bi


class NodeIDAllocator():
    def __init__(self, user=0, init_temp=1000):
        if user > 31:
            raise Exception("NodeIDAllocator user id > 31")
        self.user = user
        self._init_temp = init_temp
        self.num_ids = 0x04000000; # // 2 ** 26 # // support 32 users
        self.reset()

    def id_offset(self):
        return self.num_ids * self.user

    def reset(self):
        self._mask = self.user << 26
        self._temp = self._init_temp
        self._perm = 2
        self._perm_freed = set()

    def alloc(self):
        x = self._temp
        self._temp = bi.wrap(x + 1, self._init_temp, 0x03FFFFFF)
        return x | mask

    def alloc_perm(self):
        if len(self._perm_freed) > 0:
            x = min(self._perm_freed)
            self._perm_free.remove(x)
        else:
            x = self._perm
            self._perm = min(x + 1, self._init_temp - 1)
        return x | mask

    def free_perm(self, id):
        # // should not add a temp node id to the freed-permanent collection
        id = id & 0x03FFFFFF
        if id < self._init_temp:
            self._perm_freed.add(id)


class PowerOfTwoBlock():
    def __init__(self, address, size):
        self.address = address
        self.size = size
        self.next = None


class PowerOfTwoAllocator():
    # // THIS IS THE RECOMMENDED ALLOCATOR FOR BUSES AND BUFFERS
    def __init__(self, size, pos=0):
        self.size = size
        self.array = [None] * size
        self.free_lists = [None] * 32
        self.pos = pos

    def alloc(self, n):
        # TODO: NEXTPOWEROFTWO está en: /include/common/clz.h
        # nextPowerOf en sclang: pow(2, math.ceil(math.log(x) / math.log(2))) -> int
        n = pow(2, math.ceil(math.log(n) / math.log(2))) # nextPowerOfTwo
        size_class = math.ceil(math.log2(n)) # log2Ceil primitive
        node = self.free_lists[size_class]
        if node is not None:
            self.free_lists[size_class] = node.next
            return node.address
        if self.pos + n <= self.size:
            self.array[self.pos] = PowerOfTwoBlock(self.pos, n)
            address = self.pos
            self.pos += n
            return address
        return None

    def free(self, address):
        # BUG: typo, declara y no usa la variable next (que no es la propiedad del bloque)
        node = self.array[address]
        if node is not None:
            size_class = math.ceil(math.log2(node.size)) # log2Ceil primitive
            node.next = self.free_lists[size_class]
            self.free_lists[size_class] = node
            self.array[adress] = None

    def blocks(self):
        return [x for x in self.array if x is not None]


class LRUNumberAllocator():
    # // implements a least recently used ID allocator.
    pass # TODO: no se usa por ahora


class StackNumberAllocator():
    def __init__(self, lo, hi):
        self._lo = lo
        self._hi = hi
        self.init()

    def init(self):
        self._free_list = []
        self._next = lo - 1

    def alloc(self):
        if len(self._free_list) > 0:
            return self._free_list.pop()
        if self._next < hi:
            next += 1
            return next
        return None

    def free(self, index):
        self._free_list.append(index)


class RingNumberAllocator():
    pass # TODO: no se usa por ahora


# // by hjh: for better handling of dynamic allocation

class ContiguousBlock():
    def __init__(self, start, size):
        self.start = start
        self.size = size
        self.used = False # // assume free; owner must say otherwise

    @property
    def address(self):
        return self.start

    def adjoins(self, block):
        return (self.start < block.start and self.start + self.size >= block.start)\
        or (self.start > block.start and block.start + block.size >= self.start)

    def join(self, block):
        if self.adjoins(block):
            start = min(self.start, block.start)
            size = max(self.start + self.size, block.start + block.size) - start
            return self.__class__(start, size)
        else:
            return None

    def split(self, span):
        if span < self.size:
            return [
                self.__class__(self.start, span),
                self.__class__(self.start + span, self.size - span)
            ]
        elif span == self.size:
            return [self, None]
        else:
            return None

    # storeArgs { ^[start, size, used] }
    # TODO (en general) printOn usa sotreOn que usa storeParamsOn que
    # usa storeArgs. Acá lo puse todo en __repr__ manualmente.
    # BUG: el problema es que se usa inconsistentemente en la librería
    # de clases. En Control se usa como __str__ y acá se usa como __repr__.
    # BUG: y también acá está mal usado porque la cadena de printOn
    # llama a obj.simplifyStoreArgs que no filtra los argumentos, o no
    # se usa, correctamente porque devuelve una llamada al constructor
    # con un argumento de más ('used').
    # def __repr__(self):
    #     string = self.__class__.__name__
    #     string += '({}, {})'.format(self.start, self.size)
    #     return string


# TODO: comentario duplicado en sclang...
class ContiguousBlockAllocator():
    # // pos is offset for reserved numbers,
    # // addrOffset is offset for clientID * size
    pass
