"""Pan.sc"""

from .. import ugen as ugn


class Pan2(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, input, pos=0.0, level=1.0):
        return cls._multi_new('audio', input, pos, level)

    @classmethod
    def kr(cls, input, pos=0.0, level=1.0):
        return cls._multi_new('control', input, pos, level)

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        self._channels = ugn.ChannelList([
            ugn.OutputProxy.new(self.rate, self, 0),
            ugn.OutputProxy.new(self.rate, self, 1)
        ])
        return self._channels # NOTE: RECORDAR: las ugens retornan self en _init_ugen que es método de interfaz, pero las output ugens retornan self._channels (o _init_outputs que retorna self._channels)

    def _check_inputs(self):  # override
        return self._check_n_inputs(1)


class LinPan2(Pan2):
    pass


class Pan4(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, input, xpos=0.0, ypos=0.0, level=1.0):
        return cls._multi_new('audio', input, xpos, ypos, level)

    @classmethod
    def kr(cls, input, xpos=0.0, ypos=0.0, level=1.0):
        return cls._multi_new('control', input, xpos, ypos, level)

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        self._channels = ugn.ChannelList([
            ugn.OutputProxy.new(self.rate, self, 0),
            ugn.OutputProxy.new(self.rate, self, 1),
            ugn.OutputProxy.new(self.rate, self, 2),
            ugn.OutputProxy.new(self.rate, self, 3)
        ])
        return self._channels

    def _check_inputs(self):  # override
        return self._check_n_inputs(1)


class Balance2(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, left, right, pos=0.0, level=1.0):
        return cls._multi_new('audio', left, right, pos, level)

    @classmethod
    def kr(cls, left, right, pos=0.0, level=1.0):
        return cls._multi_new('control', left, right, pos, level)

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        self._channels = ugn.ChannelList([
            ugn.OutputProxy.new(self.rate, self, 0),
            ugn.OutputProxy.new(self.rate, self, 1)
        ])
        return self._channels

    def _check_inputs(self):  # override
        return self._check_n_inputs(2)


class Rotate2(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, x, y, pos=0.0):
        return cls._multi_new('audio', x, y, pos)

    @classmethod
    def kr(cls, x, y, pos=0.0):
        return cls._multi_new('control', x, y, pos)

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        self._channels = ugn.ChannelList([
            ugn.OutputProxy.new(self.rate, self, 0),
            ugn.OutputProxy.new(self.rate, self, 1)
        ])
        return self._channels

    def _check_inputs(self):  # override
        return self._check_n_inputs(2)


class PanB(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, input, azimuth=0, elevation=0, gain=1):
        return cls._multi_new('audio', input, azimuth, elevation, gain)

    @classmethod
    def kr(cls, input, azimuth=0, elevation=0, gain=1):
        return cls._multi_new('control', input, azimuth, elevation, gain)

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        self._channels = ugn.ChannelList([
            ugn.OutputProxy.new(self.rate, self, 0),
            ugn.OutputProxy.new(self.rate, self, 1),
            ugn.OutputProxy.new(self.rate, self, 2),
            ugn.OutputProxy.new(self.rate, self, 3)
        ])
        return self._channels

    def _check_inputs(self):  # override
        return self._check_n_inputs(1)


class PanB2(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, input, azimuth=0, gain=1):
        return cls._multi_new('audio', input, azimuth, gain)

    @classmethod
    def kr(cls, input, azimuth=0, gain=1):
        return cls._multi_new('control', input, azimuth, gain)

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        self._channels = ugn.ChannelList([
            ugn.OutputProxy.new(self.rate, self, 0),
            ugn.OutputProxy.new(self.rate, self, 1),
            ugn.OutputProxy.new(self.rate, self, 2)
        ])
        return self._channels

    def _check_inputs(self):  # override
        return self._check_n_inputs(1)


class BiPanB2(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, input_a, input_b, azimuth=0, gain=1):
        return cls._multi_new('audio', input_a, input_b, azimuth, gain)

    @classmethod
    def kr(cls, input_a, input_b, azimuth=0, gain=1):
        return cls._multi_new('control', input_a, input_b, azimuth, gain)

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        self._channels = ugn.ChannelList([
            ugn.OutputProxy.new(self.rate, self, 0),
            ugn.OutputProxy.new(self.rate, self, 1),
            ugn.OutputProxy.new(self.rate, self, 2)
        ])
        return self._channels

    def _check_inputs(self):  # override
        return self._check_n_inputs(2)


class DecodeB2(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, num_channels, w, x, y, orientation=0.5):
        return cls._multi_new('audio', num_channels, w, x, y, orientation)  # *** BUG: en sclang? asigns orientation = 0.5 here again.

    @classmethod
    def kr(cls, num_channels, w, x, y, orientation=0.5):
        return cls._multi_new('control', num_channels, w, x, y, orientation)  # *** BUG: en sclang? asigns orientation = 0.5 here again.

    def _init_ugen(self, num_channels, *inputs):  # override
        self._inputs = inputs
        self._channels = ugn.ChannelList([
            ugn.OutputProxy.new(self.rate, self, i)
            for i in range(num_channels)
        ])
        return self._channels

    def _check_inputs(self):  # override
        return self._check_n_inputs(3)


class PanAz(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, num_channels, input, pos=0.0, level=1.0,
           width=2.0, orientation=0.5):
        return cls._multi_new('audio', num_channels, input, pos, level,
                              width, orientation)

    @classmethod
    def kr(cls, num_channels, input, pos=0.0, level=1.0,
           width=2.0, orientation=0.5):
        return cls._multi_new('control', num_channels, input, pos, level,
                              width, orientation)

    def _init_ugen(self, num_channels, *inputs):  # override
        self._inputs = inputs
        self._channels = ugn.ChannelList([
            ugn.OutputProxy.new(self.rate, self, i)
            for i in range(num_channels)
        ])
        return self._channels

    def _check_inputs(self):  # override
        return self._check_n_inputs(1)


class XFade2(ugn.UGen):
    # // Equal power two channel cross fade.
    @classmethod
    def ar(cls, input_a, input_b=0.0, pan=0.0, level=1.0):
        return cls._multi_new('audio', input_a, input_b, pan, level)

    @classmethod
    def kr(cls, input_a, input_b=0.0, pan=0.0, level=1.0):
        return cls._multi_new('control', input_a, input_b, pan, level)

    def _check_inputs(self):  # override
        return self._check_n_inputs(2)


class LinXFade2(ugn.UGen):
    # // Linear two channel cross fade.
    @classmethod
    def ar(cls, input_a, input_b=0.0, pan=0.0, level=1.0):
        return cls._multi_new('audio', input_a, input_b, pan) * level

    @classmethod
    def kr(cls, input_a, input_b=0.0, pan=0.0, level=1.0):
        return cls._multi_new('control', input_a, input_b, pan) * level

    def _check_inputs(self):  # override
        return self._check_n_inputs(2)
