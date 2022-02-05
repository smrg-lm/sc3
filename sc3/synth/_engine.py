"""Engine.sc"""

import math
import logging

from ..base import builtins as bi


_logger = logging.getLogger(__name__)


class NodeIDAllocator():
    def __init__(self, user=0, init_temp=1000):
        if user > 31:
            raise Exception("NodeIDAllocator user id > 31")
        self.user = user
        self._init_temp = init_temp
        self.num_ids = (2 ** 32 // 2 - 1) // 64  # +int32, 64 logins safe range.
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
        return x | self._mask

    def alloc_perm(self):
        if len(self._perm_freed) > 0:
            x = min(self._perm_freed)
            self._perm_free.remove(x)
        else:
            x = self._perm
            self._perm = min(x + 1, self._init_temp - 1)
        return x | self.mask

    def free_perm(self, id):
        # // should not add a temp node id to the freed-permanent collection
        id = id & 0x03FFFFFF
        if id < self._init_temp:
            self._perm_freed.add(id)


class PowerOfTwoBlock():
    def __init__(self, addr, size):
        self.addr = addr
        self.size = size
        self.next = None


class PowerOfTwoAllocator():
    # // THIS IS THE RECOMMENDED ALLOCATOR FOR BUSES AND BUFFERS
    def __init__(self, size, pos=0):
        self._size = size
        self._array = [None] * size
        self._free_lists = [None] * 32
        self._pos = pos

    def alloc(self, n):
        # TODO: NEXTPOWEROFTWO está en: /include/common/clz.h
        # nextPowerOf en sclang: pow(2, math.ceil(math.log(x) / math.log(2))) -> int
        n = pow(2, math.ceil(math.log(n) / math.log(2))) # nextPowerOfTwo
        size_class = math.ceil(math.log2(n)) # log2Ceil primitive
        node = self._free_lists[size_class]
        if node is not None:
            self._free_lists[size_class] = node.next
            return node.addr
        if self._pos + n <= self._size:
            self._array[self._pos] = PowerOfTwoBlock(self._pos, n)
            addr = self._pos
            self._pos += n
            return addr
        return None

    def free(self, addr):
        node = self._array[addr]
        if node is not None:
            size_class = math.ceil(math.log2(node.size)) # log2Ceil primitive
            node.next = self._free_lists[size_class]
            self._free_lists[size_class] = node
            self._array[addr] = None

    def blocks(self):
        return [x for x in self._array if x is not None]


class LRUNumberAllocator():
    # // implements a least recently used ID allocator.
    def __init__(self, lo, hi):
        self._lo = lo
        self._hi = hi
        self._init()

    def _init(self):
        self._size = self._hi - self._lo + 1
        self._array = [None] * self._size
        for i, j in enumerate(range(self._lo, self._hi)):
            self._array[i] = j
        self._head = self._size - 1
        self._tail = 0

    def alloc(self):
        if self._head == self._tail:
            return None # // empty
        id = self._array[self._tail]
        self._tail = (self._tail + 1) % self._size
        return id

    def free(self, id):
        next_index = (self._head + 1) % self._size
        if next_index == self._tail:
            return None # // full
        self._array[self._head] = id
        self._head = next_index


class StackNumberAllocator():
    def __init__(self, lo, hi):
        self._lo = lo
        self._hi = hi
        self._init()

    def _init(self):
        self._free_list = []
        self._next = self._lo - 1

    def alloc(self):
        if len(self._free_list) > 0:
            return self._free_list.pop()
        if self._next < self._hi:
            self._next += 1
            return self._next
        return None

    def free(self, index):
        self._free_list.append(index)


class RingNumberAllocator():
    def __init__(self, lo, hi):
        self._lo = lo
        self._hi = hi
        self._init()

    def _init(self):
        self._next = self._hi

    def alloc(self):
        self._next = bi.wrap(self._next + 1, self._lo, self._hi)
        return self._next


# // by hjh: for better handling of dynamic allocation

class ContiguousBlock():
    def __init__(self, start, size):
        self.start = start
        self.size = size
        self.used = False  # // Assume free; owner must say otherwise.

    @property
    def address(self):
        return self.start

    def adjoins(self, block):
        st = self.start
        sz = self.size
        st2 = block.start
        sz2 = block.size
        return (st < st2 and st + sz >= st2) or (st > st2 and st2 + sz2 >= st)

    def join(self, block):
        if self.adjoins(block):
            start = min(self.start, block.start)
            size = max(self.start + self.size, block.start + block.size) - start
            return type(self)(start, size)
        else:
            return None

    def split(self, span):
        if span < self.size:
            return [
                type(self)(self.start, span),
                type(self)(self.start + span, self.size - span)]
        elif span == self.size:
            return [self, None]
        else:
            return [None, None]

    def __repr__(self):
        return f'{type(self).__name__}({self.start}, {self.size})'


class ContiguousBlockAllocator():
    def __init__(self, size, pos=0, addr_offset=0):
        # // pos is offset for reserved numbers,
        # // addr_offset is offset for client_id * size
        self.size = size
        shifted_pos = pos + addr_offset
        self._array = [None] * size
        self._array[pos] = ContiguousBlock(shifted_pos, size - pos)
        self._freed = dict()
        self.pos = shifted_pos
        self.top = shifted_pos
        self.addr_offset = addr_offset

    def alloc(self, n=1):
        block = self._find_available(n)
        if block is not None:
            return self._reserve(block.start, n, block).start
        else:
            return None

    def reserve(self, addr, size=1, warn=True):
        if self._array[addr] is None:
            block = self._find_next(addr)
        else:
            block = self._array[addr]
        if block is not None and block.used and addr + size > block.start:
            if warn:
                _logger.warning(
                    f'The block at ({addr}, {size}) is '
                    'already in use and cannot be reserved.')
        elif block.start == addr:
            return self._reserve(addr, size, block)

        block = self._find_previous(addr)
        if block is not None and block.used and block.start + block.size > addr:
            if warn:
                _logger.warning(
                    f'The block at ({addr}, {size}) is '
                    'already in use and cannot be reserved')
        else:
            return self._reserve(addr, size, None, block)

        return None

    def free(self, addr):
        # // this 'if' prevents an error if a Buffer object is freed twice
        if addr is None:
            return
        block = self._array[addr - self.addr_offset]
        if block is not None and block.used:
            block.used = False
            self._add_to_freed(block)
            prev = self._find_previous(addr)
            if prev is not None and not prev.used:
                tmp = prev.join(block)
                if tmp is not None:
                    # // if block is the last one, reduce the top
                    if block.start == self.top: self.top = tmp.start
                    self._array[tmp.start - self.addr_offset] = tmp
                    self._array[block.start - self.addr_offset] = None
                    self._remove_from_freed(prev)
                    self._remove_from_freed(block)
                    if self.top > tmp.start: self._add_to_freed(tmp)
                    block = tmp
            next = self._find_next(block.start)
            if next is not None and not next.used:
                tmp = next.join(block)
                if tmp is not None:
                    # // if next is the last one, reduce the top
                    if next.start == self.top: self.top = tmp.start
                    self._array[tmp.start - self.addr_offset] = tmp
                    self._array[next.start - self.addr_offset] = None
                    self._remove_from_freed(next)
                    self._remove_from_freed(block)
                    if self.top > tmp.start: self._add_to_freed(tmp)

    def blocks(self):
        return [x for x in self._array if x is not None and x.used]

    def _find_available(self, n):
        if n in self._freed and len(self._freed[n]) > 0:
            return bi.choice(list(self._freed[n]))
        for size, set_ in self._freed.items():
            if size >= n and len(set_) > 0:
                return bi.choice(list(set_))
        if self.top + n - self.addr_offset > self.size\
        or self._array[self.top - self.addr_offset].used:
            return None
        return self._array[self.top - self.addr_offset]

    def _add_to_freed(self, block):
        if self._freed.get(block.size) is None:
            self._freed[block.size] = set()
        self._freed[block.size].add(block)

    def _remove_from_freed(self, block):
        if self._freed.get(block.size) is not None:
            if block in self._freed[block.size]:
                self._freed[block.size].remove(block)
            if not self._freed[block.size]:
                del self._freed[block.size]

    def _find_previous(self, addr):
        for i in reversed(range(self.pos, addr)):
            if self._array[i - self.addr_offset] is not None:
                return self._array[i - self.addr_offset]
        return None

    def _find_next(self, addr):
        # From supercollider/pull/5307
        tmp = self._array[addr - self.addr_offset]
        if tmp is not None:
            i = tmp.start + tmp.size
        else:
            i = addr + 1
            # // self.top points to the last non-nil entry, so, stop there.
            while i <= self.top and self._array[i - self.addr_offset] is None:
                i += 1
        if i < self.size:
            return self._array[i - self.addr_offset]
        else:
            return None

    def _reserve(self, addr, size, avail_block=None, prev_block=None):
        if avail_block is None and prev_block is None:
            prev_block = self._find_previous(addr)
        if avail_block is None:
            avail_block = prev_block
        if avail_block.start < addr:
            avail_block = self._split(
                avail_block, addr - avail_block.start, False)[1]
        return self._split(avail_block, size, True)[0]

    def _split(self, avail_block, n, used=True):
        new, leftover = avail_block.split(n)  # Should not return [None, None] if n <= avail_block.size.
        new.used = used
        self._remove_from_freed(avail_block)
        if not used:
            self._add_to_freed(new)
        self._array[new.start - self.addr_offset] = new
        if leftover is not None:
            self._array[leftover.start - self.addr_offset] = leftover
            self.top = max(self.top, leftover.start)
            if self.top > leftover.start:
                self._add_to_freed(leftover)
        return [new, leftover]

    # debug { |text|
    #     Post << text << ":\n\nArray:\n";
    #     array.do({ |item, i|
    #         item.notNil.if({ Post << i << ": " << item << "\n"; });
    #     });
    #     Post << "\nFree sets:\n";
    #     freed.keysValuesDo({ |size, set|
    #         Post << size << ": " <<< set << "\n";
    #     });
    # }
