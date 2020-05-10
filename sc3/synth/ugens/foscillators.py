"""FSinOsc.sc"""

import operator

from ...base import utils as utl
from .. import ugen as ugn
from . import oscillators as ocl
from . import filter as flt


class FSinOsc(ugn.UGen):
    '''
    Fixed frequency sine oscillator.

    This unit generator uses a very fast algorithm for generating a sine wave
    at a fixed frequency.

    Args:
        freq - Frequency in cycles per second. Must be a scalar.
        iphase - Initial phase.
    '''
    @classmethod
    def ar(cls, freq=440, iphase=0.0):
        return cls._multi_new('audio', freq, iphase)

    @classmethod
    def kr(cls, freq=440, iphase=0.0):
        return cls._multi_new('control', freq, iphase)


class Klang(ugn.UGen):
    @classmethod
    def ar(cls, spec, freq_scale=1.0, freq_offset=0.0):
        spec = utl.multichannel_expand_tuple(spec, 2)
        return cls._multi_new('audio', freq_scale, freq_offset, spec)

    @classmethod
    def _new1(cls, rate, freq_scale, freq_offset, spec):  # override
        freqs, amps, phases = spec
        size = len(freqs)
        if amps is None:
            amps = [1.0] * size
        if phases is None:
            phases = [0.0] * size
        spec = [freqs, amps, phases]
        spec = utl.flat(utl.flop(spec))
        obj = cls._create_ugen_object(rate)
        obj._add_to_synth()
        return obj._init_ugen(freq_scale, freq_offset, *spec)

    # No needed.
    # def _init_ugen(self, inputs)  # override

    def _arg_names_inputs_offset(self):  # override
        return 1  # One less than sclang.


class DynKlang(ugn.PseudoUGen):
    @classmethod
    def ar(cls, spec, freq_scale=1.0, freq_offset=0.0):
        return cls._multi_new('audio', spec, freq_scale, freq_offset)

    @classmethod
    def kr(cls, spec, freq_scale=1.0, freq_offset=0.0):
        return cls._multi_new('control', spec, freq_scale, freq_offset)

    @classmethod
    def _new1(cls, rate, spec, freq_scale, freq_offset):  # override
        if spec[0] is None:
            freq = utl.list_binop(operator.mul, [440.0], freq_scale)
            freq = utl.list_binop(operator.add, freq, freq_offset)
        else:
            freq = spec[0]
        if spec[2] is None:
            phase = [0.0]
        else:
            phase = spec[2]
        if spec[1] is None:
            mul = [1.0]
        else:
            mul = spec[1]
        selector = cls._method_selector_for_rate(rate)
        sig = getattr(ocl.SinOsc, selector)(freq, phase) * mul
        return sig.sum()


class Klank(ugn.UGen):
    @classmethod
    def ar(cls, spec, input, freq_scale=1.0, freq_offset=0.0, decay_scale=1.0):
        spec = utl.multichannel_expand_tuple(spec, 2)
        return cls._multi_new(
            'audio', input, freq_scale, freq_offset, decay_scale, spec)

    @classmethod
    def _new1(cls, rate, input, freq_scale, freq_offset,
              decay_scale, spec):  # override
        freqs, amps, times = spec
        size = len(freqs)
        if amps is None:
            amps = [1.0] * size
        if times is None:
            times = [1.0] * size
        spec = [freqs, amps, times]
        spec = utl.flat(utl.flop(spec))
        obj = cls._create_ugen_object(rate)
        obj._add_to_synth()
        return obj._init_ugen(
            input, freq_scale, freq_offset, decay_scale, *spec)

    # No needed.
    # def _init_ugen(self, inputs)  # override

    def _arg_names_inputs_offset(self):  # override
        return 1  # One less than sclang.


class DynKlank(ugn.PseudoUGen):
    @classmethod
    def ar(cls, spec, input, freq_scale=1.0, freq_offset=0.0, decay_scale=1.0):
        return cls._multi_new('audio', spec, input, freq_scale,
                              freq_offset, decay_scale)

    @classmethod
    def kr(cls, spec, input, freq_scale=1.0, freq_offset=0.0, decay_scale=1.0):
        return cls._multi_new('control', spec, input, freq_scale,
                              freq_offset, decay_scale)

    @classmethod
    def _new1(cls, rate, spec, input, freq_scale,
              freq_offset, decay_scale):  # override
        if spec[0] is None:
            freq = utl.list_binop(operator.mul, [440.0], freq_scale)
            freq = utl.list_binop(operator.add, freq, freq_offset)
        else:
            freq = spec[0]
        if spec[2] is None:
            decay_time = utl.list_binop(operator.mul, [1.0], decay_scale)
        else:
            decay_time = spec[2]
        if spec[1] is None:
            mul = [1.0]
        else:
            mul = spec[1]
        selector = cls._method_selector_for_rate(rate)
        sig = getattr(flt.Ringz, selector)(input, freq, decay_time) * mul
        return sig.sum()


class Blip(ugn.UGen):
    @classmethod
    def ar(cls, freq=440, numharm=200.0):
        return cls._multi_new('audio', freq, numharm)

    @classmethod
    def kr(cls, freq=440, numharm=200.0):
        return cls._multi_new('control', freq, numharm)


class Saw(ugn.UGen):
    @classmethod
    def ar(cls, freq=440):
        return cls._multi_new('audio', freq)

    @classmethod
    def kr(cls, freq=440):
        return cls._multi_new('control', freq)


class Pulse(ugn.UGen):
    @classmethod
    def ar(cls, freq=440, width=0.5):
        return cls._multi_new('audio', freq, width)

    @classmethod
    def kr(cls, freq=440, width=0.5):
        return cls._multi_new('control', freq, width)
