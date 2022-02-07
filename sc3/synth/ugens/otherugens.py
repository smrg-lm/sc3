
from .. import ugen as ugn


class PitchShift(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, window_size=0.2, pitch_ratio=1.0,
           pitch_dispersion=0.0, time_dispersion=0.0):
        return cls._multi_new(
            'audio', input, window_size, pitch_ratio,
            pitch_dispersion, time_dispersion)

    def _check_inputs(self):  # override
        return self._check_sr_as_first_input()


class Pluck(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, trig=1.0, max_delay=0.2,
           delay_time=0.2, decay_time=1.0, coef=0.5):
        return cls._multi_new(
            'audio', input, trig, max_delay,
            delay_time, decay_time, coef)


class PSinGrain(ugn.UGen):
    # PSinGrain - fixed frequency sine oscillator
    # arguments:
    #     freq - frequency in cycles per second. Must be a scalar.
    #     dur - grain duration
    #     amp - amplitude of grain
    # This unit generator uses a very fast algorithm for generating a sine
    # wave at a fixed frequency.
    @classmethod
    def ar(cls, freq=440, dur=0.2, amp=0.1):
        return cls._multi_new('audio', freq, dur, amp)
