"""AbstractFunction.sc"""

import inspect

from . import absobject as aob
from . import builtins as bi


__all__ = ['value', 'Function', 'function']


def value(obj, *args, **kwargs):
    '''
    Utility function for optional value/function parameters like
    `completion_msg`. If obj is a function it gets evaluated with `*args`
    and `**kwargs` and the result is returned, else obj is returned as is.
    Spare parameters are discarded.
    '''

    if callable(obj):
        parameters = inspect.signature(obj).parameters
        if any(p.kind == p.VAR_POSITIONAL for p in parameters.values()):
            return obj(*args, **kwargs)
        else:
            nargs = len(parameters)
            return obj(*args[:nargs], **kwargs)
    else:
        return obj


class AbstractFunction(aob.AbstractObject):
    def __call__(self, *args):
        raise NotImplementedError(
            f'{type(self).__name__} does not implement __call__')


    ### AbstractObject interface ###

    def _compose_unop(self, selector):
        return UnopFunction(selector, self)

    def _compose_binop(self, selector, other):
        return BinopFunction(selector, self, other)

    def _rcompose_binop(self, selector, other):
        return BinopFunction(selector, other, self)

    def _compose_narop(self, selector, *args):
        return NaropFunction(selector, self, *args)

    # applyTo
    # <> function composition

    def sampled(self, n=80, from_=0.0, to=1.0):
        range_ = to - from_
        step = range_ / (n - 1)
        end = range_ / step + 1
        start = int(from_)
        offset = from_ - start
        values = []
        for i in range(start, int(end)):
            values.append(self(i * step + offset))

        def sampled_func(x):
            pos = (bi.clip(x, from_, to) - from_) / (to - from_) * (n - 1)
            i = bi.ceil(pos) - 1  # i = int(bi.roundup(pos)) - 1  # ceil(x) -> int
            return bi.blend(values[i], values[i + 1], bi.absdif(pos, i))  # uses blendAt from Object.

        return sampled_func

    # ### UGen graph parameter interface ###
    # # Is a mistake to make AbstractFunction an UGenParameter because some
    # # subclases are not (e.g. every stream), if needed it could be better to
    # # create a ugen_param for functions, callables or alike.
    #
    # def _is_valid_ugen_input(self):
    #     return True
    #
    # def _as_ugen_input(self, *ugen_cls):
    #     return self(*ugen_cls)
    #
    # def _as_control_input(self):  # Is NodeParameter interface.
    #     return self()
    #
    # def _as_audio_rate_input(self, *args):
    #     res = self(*args)
    #     if gpp.ugen_param(res)._as_ugen_rate() != 'audio':
    #         return xxx.K2A.ar(res)
    #     return res


class UnopFunction(AbstractFunction):
    def __init__(self, selector, a):
        self.selector = selector
        self.a = a

    def __call__(self, *args, **kwargs):
        return self.selector(self.a(*args, **kwargs))

    def __repr__(self):
        return f'{type(self).__name__}({self.selector.__name__}, {self.a})'


class BinopFunction(AbstractFunction):
    def __init__(self, selector, a, b):
        self.selector = selector
        self.a = a
        self.b = b

    def __call__(self, *args, **kwargs):
        a_value = self.a(*args, **kwargs) if callable(self.a) else self.a
        b_value = self.b(*args, **kwargs) if callable(self.b) else self.b
        return self.selector(a_value, b_value)

    def __repr__(self):
        return (
            f'{type(self).__name__}({self.selector.__name__}, '
            f'{self.a}, {self.b})')


class NaropFunction(AbstractFunction):
    def __init__(self, selector, a, *args):
        self.selector = selector
        self.a = a
        self.args = args

    def __call__(self, *args, **kwargs):
        evaluated_args = [
            x(*args, **kwargs) if isinstance(x, Function)
            else x for x in self.args]
        return self.selector(self.a(*args, **kwargs), *evaluated_args)

    def __repr__(self):
        return (
            f'{type(self).__name__}({self.selector.__name__}, '
            f'{self.a}, {self.args})')


# class FunctionList(AbstractFunction):
#     ...


### Function.sc ###

class Function(AbstractFunction):
    '''
    This class is a wrapper for ordinary function which adds lazy
    evaluation capabilities (`AbstractObject` interface) and the interface
    needed to scheduled functions in clocks.

    Note that any user defined function scheduled in clocks are internally
    wrapped in this class and there is no need to wrap them explicitly
    for that purpose.
    '''

    def __init__(self, func):
        if inspect.isfunction(func):
            parameters = inspect.signature(func).parameters
            self._nargs = len(parameters)
            self._kwords = parameters.keys()
            self.func = func
            self._clock = None  # Internal compatibility as Clock item.
        else:
            raise TypeError(
                'Function wrapper only apply to user-defined functions')

    def __call__(self, *args, **kwargs):
        kwargs = {k: kwargs[k] for k in kwargs.keys() & self._kwords}
        return self.func(*args[:self._nargs], **kwargs)

    def __awake__(self, clock):
        return self.func(*(self, clock)[:self._nargs])

    def __repr__(self):
        return f'{type(self).__name__}({self.func.__qualname__})'


# decorator syntax
def function(func):
    '''Decorator to wrap ordinary function types as `AbstractObject`.

    This function is redundant with the `Function` class, it returns an
    instance of that class, but its use is recommended when used as decorator.
    '''

    return Function(func)


# Thunk
# UGenThunk
