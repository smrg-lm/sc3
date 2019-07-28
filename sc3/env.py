"""Env.sc"""

from . import graphparam as gpp
from . import utils as utl


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
        self.levels = levels or [0, 1, 0]
        self.times = utl.wrap_extend(utl.as_list(times or [1, 1]),
                                     len(self.levels) - 1)
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
        xyc = xyc[:]  # sclang don't modify the parameter
        xyc.sort(key=lambda x: x[0])
        times, levels, curves = utl.flop(xyc)
        offset = times[0]
        times = [b - a for a, b in utl.pairwise(times)]  # differentiate
        curves.pop(-1)  # BUG: in sclang asArray.drop(-1) is not reasigned.
        return cls(levels, times, curves, offset=offset)

    @classmethod
    def pairs(cls, pairs, curves=None):
        pairs = pairs[:]  # sclang may use a copy
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
        pass # TODO

    @classmethod
    def sine(cls, dur=1.0, level=1.0):
        pass # TODO

    @classmethod
    def perc(cls, attack_time=0.01, release_time=1.0, level=1.0, curve=-4.0):
        pass # TODO

    @classmethod
    def linen(cls, attack_time=0.01, sustain_time=1.0, release_time=1.0,
              level=1.0, curve='lin'):
        pass # TODO

    @classmethod
    def step(cls, levels=None, times=None, release_node=None,
             loop_node=None, offset=0):
        levels = levels or [0, 1]
        times = times or [1, 1]
        if len(levels) != len(times):
            raise ValueError('levels and times must have same length')
        levels = levels[:]  # sclang don't modify the parameter
        levels.insert(0, levels[0])
        return Env(levels, times, 'step', release_node, loop_node, offset)

    # // Envelopes with sustain.

    @classmethod
    def cutoff(cls, release_time=0.1, level=1.0, curve='lin'):
        pass # TODO

    @classmethod
    def dadsr(cls, delay_time=0.1, attack_time=0.01, decay_time=0.3,
              sustain_level=0.5, release_time=1.0, peak_level=1.0,
              curve=-4.0, bias=0.0):
        pass # TODO

    @classmethod
    def adsr(cls, attack_time=0.01, decay_time=0.3, sustain_level=0.5,
             release_time=1.0, peak_level=1.0, curve=-4.0, bias=0.0):
        pass # TODO

    @classmethod
    def asr(cls, attack_time=0.01, sustain_level=1.0,
            release_time=1.0, curve=-4.0):
        pass # TODO

    @classmethod
    def circle(cls, levels, times, curve='lin'):
        pass # TODO


    @property
    def duration(self):
        return utl.list_sum(self.times)

    @duration.setter
    def duration(self, value):
        res = utl.list_binop('mul', self.times, 1 / self.total_duration())
        self.times = utl.list_binop('mul', res, value)

    def total_duration(self):
        duration = utl.list_sum(self.times)
        return utl.list_max(utl.as_list(duration))

    def range(self, lo=0.0, hi=1.0):
        pass # TODO

    def exprange(self, lo=0.01, hi=1.0):
        pass # TODO

    def curverange(self, lo=0.0, hi=1.0, curve=-4):
        pass # TODO

    def release_time(self):
        if self.release_node is None:
            return 0.0
        else:
            return utl.list_sum(self.times[self.release_node:])

    def sustained(self):  # is_sustained
        return self.release_node is not None

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
    # circle (instancia)
    # test

    @classmethod
    def _shape_number(cls, name):
        name = utl.as_list(name)
        ret = []
        for item in name:
            if gpp.ugen_param(item).is_valid_ugen_input():
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
                if gpp.ugen_param(item).is_valid_ugen_input():
                    ret.append(item)
                else:
                    ret.append(0)
            return ret
        else:
            if gpp.ugen_param(curve).is_valid_ugen_input():
                return curve
            else:
                return 0

    def envgen_format(self):  # asMultichannelArray, se usa solo en Env y EnvGen.
        if self._envgen_format:  # this.array
            return self._envgen_format

        # prAsArray
        levels = gpp.ugen_param(self.levels).as_ugen_input()
        times = gpp.ugen_param(self.times).as_ugen_input()
        curves = gpp.ugen_param(utl.as_list(self.curves)).as_ugen_input()
        size = len(self.times)
        contents = []

        contents.append(levels[0])
        contents.append(size)
        contents.append(gpp.ugen_param(self.release_node).as_ugen_input() or -99)
        contents.append(gpp.ugen_param(self.loop_node).as_ugen_input() or -99)

        for i in range(size):
            contents.append(levels[i + 1])
            contents.append(times[i])
            contents.append(type(self)._shape_number(curves[i % len(curves)]))
            contents.append(type(self)._curve_value(curves[i % len(curves)]))

        self._envgen_format = utl.flop(contents)
        return self._envgen_format

    def interpolation_format(self):
        '''This version is for IEnvGen which has a special format.'''
        if self._interpolation_format:
            return self._interpolation_format

        levels = gpp.ugen_param(self.levels).as_ugen_input()
        times = gpp.ugen_param(self.times).as_ugen_input()
        curves = gpp.ugen_param(utl.as_list(self.curves)).as_ugen_input()
        size = len(self.times)
        contents = []

        contents.append(gpp.ugen_param(self.offset).as_ugen_input() or 0)
        contents.append(levels[0])
        contents.append(size)
        contents.append(utl.list_sum(times))
        # curvesArray = curves.asArray; # BUG: sclang, overides curvesArray without as_ugen_input.

        for i in range(size):  # BUG: sclang, uses times.size.do instead of size that is timeArray.size that is times.asUGenInput.
            contents.append(times[i])
            contents.append(type(self)._shape_number(curves[i % len(curves)]))
            contents.append(type(self)._curve_value(curves[i % len(curves)]))
            contents.append(levels[i + 1])

        self._interpolation_format = utl.flop(contents)
        return self._interpolation_format

    ### UGen graph parameter interface ###
    # TODO: ver el resto en UGenParameter

    def as_control_input(self):
        pass # TODO

    ### Node parameter interface ###

    def as_osc_arg_embedded_list(self, lst):
        env_lst = gpp.ugen_param(self).as_control_input()
        return gpp.node_param(env_lst).as_osc_arg_embedded_list(lst)
