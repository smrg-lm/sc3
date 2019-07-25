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

    # no newClear
    # no kr
    # no ar
    # no setters

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

    # TODO: move followin contructors after __init__, group instance methods.

    # TODO: sigue...

    @classmethod
    def _shape_number(cls, name):
        name = utl.as_list(name)
        print('name', name)
        ret = []
        for item in name:
            if gpp.ugen_param(item).is_valid_ugen_input():
                ret.append(5)  # 'curvature value', items is not NaN SimpleNumber.
            else:
                shape = cls._SHAPE_NAMES[item]  # KeyError, 'invalid Env shape'
                # if shape is None:
                #     raise ValueError('invalid Env shape')
                ret.append(shape)
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


    ### UGen graph parameter interface ###
    # TODO: ver el resto en UGenParameter

    def as_control_input(self):
        pass # TODO

    ### Node parameter interface ###

    def as_osc_arg_embedded_list(self, lst):
        env_lst = gpp.ugen_param(self).as_control_input()
        return gpp.node_param(env_lst).as_osc_arg_embedded_list(lst)
