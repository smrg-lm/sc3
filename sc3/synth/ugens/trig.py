"""Trig.sc"""

from .. import ugen as ugn


class Trig1(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, dur=0.1):
        return cls._multi_new('audio', input, dur)

    @classmethod
    def kr(cls, input=0.0, dur=0.1):
        return cls._multi_new('control', input, dur)

    @classmethod
    def signal_range(self):
        return 'unipolar'


class Trig(Trig1):
    pass


class SendTrig(ugn.UGen):
    ...


class SendReply(SendTrig):
    ...


class TDelay(Trig1):
    ...


class Latch(ugn.UGen):
    ...


class Gate(Latch):
    pass


class PulseCount(ugn.UGen):
    ...


class Peak(ugn.UGen):
    ...


class RunningMin(Peak):
    pass


class RunningMax(Peak):
    pass


class Stepper(ugn.UGen):
    ...


class PulseDivider(ugn.UGen):
    ...


class SetResetFF(PulseCount):
    pass


class ToggleFF(ugn.UGen):
    ...


class ZeroCrossing(ugn.UGen):
    ...


class Timer(ugn.UGen):
    ...


class Sweep(ugn.UGen):
    ...


class Phasor(ugn.UGen):
    ...


class PeakFollower(ugn.UGen):
    ...


class Pitch(ugn.MultiOutUGen):
    ...


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
    ...


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
    ...


class MostChange(ugn.UGen):
    ...


class LeastChange(MostChange):
    pass


class LastValue(ugn.UGen):
    ...


class SendPeakRMS(ugn.UGen):
    ...
