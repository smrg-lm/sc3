"""Filter.sc"""

from . import ugens as ugn


class Filter(ugn.PureUGen):
    def check_inputs(self):
        return self.check_sr_as_first_input() # NOTE: le cambié el nombre de check_sample_rate_as_first_input por extensas razones


# TODO: muchas, muchas...


class LPF(Filter):
    @classmethod
    def ar(cls, input=0.0, freq=440.0, mul=1.0, add=0.0):
        return cls.multi_new('audio', input, freq).madd(mul, add)

    @classmethod
    def kr(cls, input=0.0, freq=440.0, mul=1.0, add=0.0):
        return cls.multi_new('control', input, freq).madd(mul, add)


# TODO: otras tantas...
