"""Ppatmod.sc"""

from ...base import stream as stm
from .. import pattern as ptt


class Pvalue(ptt.Pattern):
    # This pattern is for special cases where common
    # values aren't or can't be embeded as streams.
    def __init__(self, value):
        self.value = value

    def __embed__(self, inval):
        return (yield from stm.stream(self.value))

    # storeArgs


class Plazy(ptt.Pattern):
    def __init__(self, func):
        self.func = func

    def __embed__(self, inval):
        return (yield from stm.embed(self.func(inval), inval))

    # storeArgs
