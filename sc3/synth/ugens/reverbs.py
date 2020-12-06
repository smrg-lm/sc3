"""GVerb.sc & FreeVerb.sc"""

from .. import ugen as ugn


class GVerb(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, input, roomsize=10, revtime=3, damping=0.5, inputbw=0.5,
           spread=15, drylevel=1, earlyreflevel=0.7, taillevel=0.5,
           maxroomsize=300):
        return cls._multi_new(
            'audio', input, roomsize, revtime, damping, inputbw, spread,
            drylevel, earlyreflevel, taillevel, maxroomsize)

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(2, self.rate)

    def _check_inputs(self):  # override
        return self._check_n_inputs(1)


class FreeVerb(ugn.PureUGenMixin, ugn.UGen):
    @classmethod
    def ar(cls, input, mix=0.33, room=0.5, damp=0.5):
        return cls._multi_new('audio', input, mix, room, damp)

    def _check_inputs(self):  # override
        return self._check_sr_as_first_input()


class FreeVerb2(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, in0, in1, mix=0.33, room=0.5, damp=0.5):
        return cls._multi_new('audio', in0, in1, mix, room, damp)

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        self._channels = ugn.ChannelList([
            ugn.OutputProxy.new(self.rate, self, 0),
            ugn.OutputProxy.new(self.rate, self, 1)
        ])
        return self._channels

    def _check_inputs(self):  # override
        return self._check_n_inputs(2)
