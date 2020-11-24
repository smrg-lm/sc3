"""Env.sc"""

import copy
import operator

from ..base import main as _libsc3
from ..base import utils as utl
from ..base import builtins as bi
from . import _graphparam as gpp
from .ugens import trig as trg
from .ugens import oscillators as ocl


__all__ = ['Env']


class Env(gpp.UGenParameter, gpp.NodeParameter):
    _SHAPE_NAMES = {
        'step': 0,
        'lin': 1,
        'linear': 1,
        'exp': 2,
        'exponential': 2,
        'sin': 3,
        'sine': 3,
        'wel': 4,
        'welch': 4,
        'sqrt': 6,
        'squared': 6,
        'cub': 7,
        'cubed': 7,
        'hold': 8
    }

    def __init__(self, levels=None, times=None, curves='lin',
                 release_node=None, loop_node=None, offset=0):
        super(gpp.UGenParameter, self).__init__(self)
        self.levels = levels or [0, 1, 0]  # Can't be empty or zero either.
        self.times = utl.wrap_extend(
            utl.as_list(times or [1, 1]), len(self.levels) - 1)
        self.curves = curves
        self.release_node = release_node
        self.loop_node = loop_node
        self.offset = offset
        self._envgen_format = None
        self._interpolation_format = None

    # no newClear
    # no kr
    # no ar
    # no setters

    # // Methods to make some typical shapes.

    # // Fixed duration envelopes.

    @classmethod
    def xyc(cls, xyc):
        if any(len(i) != 3 for i in xyc):
            raise ValueError('xyc list must contain only sequences of length 3')
        xyc = xyc[:]  # Ensures internal state.
        xyc.sort(key=lambda x: x[0])
        times, levels, curves = utl.flop(xyc)
        offset = times[0]
        times = [b - a for a, b in utl.pairwise(times)]  # differentiate
        curves.pop(-1)
        return cls(levels, times, curves, offset=offset)

    @classmethod
    def pairs(cls, pairs, curves=None):
        pairs = pairs[:]  # Ensures internal state.
        if curves is None:
            for i in range(len(pairs)):
                pairs[i].append('lin')
        elif isinstance(curves, str):
            for i in range(len(pairs)):
                pairs[i].append(curves)
        else:
            if len(pairs) != len(curves):
                raise ValueError('pairs and curves must have the same length')
            for i in range(len(pairs)):
                pairs[i].append(curves[i])
        return cls.xyc(pairs)

    @classmethod
    def triangle(cls, dur=1.0, level=1.0):
        dur *= 0.5
        return cls([0, level, 0], [dur, dur])

    @classmethod
    def sine(cls, dur=1.0, level=1.0):
        dur *= 0.5
        return cls([0, level, 0], [dur, dur], 'sine')

    @classmethod
    def perc(cls, attack_time=0.01, release_time=1.0, level=1.0, curve=-4.0):
        return cls([0, level, 0], [attack_time, release_time], curve)

    @classmethod
    def linen(cls, attack_time=0.01, sustain_time=1.0, release_time=1.0,
              level=1.0, curve='lin'):
        return cls(
            [0, level, level, 0],
            [attack_time, sustain_time, release_time], curve)

    @classmethod
    def step(cls, levels=None, times=None, release_node=None,
             loop_node=None, offset=0):
        levels = levels or [0, 1]
        times = times or [1, 1]
        if len(levels) != len(times):
            raise ValueError('levels and times must have same length')
        levels = levels[:]  # Ensures internal state.
        levels.insert(0, levels[0])
        return Env(levels, times, 'step', release_node, loop_node, offset)

    # // Envelopes with sustain.

    @classmethod
    def cutoff(cls, release_time=0.1, level=1.0, curve='lin'):
        curve_no = cls._shape_number(curve)
        release_level = bi.dbamp(-100) if curve_no == 2 else 0
        return cls([level, release_level], [release_time], curve, 0)

    @classmethod
    def dadsr(cls, delay_time=0.1, attack_time=0.01, decay_time=0.3,
              sustain_level=0.5, release_time=1.0, peak_level=1.0,
              curve=-4.0, bias=0.0):
        return cls(
            utl.list_binop(
                operator.add,
                [0, 0, peak_level, peak_level * sustain_level, 0], bias),
            [delay_time, attack_time, decay_time, release_time], curve, 3)

    @classmethod
    def adsr(cls, attack_time=0.01, decay_time=0.3, sustain_level=0.5,
             release_time=1.0, peak_level=1.0, curve=-4.0, bias=0.0):
        return cls(
            utl.list_binop(
                operator.add,
                [0, peak_level, peak_level * sustain_level, 0], bias),
            [attack_time, decay_time, release_time], curve, 2)

    @classmethod
    def asr(cls, attack_time=0.01, sustain_level=1.0,
            release_time=1.0, curve=-4.0):
        return cls(
            [0, sustain_level, 0], [attack_time, release_time], curve, 1)

    @classmethod
    def cyclic(cls, levels, times, curves='lin'):  # was *circle
        times = utl.wrap_extend(utl.as_list(times), len(levels))
        last_time = times.pop()
        curves = utl.wrap_extend(utl.as_list(curves), len(levels))
        last_curve = curves.pop()
        return cls(levels, times, curves).circle(last_time, last_curve)

    def circle(self, last_time=0.0, last_curve='lin'):
        # // Connect releaseNode (or end) to first node of envelope.
        if _libsc3.main._current_synthdef is None:
            raise Exception('circle can only be used within graph functions')
        first_0_then_1 = trg.Latch.kr(1.0, ocl.Impulse.kr(0.0))
        if self.release_node is None:
            self.levels = [0.0, *self.levels, 0.0]
            self.curves = ult.wrap_extend(
                utl.as_list(self.curves), len(self.times))
            self.curves = [last_curve, *self.curves, 'lin']
            self.times = [
                first_0_then_1 * last_time, *self.times, float('inf')]
            self.release_node = len(self.levels) - 2
        else:
            self.levels = [0.0, *self.levels]
            self.curves = ult.wrap_extend(
                utl.as_list(self.curves), len(self.times))
            self.curves = [last_curve, *self.curves]
            self.times = [first_0_then_1 * last_time, *self.times]
            self.release_node += 1
        self.loop_node = 0
        return self

    @property
    def duration(self):
        return utl.list_sum(self.times)

    @duration.setter
    def duration(self, value):
        res = utl.list_binop(
            operator.mul, self.times, 1 / self.total_duration())
        self.times = utl.list_binop(operator.mul, res, value)

    def total_duration(self):
        duration = utl.list_sum(self.times)
        return utl.list_max(utl.as_list(duration))

    @property
    def release_time(self):
        if self.release_node is None:
            return 0.0
        else:
            return utl.list_sum(self.times[self.release_node:])

    @property
    def is_sustained(self):
        return self.release_node is not None

    def range(self, lo=0.0, hi=1.0):
        obj = copy.copy(self)
        min = utl.list_min(obj.levels)
        max = utl.list_max(obj.levels)
        obj.levels = utl.list_narop(bi.linlin, obj.levels, min, max, lo, hi)
        return obj

    def exprange(self, lo=0.01, hi=1.0):
        obj = copy.copy(self)
        min = utl.list_min(obj.levels)
        max = utl.list_max(obj.levels)
        obj.levels = utl.list_narop(bi.linexp, obj.levels, min, max, lo, hi)
        return obj

    def curverange(self, lo=0.0, hi=1.0, curve=-4):
        obj = copy.copy(self)
        min = utl.list_min(obj.levels)
        max = utl.list_max(obj.levels)
        obj.levels = utl.list_narop(
            bi.lincurve, obj.levels, min, max, lo, hi, curve)
        return obj

    # TODO
    # asMultichannelSignal
    # asSignal
    # discretize
    # storeArgs
    # ==
    # hash
    # at
    # embedInStream
    # asStream
    # asPseg
    # blend
    # delay
    # circle (moved up)
    # test

    @classmethod
    def _shape_number(cls, name):
        name = utl.as_list(name)
        ret = []
        for item in name:
            if gpp.ugen_param(item)._is_valid_ugen_input():
                ret.append(5)  # 'curvature value', items is not NaN SimpleNumber.
            else:
                try:
                    shape = cls._SHAPE_NAMES[item]
                    ret.append(shape)
                except KeyError as e:
                     raise ValueError(f"invalid Env shape '{item}'") from e
        return utl.unbubble(ret)

    @classmethod
    def _curve_value(cls, curve):
        if isinstance(curve, list):
            ret = []
            for item in curve:
                if gpp.ugen_param(item)._is_valid_ugen_input():
                    ret.append(item)
                else:
                    ret.append(0)
            return ret
        else:
            if gpp.ugen_param(curve)._is_valid_ugen_input():
                return curve
            else:
                return 0

    def envgen_format(self):  # Was asMultichannelArray.
        if self._envgen_format:  # this.array
            return self._envgen_format

        # prAsArray
        levels = gpp.ugen_param(self.levels)._as_ugen_input()
        times = gpp.ugen_param(self.times)._as_ugen_input()
        curves = gpp.ugen_param(utl.as_list(self.curves))._as_ugen_input()
        size = len(self.times)
        contents = []

        contents.append(levels[0])
        contents.append(size)
        aux_input = gpp.ugen_param(self.release_node)._as_ugen_input()
        if aux_input is None:
            aux_input = -99
        contents.append(aux_input)
        aux_input = gpp.ugen_param(self.loop_node)._as_ugen_input()
        if aux_input is None:
            aux_input = -99
        contents.append(aux_input)

        for i in range(size):
            contents.append(levels[i + 1])
            contents.append(times[i])
            contents.append(type(self)._shape_number(curves[i % len(curves)]))
            contents.append(type(self)._curve_value(curves[i % len(curves)]))

        self._envgen_format = [tuple(i) for i in utl.flop(contents)]
        return self._envgen_format

    def interpolation_format(self):
        '''This version is for IEnvGen which has a special format.'''
        if self._interpolation_format:
            return self._interpolation_format

        levels = gpp.ugen_param(self.levels)._as_ugen_input()
        times = gpp.ugen_param(self.times)._as_ugen_input()
        curves = gpp.ugen_param(utl.as_list(self.curves))._as_ugen_input()
        size = len(self.times)
        contents = []

        aux_input = gpp.ugen_param(self.offset)._as_ugen_input()
        if aux_input is None:
            aux_input = 0
        contents.append(aux_input)
        contents.append(levels[0])
        contents.append(size)
        contents.append(utl.list_sum(times))

        for i in range(size):
            contents.append(times[i])
            contents.append(type(self)._shape_number(curves[i % len(curves)]))
            contents.append(type(self)._curve_value(curves[i % len(curves)]))
            contents.append(levels[i + 1])

        self._interpolation_format = [tuple(i) for i in utl.flop(contents)]
        return self._interpolation_format


    ### Node parameter interface ###

    def _as_control_input(self):
        return utl.unbubble(self.envgen_format())

    def _embed_as_osc_arg(self, lst):
        gpp.node_param(self._as_control_input())._embed_as_osc_arg(lst)
