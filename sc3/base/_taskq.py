
import heapq
import itertools


__all__ = ['TaskQueue']


class TaskQueue():
    """
    This class is an encapsulation of the algorithm found in heapq
    documentation. heapq module in itself use the same principles as
    SuperCollider's clocks implementation. TaskQueue is not thread safe.
    """

    class _REMOVED(): pass

    def __init__(self):
        self._init()

    def _init(self):
        self._queue = []
        self._entry_finder = {}
        self._counter = itertools.count()
        self._removed_counter = 0

    def add(self, prio, task):
        '''Add a new task or update the prio of an existing task.'''
        if task in self._entry_finder:
            self.remove(task)
        count = next(self._counter)
        entry = [prio, count, task]
        self._entry_finder[task] = entry
        heapq.heappush(self._queue, entry)

    def remove(self, task):
        '''Remove an existing task. Does nothing if not found.'''
        try:
            entry = self._entry_finder.pop(task)
            entry[-1] = type(self)._REMOVED
            self._removed_counter += 1
        except KeyError:
            return

    def pop(self):
        '''
        Remove and return the lowest prio entry as a tuple (prio, task).
        Raise KeyError if empty.
        '''
        while self._queue:
            prio, count, task = heapq.heappop(self._queue)
            if task is not type(self)._REMOVED:
                del self._entry_finder[task]
                return (prio, task)
            else:
                self._removed_counter -= 1
        raise KeyError('pop from an empty task queue')

    def peek(self, smallest=True):
        '''
        Return the lowest/highest prio entry as a tuple (prio, task) without
        removing it. Raise KeyError if empty.
        '''
        if self._queue:
            if smallest:
                prio, count, task = heapq.nsmallest(
                    1, self._queue, key=self._small_key)[0]
            else:
                prio, count, task = heapq.nlargest(
                    1, self._queue, key=self._large_key)[0]
            if task is not self._REMOVED:
                return (prio, task)
        raise KeyError('peek from an empty task queue')

    def _small_key(self, item):
        if item[2] is type(self)._REMOVED:
            return [float('inf')] * 2
        else:
            return item[:2]

    def _large_key(self, item):
        if item[2] is type(self)._REMOVED:
            return [float('-inf')] * 2
        else:
            return item[:2]

    def empty(self):
        '''Return True if queue is empty.'''
        return (len(self._queue) - self._removed_counter) == 0

    def clear(self):
        '''Reset the queue to initial state (remove all tasks).'''
        self._init()

    def __iter__(self):
        # FIXME: Returns a generator but creates the whole list first.
        queue = heapq.nsmallest(len(self._queue), self._queue)
        for prio, count, task in queue:
            if task is not type(self)._REMOVED:
                yield (prio, task)

    # def __copy__(self):
    #     ...
