"""Line.sc"""

from .. import ugen as ugn


class Line(ugn.UGen):
    @classmethod
    def ar(cls, start=0.0, end=1.0, dur=1.0, mul=1.0, add=0.0, done_action=0):
        return cls._multi_new('audio', start, end, dur, done_action).madd(mul, add)

    @classmethod
    def kr(cls, start=0.0, end=1.0, dur=1.0, mul=1.0, add=0.0, done_action=0):
        return cls._multi_new('control', start, end, dur, done_action).madd(mul, add)


class XLine(ugn.UGen):
    @classmethod
    def ar(cls, start=1.0, end=2.0, dur=1.0, mul=1.0, add=0.0, done_action=0):
        return cls._multi_new('audio', start, end, dur, done_action).madd(mul, add)

    @classmethod
    def kr(cls, start=1.0, end=2.0, dur=1.0, mul=1.0, add=0.0, done_action=0):
        return cls._multi_new('control', start, end, dur, done_action).madd(mul, add)


# TODO: muchas...


# SON LAS DOS ÚLTIMAS
class DC(ugn.PureMultiOutUGen):
    @classmethod
    def ar(cls, input=0.0):
        return cls._multi_new('audio', input)

    @classmethod
    def kr(cls, input=0.0):
        return cls._multi_new('control', input)

    def _init_ugen(self, *inputs):
        self.inputs = inputs # TODO: es tupla. En sclang es nil si no hay inputs.
        return self._init_outputs(len(inputs), self.rate)


class Silent(): # No es una UGen.
    @classmethod
    def ar(cls, num_channels=1):
        sig = DC.ar(0)
        if num_channels == 1:
            return sig
        else:
            return [sig] * num_channels
