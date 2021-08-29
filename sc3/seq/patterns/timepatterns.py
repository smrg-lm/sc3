
from ...base import main as _libsc3
from ...base import builtins as bi
from ...base import stream as stm
from ...synth import envelope as evp
from .. import pattern as ptt
from . import listpatterns as lsp


class TimePattern(ptt.Pattern):
    pass


class Pstep(TimePattern):
    def __init__(self, levels, durs=1, repeats=1):
        self.levels = levels
        self.durs = durs
        self.repeats = repeats

    def __embed__(self, inval):
        # Moved here so input values are not changed, despite overhead.
        levels = lsp.Pseq(self.levels) if isinstance(self.levels, list) else self.levels
        durs = lsp.Pseq(self.durs) if isinstance(self.durs, list) else self.durs

        end_beat = _libsc3.main.current_tt._beats
        ld_stream = val = dur = None

        for _ in bi.counter(self.repeats):
            ld_stream = stm.stream(lsp.Ptuple([levels, durs]))
            try:
                while True:
                    val, dur = ld_stream.next(inval)
                    end_beat += dur
                    while end_beat > _libsc3.main.current_tt._beats:
                        inval = yield from stm.embed(val, inval)
            except stm.StopStream:
                pass
        return inval

    # storeArgs


class Pseg(TimePattern):
    def __init__(self, levels, durs=1, curves='lin', repeats=1):
        self.levels = levels
        self.durs = durs
        self.curves = curves
        self.repeats = repeats

    def __embed__(self, inval):
        levels = lsp.Pseq(self.levels) if isinstance(self.levels, list) else self.levels
        durs = lsp.Pseq(self.durs) if isinstance(self.durs, list) else self.durs
        curves = lsp.Pseq(self.curves) if isinstance(self.curves, list) else self.curves

        val_stream = dur_stream = cur_stream = None
        start_val = val = dur = curve = None
        start_beat = current_beat = end_beat = None
        env = None

        for _ in bi.counter(self.repeats):
            val_stream = stm.stream(levels)
            dur_stream = stm.stream(durs)
            cur_stream = stm.stream(curves)
            val = val_stream.next(inval)  # Should not be an empty stream.
            end_beat = _libsc3.main.current_tt._beats
            try:
                while True:
                    start_val = val
                    val = val_stream.next(inval)
                    dur = dur_stream.next(inval)
                    curve = cur_stream.next(inval)
                    start_beat = end_beat
                    end_beat += dur
                    # Pseg does not really support multichannel expansion for
                    # two  reasons, it's not the common behaviour in patterns
                    # and expanding durs should create multiple time streams.
                    env = evp.Env([start_val, val], dur, curve)
                    current_beat = _libsc3.main.current_tt._beats
                    while end_beat > current_beat:
                        inval = yield env._at(current_beat - start_beat)
                        current_beat = _libsc3.main.current_tt._beats
            except stm.StopStream:
                pass
        return inval

    # storeArgs
