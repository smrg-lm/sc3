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
                                     len(self.levels) - 1) # *** BUG: esto funciona si es multicanal?
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
        pass # TODO

    # BUG: si se necesita que sea general para otras clases hacer también __iter__?
    # BUG: y que EnvGen siempre reciba un array de tuplas en envelope
    # BUG: (como está hecho en sclang), pero no le veo sentido a simple vista.
    def envgen_format(self):  # asMultichannelArray, se usa solo en Env y EnvGen.
        if self._envgen_format is None:  # this.array
            self._envgen_format = self._as_array()  # prAsArray
        return self._envgen_format

    def _as_array(self):
        pass  # TODO: prAsArray, si hay variantes hacer dentro de envgen_format.

    ### UGen graph parameter interface ###
    # TODO: ver el resto en UGenParameter

    def as_control_input(self):
        pass # TODO

    ### Node parameter interface ###

    def as_osc_arg_embedded_list(self, lst):
        env_lst = gpp.ugen_param(self).as_control_input()
        return gpp.node_param(env_lst).as_osc_arg_embedded_list(lst)
