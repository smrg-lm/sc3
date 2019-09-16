"""BufIO.sc"""

from .. import ugen as ugn


class PlayBuf(ugn.MultiOutUGen):
    ...


class TGrains(ugn.MultiOutUGen):
    ...


# SimpleLoopBuf, missing ugen.


class BufRd(ugn.MultiOutUGen):
    ...


class BufWr(ugn.UGen):
    ...


class RecordBuf(ugn.UGen):
    ...


class ScopeOut(ugn.UGen):
    ...


class ScopeOut2(ugn.UGen):
    ...


class Tap(ugn.UGen):
    ...


class LocalBuf(ugn.WidthFirstUGen):
    ...


class MaxLocalBufs(ugn.UGen):
    ...


class SetBuf(ugn.WidthFirstUGen):
    ...


class ClearBuf(ugn.WidthFirstUGen):
    ...
