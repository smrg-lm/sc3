"""ListPatterns.sc"""

import collections

from ...base import stream as stm
from ...base import builtins as bi
from .. import pattern as ptt


class ListPattern(ptt.Pattern):
    def __init__(self, lst=None, repeats=1):
        lst = list(lst)  # raises TypeError
        if len(lst) > 0:
            self.lst = lst
            self.repeats = repeats
        else:
            raise ValueError(
                f"ListPattern '{type(self).__name__}' "
                "requires a non empty collection")
        self._is_event_pattern = any(
            isinstance(x, ptt.Pattern) and x.is_event_pattern for x in lst)

    @property
    def is_event_pattern(self):
        return self._is_event_pattern

    # copy
    # storeArgs


class Pseq(ListPattern):
    def __init__(self, lst, repeats=1, offset=0):
        super().__init__(lst, repeats)
        self.offset = int(offset)

    def __embed__(self, inval):
        # if (inval.eventAt('reverse') == true, { # Not good.
        lst = self.lst
        offset = self.offset
        for _ in bi.counter(self.repeats):
            for item in lst[offset:]:
                inval = yield from stm.embed(item, inval)
            for item in lst[:offset]:
                inval = yield from stm.embed(item, inval)
        return inval

    # storeArgs # TODO


class Pser(Pseq):
    def __embed__(self, inval):
        lst = self.lst
        offset = self.offset
        size = len(lst)
        for i in bi.counter(self.repeats):
            inval = yield from stm.embed(lst[(i + offset) % size], inval)
        return inval


# class Pindex(ptt.Pattern):
#     # I don't see the difference with Pswitch, here or in sclang.
#     def __init__(self, lst, indx_pattern, repeats=1):
#         self.lst = lst
#         self.indx_pattern = indx_pattern
#         self.repeats = repeats
#
#     # storeArgs
#
#     def __embed__(self, inval):
#         lst_stream = stm.stream(self.lst)
#         indx_stream = None
#         indx_pattern = self.indx_pattern
#         lst = size = None
#         try:
#             for _ in bi.counter(self.repeats):
#                 lst = lst_stream.next(inval)  # raises StopStream
#                 size = len(lst)
#                 indx_stream = stm.stream(indx_pattern)
#                 for i in indx_stream:
#                     inval = yield from stm.embed(lst[i % size], inval)
#         except stm.StopStream:
#             pass
#         return inval


class Pswitch(ptt.Pattern):
    def __init__(self, lst, which=0):
        self.lst = lst
        self.which = which

    def __embed__(self, inval):
        lst = self.lst
        size = len(lst)
        indx_stream = stm.stream(self.which)
        indx = None
        try:
            while True:
                indx = indx_stream.next(inval)  # raises StopStream
                inval = yield from stm.embed(lst[indx % size], inval)
        except stm.StopStream:
            return inval

    # storeArgs


class Pswitch1(Pswitch):
    def __embed__(self, inval):
        stream_lst = [stm.stream(i) for i in self.lst]
        size = len(stream_lst)
        indx_stream = stm.stream(self.which)
        indx = None
        try:
            while True:
                indx = indx_stream.next(inval)
                inval = yield stream_lst[indx % size].next(inval)
        except stm.StopStream:
            return inval


class Ptuple(ListPattern):
    def __embed__(self, inval):
        for _ in bi.counter(self.repeats):
            stream_lst = [stm.stream(i) for i in self.lst]
            try:
                while True:
                    tpl = []
                    for i in stream_lst:
                        tpl.append(i.next(inval))
                    inval = yield tuple(tpl)  # real tuple or list?
            except stm.StopStream:
                pass
        return inval


class Place(Pseq):
    def __embed__(self, inval):
        lst = self.lst
        offset = self.offset
        lst = lst[offset:] + lst[:offset]
        for j in bi.counter(self.repeats):
            for item in lst:
                if isinstance(item, (list, tuple)):
                    item = item[j % len(item)]
                inval = yield from stm.embed(item, inval)
        return inval


class Placep(Pseq):  # Was Ppatlace.
    def __embed__(self, inval):
        lst = self.lst
        size = len(lst)
        offset = self.offset
        stream_lst = [stm.stream(i) for i in lst[offset:]]
        stream_lst += [stm.stream(i) for i in lst[:offset]]
        done = 0
        for _ in bi.counter(self.repeats):
            for item in stream_lst:
                try:
                    inval = yield item.next(inval)
                except stm.StopStream:
                    done += 1
            if done == size:
                break
            else:
                done = 0
        return inval


### Random ###

class Pshuffle(ListPattern):  # Pshuf
    def __embed__(self, inval):
        slist = self.lst[:]
        bi.shuffle(slist)
        for _ in bi.counter(self.repeats):
            for item in slist:
                inval = yield from stm.embed(item)
        return inval


class Prand(ListPattern):
    # repeats should be length.
    def __embed__(self, inval):
        lst = self.lst
        size = len(lst)
        for _ in bi.counter(self.repeats):
            inval = yield from stm.embed(lst[bi.rand(size)], inval)
        return inval


class Pxrand(ListPattern):
    # repeats should be length.
    def __embed__(self, inval):
        lst = self.lst
        size = len(lst)
        index = bi.rand(size)
        for _ in bi.counter(self.repeats):
            index = (index + bi.rand(size - 1) + 1) % size
            inval = yield from stm.embed(lst[index], inval)
        return inval


class Pwrand(ListPattern):
    # repeats should be length.
    def __init__(self, lst, weights=None, repeats=1):  #, *, cum_weights=None, k=1):
        super().__init__(lst, repeats)
        self.weights = weights
        # self.cum_weights = cum_weights
        # self.k = k

    def __embed__(self, inval):
        lst = self.lst
        weights = self.weights
        ilst = range(len(weights)) if weights else range(len(lst))
        indx = None
        wstream = stm.stream(weights)
        try:
            for _ in bi.counter(self.repeats):
                indx = bi.choices(ilst, wstream.next(inval))[0]  #, cum_weights=cw, k=k)
                inval = yield from stm.embed(lst[indx], inval)
        except stm.StopStream:
            pass
        return inval


class Pslide(ListPattern):
    # // 'repeats' is the number of segments.
    # // 'len' is the length of each segment.
    # // 'step' is how far to step the start of each segment from previous.
    # // 'start' is what index to start at.
    # // indexing wraps around if goes past beginning or end.
    # // step can be negative.

    def __init__(self, lst, length=3, step=1, start=0, wrap=True, repeats=1):
        super().__init__(lst, repeats)
        self.length = length
        self.step = step
        self.start = start
        self.wrap = wrap

    def __embed__(self, inval):
        lst = self.lst
        size = len(lst)
        pos = self.start
        wrap = self.wrap
        step_stream = stm.stream(self.step)
        len_stream = stm.stream(self.length)
        lval = None
        try:
            for _ in bi.counter(self.repeats):
                lval = len_stream.next(inval)  # raises StopStream
                if wrap:
                    for j in range(lval):
                        inval = yield from stm.embed(
                            lst[bi.mod(pos + j, size)], inval)
                else:
                    for j in range(lval):
                        if pos + j < size:
                            inval = yield from stm.embed(
                                lst[pos + j], inval)
                        else:
                            return inval
                pos += step_stream.next(inval)  # raises StopStream
        except stm.StopStream:
            pass
        return inval


class Pwalk(ListPattern):
    # // random walk pattern - hjh - jamshark70@gmail.com
    def __init__(self, lst, steps=None, directions=1, start=0):
        super().__init__(lst)
        self.steps = steps or Prand([-1, 1], float('inf'))
        self.directions = 1 if directions is None else directions
        self.start = start

    # storeArgs

    def __embed__(self, inval):
        lst = self.lst
        step = None
        size = len(lst)
        index = self.start
        step_stream = stm.stream(self.steps)
        direction_stream = stm.stream(self.directions)
        direction = direction_stream.next(inval)

        try:
            while True:
                step = step_stream.next(inval)  # raises StopStream
                inval = yield from stm.embed(lst[int(index)], inval)
                step *= direction
                if index + step < 0 or index + step >= size:
                    direction = direction_stream.next(inval)  # or 1  # raises StopStream
                    step = abs(step) * bi.sign(direction)
                index += step
                index %= size
        except stm.StopStream:
            return inval



### Finite State Machine ###

class Pfsm(ListPattern):
    # // Finite State Machine
    def __embed__(self, inval):
        lst = self.lst
        index = None
        max_state = ((len(lst) - 1) // 2) - 1
        for _ in bi.counter(self.repeats):
            index = 0
            while True:
                if lst[index] is None:
                    break
                index = bi.clip(bi.choice(lst[index]), 0, max_state) * 2 + 2
                item = lst[index - 1]
                if item is None:
                    break
                inval = yield from stm.embed(item, inval)
        return inval


class Pdfsm(ListPattern):
    # // Deterministic Finite State Machine
    def __init__(self, lst, start_state=0, repeats=1):
        super().__init__(lst, repeats)
        self.start_state = start_state

    def __embed__(self, inval):
        lst = self.lst
        start_state = self.start_state
        num_states = len(lst) - 1
        curr_state = sig_state = None
        sig = state = out_stream = None
        for _ in bi.counter(self.repeats):
            curr_state = start_state
            sig_state = stm.stream(lst[0])
            try:
                while True:
                    sig = sig_state.next(inval)  # raises StopStream
                    if sig is None:
                        break
                    state = lst[curr_state + 1]
                    if sig in state:
                        curr_state, out_stream = state[sig]
                    else:
                        curr_state, out_stream = state['default']
                    if curr_state is None or curr_state >= num_states:
                        break
                    inval = yield from stm.embed(out_stream, inval)
            except stm.StopStream:
                pass
        return inval
