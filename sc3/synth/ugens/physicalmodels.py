
from .. import ugen as ugn


class Spring(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, spring=1, damp=0):
        return cls._multi_new('audio', input, spring, damp)

    @classmethod
    def kr(cls, input=0.0, spring=1, damp=0):
        return cls._multi_new('control', input, spring, damp)


# class Friction(ugn.UGen):
#     @classmethod
#     def ar(cls, input=0.0, spring=1, thresh=0.5):
#         return cls._multi_new('audio', input, spring, thresh)


class Ball(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, g=1, damp=0, friction=0.01):
        return cls._multi_new('audio', input, g, damp, friction)

    @classmethod
    def kr(cls, input=0.0, g=1, damp=0, friction=0.01):
        return cls._multi_new('control', input, g, damp, friction)


class TBall(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, g=1, damp=0, friction=0.01):
        return cls._multi_new('audio', input, g, damp, friction)

    @classmethod
    def kr(cls, input=0.0, g=1, damp=0, friction=0.01):
        return cls._multi_new('control', input, g, damp, friction)
