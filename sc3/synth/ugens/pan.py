"""Pan.sc"""

from ...base import builtins as bi
from ...base import utils as utl
from .. import ugen as ugn
from . import mix


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
        return self._channels

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
    def ar(cls, channels, w, x, y, orientation=0.5):
        return cls._multi_new('audio', channels, w, x, y, orientation)  # *** BUG: en sclang? asigns orientation = 0.5 here again.

    @classmethod
    def kr(cls, channels, w, x, y, orientation=0.5):
        return cls._multi_new('control', channels, w, x, y, orientation)  # *** BUG: en sclang? asigns orientation = 0.5 here again.

    def _init_ugen(self, channels, *inputs):  # override
        self._inputs = inputs
        self._channels = ugn.ChannelList([
            ugn.OutputProxy.new(self.rate, self, i)
            for i in range(channels)
        ])
        return self._channels

    def _check_inputs(self):  # override
        return self._check_n_inputs(3)


class PanAz(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, channels, input, pos=0.0, level=1.0,
           width=2.0, orientation=0.5):
        return cls._multi_new(
            'audio', channels, input, pos, level, width, orientation)

    @classmethod
    def kr(cls, channels, input, pos=0.0, level=1.0,
           width=2.0, orientation=0.5):
        return cls._multi_new(
            'control', channels, input, pos, level, width, orientation)

    def _init_ugen(self, channels, *inputs):  # override
        self._inputs = inputs
        self._channels = ugn.ChannelList([
            ugn.OutputProxy.new(self.rate, self, i)
            for i in range(channels)
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


class Splay(ugn.PseudoUGen):
    @classmethod
    def ar(cls, inputs, spread=1, level=1, center=0.0, level_comp=True):
        return cls._multi_new(
            'audio', spread, level, center, level_comp, *inputs)

    @classmethod
    def kr(cls, inputs, spread=1, level=1, center=0.0, level_comp=True):
        return cls._multi_new(
            'control', spread, level, center, level_comp, *inputs)

    @classmethod
    def _new1(cls, rate, spread=1, level=1, center=0.0,
              level_comp=True, *inputs):  # override
        n = max(2, len(inputs))
        n2n1 = 2 / (n - 1)
        positions = [(i * n2n1 - 1) * spread + center for i in range(n)]
        if level_comp:
            if rate == 'audio':
                level *= bi.sqrt(1 / n)
            else:
                level /= n
        selector = Pan2._method_selector_for_rate(rate)
        pan = getattr(Pan2, selector)(list(inputs), positions)
        return mix.Mix(pan) * level

    # @classmethod
    # def ar_fill(cls, n, func, spread=1, level=1, center=0.0, level_comp=True):
    #     return cls.ar(
    #         [fn.value(func, i) for i in range(n)],
    #         spread, level, center, level_comp)


class SplayAz(ugn.PseudoUGen):
    @classmethod
    def ar(cls, channels, inputs, spread=1, level=1, width=2,
           center=0.0, orientation=0.5, level_comp=True):
        pos, level = cls._calc_poslevel(
            inputs, spread, level, center, level_comp)
        aux = PanAz.ar(channels, inputs, pos, level, width, orientation)
        return ugn.ChannelList([mix.Mix.ar(x) for x in utl.flop(aux)])

    @classmethod
    def kr(cls, channels, inputs, spread=1, level=1, width=2,
           center=0.0, orientation=0.5, level_comp=True):
        pos, level = cls._calc_poslevel(
            inputs, spread, level, center, level_comp)
        aux = PanAz.kr(channels, inputs, pos, level, width, orientation)
        return ugn.ChannelList([mix.Mix.kr(x) for x in utl.flop(aux)])

    @staticmethod
    def _calc_poslevel(inputs, spread, level, center, level_comp):
        n = max(1, len(inputs))
        pos = center if n == 1 else bi.resamp1(
            [center - spread, center + spread], n)
        if level_comp: level *= bi.sqrt(1 / n)
        return pos, level

    # @classmethod
    # def ar_fill(cls, channels, n, func, spread=1, level=1, width=2,
    #             center=0.0, orientation=0.5, level_comp=True):
    #     return cls.ar(
    #         channels, [fn.value(func, i) for i in range(n)],
    #         spread, level, width, center, orientation, level_comp)
