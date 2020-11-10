"""Trig.sc"""

from .. import ugen as ugn
from .. import _graphparam as gpp
from ...base import utils as utl


class Trig1(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, dur=0.1):
        return cls._multi_new('audio', input, dur)

    @classmethod
    def kr(cls, input=0.0, dur=0.1):
        return cls._multi_new('control', input, dur)

    @classmethod
    def signal_range(cls):  # override
        return 'unipolar'


class Trig(Trig1):
    pass


class SendTrig(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, id=0, value=0.0):
        cls._multi_new('audio', input, id, value)
        # return 0.0  # // SendTrig has no output.

    @classmethod
    def kr(cls, input=0.0, id=0, value=0.0):
        cls._multi_new('control', input, id, value)
        # return 0.0  # // SendTrig has no output.

    def _check_inputs(self):  # override
        return self._check_sr_as_first_input()

    def _num_outputs(self):  # override
        return 0

    def _write_output_specs(self, file):  # override
        pass


class SendReply(SendTrig):
    @classmethod
    def ar(cls, trig=0.0, cmd_name='/reply', values=(), reply_id=-1):
        # *** NOTE: values must be a tuple, use a list of tuples for multichannel expansion. Can't be a single value.
        for args in utl.flop([trig, cmd_name, values, reply_id]):
            cls._new1('audio', *args)
        # return 0.0  # // SendReply has no output.

    @classmethod
    def kr(cls, trig=0.0, cmd_name='/reply', values=(), reply_id=-1):
        # *** NOTE: values must be a tuple, use a list of tuples for multichannel expansion. Can't be a single value.
        for args in utl.flop([trig, cmd_name, values, reply_id]):
            cls._new1('control', *args)
        # return 0.0  # // SendReply has no output.

    @classmethod
    def _new1(cls, rate, trig=0.0, cmd_name='/reply', values=None, reply_id=-1):
        cmd_name = [int(x) for x in bytes(cmd_name, 'utf-8')]  # *** TODO: sc ascii method, sclang uses signed vlaues, see Poll.
        return super()._new1(rate, trig, reply_id, len(cmd_name), *cmd_name,
                             *values)


class TDelay(Trig1):
    def _check_inputs(self):  # override
        return self._check_sr_as_first_input()


class Latch(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, trig=0.0):
        return cls._muli_new('audio', input, trig)

    @classmethod
    def kr(cls, input=0.0, trig=0.0):
        return cls._muli_new('control', input, trig)


class Gate(Latch):
    pass


class PulseCount(ugn.UGen):
    @classmethod
    def ar(cls, trig=0.0, reset=0.0):
        return cls._multi_new('audio', trig, reset)

    @classmethod
    def kr(cls, trig=0.0, reset=0.0):
        return cls._multi_new('control', trig, reset)

    def _check_inputs(self):  # override
        return self._check_sr_as_first_input()


class Peak(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, trig=0.0):
        return cls._muli_new('audio', input, trig)

    @classmethod
    def kr(cls, input=0.0, trig=0.0):
        return cls._muli_new('control', input, trig)

    def _check_inputs(self):  # override
        if self.rate == 'control'\
        and gpp.ugen_param(self.inputs[0])._as_ugen_rate() == 'audio':
            return self._check_valid_inputs()
        else:
            return self._check_sr_as_first_input()


class RunningMin(Peak):
    pass


class RunningMax(Peak):
    pass


class Stepper(ugn.UGen):
    @classmethod
    def ar(cls, trig=0, reset=0, min=0, max=7, step=1, resetval=None):
        if resetval is None:
            resetval = min
        return cls._multi_new('audio', trig, reset, min, max, step, resetval)

    @classmethod
    def kr(cls, trig=0, reset=0, min=0, max=7, step=1, resetval=None):
        if resetval is None:
            resetval = min
        return cls._multi_new('control', trig, reset, min, max, step, resetval)

    def _check_inputs(self):  # override
        return self._check_sr_as_first_input()


class PulseDivider(ugn.UGen):
    @classmethod
    def ar(cls, trig=0.0, div=2.0, start=0.0):
        return cls._multi_new('audio', trig, div, start)

    @classmethod
    def kr(cls, trig=0.0, div=2.0, start=0.0):
        return cls._multi_new('control', trig, div, start)


class SetResetFF(PulseCount):
    pass


class ToggleFF(ugn.UGen):
    @classmethod
    def ar(cls, trig=0.0):
        return cls._multi_new('audio', trig)

    @classmethod
    def kr(cls, trig=0.0):
        return cls._multi_new('control', trig)


class ZeroCrossing(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0):
        return cls._multi_new('audio', input)

    @classmethod
    def kr(cls, input=0.0):
        return cls._multi_new('control', input)

    def _check_inputs(self):  # override
        return self._check_sr_as_first_input()


class Timer(ugn.UGen):
    # // Output is the time between two triggers.
    @classmethod
    def ar(cls, trig=0.0):
        return cls._multi_new('audio', trig)

    @classmethod
    def kr(cls, trig=0.0):
        return cls._multi_new('control', trig)

    def _check_inputs(self):  # override
        return self._check_sr_as_first_input()


class Sweep(ugn.UGen):
    # // Output sweeps up in value at rate per
    # // second the trigger resets to zero.
    @classmethod
    def ar(cls, trig=0.0, rate=1.0):
        return cls._multi_new('audio', trig, rate)

    @classmethod
    def kr(cls, trig=0.0, rate=1.0):
        return cls._multi_new('control', trig, rate)


class Phasor(ugn.UGen):
    @classmethod
    def ar(cls, trig=0.0, rate=1.0, start=0.0, end=1.0, reset_pos=0.0):
        return cls._multi_new('audio', trig, rate, start, end, reset_pos)

    @classmethod
    def kr(cls, trig=0.0, rate=1.0, start=0.0, end=1.0, reset_pos=0.0):
        return cls._multi_new('control', trig, rate, start, end, reset_pos)


class PeakFollower(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, decay=0.999):
        return cls._multi_new('audio', input, decay)

    @classmethod
    def kr(cls, input=0.0, rate=0.999):
        return cls._multi_new('control', input, decay)


class Pitch(ugn.MultiOutUGen):
    _default_rate = 'control'

    @classmethod
    def kr(cls, input=0.0, init_freq=440.0, min_freq=60.0, max_freq=4000.0,
           exec_freq=100.0, max_bins_per_octave=16, median=1,
           amp_threshold=0.01, peak_threshold=0.5, down_sample=1, clar=0):
        return cls._multi_new('control', input, init_freq, min_freq, max_freq,
                              exec_freq, max_bins_per_octave, median,
                              amp_threshold, peak_threshold, down_sample, clar)

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(2, self.rate)


class InRange(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, lo=0.0, hi=1.0):
        return cls._multi_new('audio', input, lo, hi)

    @classmethod
    def kr(cls, input=0.0, lo=0.0, hi=1.0):
        return cls._multi_new('control', input, lo, hi)

    @classmethod
    def ir(cls, input=0.0, lo=0.0, hi=1.0):
        return cls._multi_new('scalar', input, lo, hi)


class InRect(ugn.UGen):
    @classmethod
    def ar(cls, x=0.0, y=0.0, rect=(0.0, 0.0, 0.0, 0.0)):  # left, top, right, bottom (x, y, x, y lines on screen)
        return cls._multi_new('audio', x, y, *rect)

    @classmethod
    def kr(cls, x=0.0, y=0.0, rect=(0.0, 0.0, 0.0, 0.0)):  # left, top, right, bottom (x, y, x, y lines on screen)
        return cls._multi_new('control', x, y, *rect)


# Trapezoid, commented UGen.


class Fold(InRange):
    pass


class Clip(InRange):
    pass


class Wrap(InRange):
    pass


class Schmidt(InRange):
    pass


class ModDif(ugn.UGen):
    @classmethod
    def ar(cls, x=0.0, y=0.0, mod=1.0):
        return cls._multi_new('audio', x, y, mod)

    @classmethod
    def kr(cls, x=0.0, y=0.0, mod=1.0):
        return cls._multi_new('control', x, y, mod)

    @classmethod
    def ir(cls, x=0.0, y=0.0, mod=1.0):
        return cls._multi_new('scalar', x, y, mod)


class MostChange(ugn.UGen):
    @classmethod
    def ar(cls, a=0.0, b=0.0):
        return cls._multi_new('audio', a, b)

    @classmethod
    def kr(cls, a=0.0, b=0.0):
        return cls._multi_new('control', a, b)


class LeastChange(MostChange):
    pass


class LastValue(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, diff=0.01):
        return cls._multi_new('audio', input, diff)

    @classmethod
    def kr(cls, input=0.0, diff=0.01):
        return cls._multi_new('control', input, diff)


class SendPeakRMS(ugn.UGen):
    @classmethod
    def ar(cls, sig, reply_rate=20.0, peak_lag=3, cmd_name='/reply',
           reply_id=-1):
        return cls._new1('audio', utl.as_list(sig), reply_rate, peak_lag,
                         cmd_name, reply_id)

    @classmethod
    def kr(cls, sig, reply_rate=20.0, peak_lag=3, cmd_name='/reply',
           reply_id=-1):
        return cls._new1('control', utl.as_list(sig), reply_rate, peak_lag,
                         cmd_name, reply_id)

    @classmethod
    def _new1(cls, rate, sig, reply_rate, peak_lag, cmd_name, reply_id):
        cmd_name = [int(x) for x in bytes(cmd_name, 'utf-8')]  # *** TODO: sc ascii method, sclang uses signed vlaues, see Poll.
        return super()._new1(rate, reply_rate, peak_lag, reply_id, len(sig),
                             *utl.flatten(sig), len(cmd_name), *cmd_name)

    def _num_outputs(self):  # override
        return 0

    def _write_output_specs(self, file):  # override
        pass
