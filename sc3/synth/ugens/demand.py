"""Demand.sc"""

from ...base import utils as utl
from ...base import builtins as bi
from .. import ugen as ugn
from .. import _graphparam as gpp
from . import line as lne
from . import bufio as bio


class Demand(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, trig, reset, demand_ugens):
        return cls._multi_new('audio', trig, reset, *utl.as_list(demand_ugens))

    @classmethod
    def kr(cls, trig, reset, demand_ugens):
        return cls._multi_new('control', trig, reset, *utl.as_list(demand_ugens))

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(len(self.inputs) - 2, self.rate)


class Duty(ugn.UGen):
    @classmethod
    def ar(cls, dur=1.0, reset=0.0, level=1.0, done_action=0):
        return cls._multi_new('audio', dur, reset, done_action, level)

    @classmethod
    def kr(cls, dur=1.0, reset=0.0, level=1.0, done_action=0):
        return cls._multi_new('control', dur, reset, done_action, level)

    def _check_inputs(self):
        if gpp.ugen_param(self.inputs[0])._as_ugen_rate() == 'demand':
            reset_rate = gpp.ugen_param(self.inputs[1])._as_ugen_rate()
            if reset_rate != 'demand'\
            and reset_rate != 'scalar'\
            and reset_rate != self.rate:
                return (f"reset input is not '{self.rate}' rate: "
                        f"{self.inputs[1]} is '{reset_rate}' rate")
            else:
                return None
        else:
            return self._check_valid_inputs()


class TDuty(Duty):
    @classmethod
    def ar(cls, dur=1.0, reset=0.0, level=1.0, done_action=0, gap_first=0):
        return cls._multi_new('audio', dur, reset, done_action,
                              level, gap_first)

    @classmethod
    def kr(cls, dur=1.0, reset=0.0, level=1.0, done_action=0, gap_first=0):
        return cls._multi_new('control', dur, reset, done_action,
                              level, gap_first)


class DemandEnvGen(ugn.UGen):
    @classmethod
    def ar(cls, level, dur, shape=1, curve=0, gate=1.0, reset=1.0,
           level_scale=1.0, level_bias=0.0, time_scale=1.0, done_action=0):
        gate_rate = gpp.ugen_param(gate)._as_ugen_rate()
        reset_rate = gpp.ugen_param(reset)._as_ugen_rate()
        if gate_rate == 'audio' or reset_rate == 'audio':
            if gate_rate != 'audio':
                gate = lne.K2A.ar(gate)
            if reset_rate != 'audio':
                reset = lne.K2A.ar(reset)
        return cls._multi_new('audio', level, dur, shape, curve, gate, reset,
                              level_scale, level_bias, time_scale, done_action)

    @classmethod
    def kr(cls, level, dur, shape=1, curve=0, gate=1.0, reset=1.0,
           level_scale=1.0, level_bias=0.0, time_scale=1.0, done_action=0):
        return cls._multi_new('control', level, dur, shape, curve, gate, reset,
                              level_scale, level_bias, time_scale, done_action)


class DUGen(ugn.UGen):
    _default_rate = 'demand'

    # // Some n-ary op special cases.

    def linlin(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return ((self.prune(inmin, inmax, clip) - inmin) /
                (inmax-inmin) * (outmax - outmin) + outMin)

    def linexp(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return (bi.pow(outmax / outmin, (self - inmin) / (inmax - inmin)) *
                outmin).prune(outmin, outmax, clip)

    def explin(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return (bi.log(self.prune(inmin, inmax, clip) / inmin) /
                bi.log(inmax / inmin) * (outmax - outmin) + outmin)

    def expexp(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return bi.pow(outmax / outmin,
                      bi.log(self.prune(inmin, inmax, clip / inmin) /
                             bi.log(inmax / inmin)) * outmin)


class Dseries(DUGen):
    @classmethod
    def dr(cls, start=1, step=1, length=float('inf')):
        return cls._multi_new('demand', length, start, step)


class Dgeom(DUGen):
    @classmethod
    def dr(cls, start=1, grow=1, length=float('inf')):
        return cls._multi_new('demand', length, start, grow)


class Dbufrd(DUGen):
    @classmethod
    def dr(cls, bufnum=0, phase=0.0, loop=1.0):
        return cls._multi_new('demand', bufnum, phase, loop)


class Dbufwr(DUGen):
    @classmethod
    def dr(cls, input=0.0, bufnum=0, phase=0.0, loop=1.0):
        return cls._multi_new('demand', bufnum, phase, input, loop)


class ListDUGen(DUGen):
    @classmethod
    def dr(cls, lst, repeats=1):
        return cls._multi_new('demand', repeats, *utl.as_list(lst))


class Dseq(ListDUGen):
    pass


class Dser(ListDUGen):
    pass


class Dshuf(ListDUGen):
    pass


class Drand(ListDUGen):
    pass


class Dxrand(ListDUGen):
    pass


class Dwrand(DUGen):
    @classmethod
    def dr(cls, lst, weights, repeats=1):
        size = len(lst)
        weights = utl.extend(weights, size, 0.0)
        return cls._multi_new('demand', repeats, size, *weights, *lst)


class Dswitch1(DUGen):
    @classmethod
    def dr(cls, lst, index):
        return cls._multi_new('demand', index, *lst)


class Dswitch(Dswitch1):
    pass


class Dwhite(DUGen):
    @classmethod
    def dr(cls, lo=0.0, hi=1.0, length=float('inf')):
        return cls._multi_new('demand', length, lo, hi)


class Diwhite(Dwhite):
    pass


class Dbrown(DUGen):
    @classmethod
    def dr(cls, lo=0.0, hi=1.0, step=0.01, length=float('inf')):
        return cls._multi_new('demand', length, lo, hi, step)


class Dibrown(Dbrown):
    pass


class Dstutter(DUGen):
    @classmethod
    def dr(cls, n, input):
        return cls._multi_new('demand', n, input)


class Dconst(DUGen):
    @classmethod
    def dr(cls, sum, input, tolerance=0.001):
        return cls._multi_new('demand', sum, input, tolerance)


class Dreset(DUGen):
    @classmethod
    def dr(cls, input, reset=0.0):
        return cls._multi_new('demand', input, reset)


class Dpoll(DUGen):
    @classmethod
    def dr(cls, input, label=None, run=1, trig_id=-1):
        return cls._multi_new('demand', input, label, run, trig_id)

    @classmethod
    def _new1(cls, rate, input, label, run, trig_id):  # override
        label = label or f'DemandUGen({type(input).__name__})'
        label = [int(x) for x in bytes(label, 'utf-8')]  # *** TODO: sc ascii method, sclang uses signed values, see Poll.
        obj = cls._create_ugen_object(rate)
        obj._add_to_synth()
        return obj._init_ugen(input, trig_id, run, len(label), *label)


class Dunique(ugn.PseudoUGen):
    _default_rate = 'demand'

    @classmethod
    def dr(cls, source, max_buffer_size=1024, protected=True):
        obj = cls._create_ugen_object('demand')
        obj._init(source, max_buffer_size, protected)
        return obj

    def _init(self, source, max_buffer_size, protected):
        self._protected = bool(protected)
        self._buffer = bio.LocalBuf.new(max_buffer_size)
        self._buffer.clear()
        if self._protected:
            self._iwr = bio.LocalBuf.new(1)
            self._iwr.clear()
            # // Here we also limit to the largest integer a 32bit float
            # // can correctly address.
            self._writer = Dbufwr.new(
                source,  self._buffer,
                Dbufwr.new(Dseries.new(0, 1, 16777216), self._iwr), 1)
        else:
            self._iwr = None
            # // Here we can simply loop.
            self._writer = Dbufwr.new(
                source, self._buffer,
                Dseq.new([Dseries.new(0, 1, max_buffer_size)], float('inf')), 0)

    def _as_ugen_input(self, *_):
        # // We call the writer from each reader.
        brd = self._buffer.first_arg(self._writer)
        if self._protected:
            ird = bio.LocalBuf.new(1)
            ird.clear()
            index = Dbufwr.new(Dseries.new(0, 1, float('inf')), ird)
            overrun = (Dbufrd.new(self._iwr) - Dbufrd.new(ird)) >\
                      self._buffer.num_frames
            # // Catch buffer overrun by switching to a zero length series.
            brd = Dswitch1.new([brd, Dseries.new(length=0)], overrun)
        else:
            index = Dseq.new(
                [Dseries.new(0, 1, self._buffer.num_frames)], float('inf'))
        return Dbufrd.new(brd, index, 1)
