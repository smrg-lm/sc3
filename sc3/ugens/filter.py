"""Filter.sc"""

from .. import ugen as ugn


class Filter(ugn.PureUGen):
    def _check_inputs(self):  # override
        return self._check_sr_as_first_input()


# TODO: muchas, muchas...


class LPF(Filter):
    @classmethod
    def ar(cls, input=0.0, freq=440.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', input, freq).madd(mul, add)

    @classmethod
    def kr(cls, input=0.0, freq=440.0, mul=1.0, add=0.0):
        return cls._multi_new('control', input, freq).madd(mul, add)


# TODO: otras tantas...
