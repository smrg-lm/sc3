"MachineListening.sc"

from .. import ugen as ugn


class RunningSum(ugn.UGen):
    # // Useful for time domain onset detection.
    @classmethod
    def ar(cls, input, num_samples=40):
        return cls._multi_new('audio', input, num_samples)

    @classmethod
    def kr(cls, input, num_samples=40):
        return cls._multi_new('control', input, num_samples)

    @classmethod
    def rms(cls, input, num_samples=40):
        sig = RunningSum.ar(input.squared(), num_samples)  # NOTE: si se pasa un valor erróneo a input va a tirar un error distinto al habitual.
        return (sig * (1 / num_samples)).sqrt()

...
