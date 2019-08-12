"""Osc.sc"""

from .. import ugen as ugn


class Osc(ugn.PureUGen):
    @classmethod
    def ar(cls, bufnum, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', bufnum, freq, phase).madd(mul, add)

    @classmethod
    def kr(cls, bufnum, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('control', bufnum, freq, phase).madd(mul, add)


class SinOsc(ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', freq, phase).madd(mul, add)

    @classmethod
    def kr(cls, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('control', freq, phase).madd(mul, add)


# TODO: ...


class Impulse(ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', freq, phase).madd(mul, add)

    @classmethod
    def kr(cls, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('control', freq, phase).madd(mul, add)

    def signal_range(self):
        return 'unipolar'


# TODO: ...


class VarSaw(ugn.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, iphase=0.0, width=0.5, mul=1.0, add=0.0):
        return cls._multi_new('audio', freq, iphase, width).madd(mul, add)

    @classmethod
    def kr(cls, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return cls._multi_new('audio', freq, iphase, width).madd(mul, add)


# TODO: muchas más...
