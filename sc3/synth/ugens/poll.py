"""Poll.sc"""

from ...base import utils as utl
from .. import ugen as ugn
from .. import _graphparam as gpp
from . import oscillators as ocl


class Poll(ugn.UGen):
    @classmethod
    def ar(cls, trig, input, label=None, trig_id=-1):
        cls._multi_new_list(['audio', trig, input, label, trig_id])
        return input

    @classmethod
    def kr(cls, trig, input, label=None, trig_id=-1):
        cls._multi_new_list(['control', trig, input, label, trig_id])
        return input

    @classmethod
    def new(cls, trig, input, label=None, trig_id=-1):
        rate = [gpp.ugen_param(item)._as_ugen_rate() for item in utl.as_list(input)]
        rate = utl.unbubble(rate)
        cls._multi_new_list([rate, trig, input, label, trig_id])
        return input

    @classmethod
    def _new1(cls, rate, trig, input, label, trig_id):
        label = label or f'UGen({type(input).__name__})'
        label = [int(x) for x in bytes(label, 'utf-8')]  # *** TODO: sc ascii method
        # label = [x - 256 if x > 127 else x for x in bytes(label, 'utf-8')]  # sclang uses signed, works the same
        if rate == 'scalar':
            rate = 'control'
        if isinstance(trig, (int, float)):
            selector = ocl.Impulse._method_selector_for_rate(rate)
            trig = getattr(ocl.Impulse, selector)(trig, 0)
        obj = cls._create_ugen_object(rate)
        obj._add_to_synth()
        return obj._init_ugen(trig, input, trig_id, len(label), *label)

    def _check_inputs(self):  # override
        return self._check_sr_as_first_input()

    # init_ugen, same override pattern as EnvGen, I don't get it.
