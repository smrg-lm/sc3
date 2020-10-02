"""MacUGens.sc"""

from .. import ugen as ugn


class MouseX(ugn.UGen):
    _default_rate = 'control'
    _WARPS = {
        'lin': 0, 'linear': 0, 0: 0,
        'exp': 1, 'exponential': 1, 1: 1}

    @classmethod
    def kr(cls, minval=0, maxval=1, warp=0, lag=0.2):
        try:
            warp = cls._WARPS[warp]
        except KeyError:
            raise ValueError(f'invalid warp {repr(warp)}') from None
        return cls._multi_new('control', minval, maxval, warp, lag)

    @classmethod
    def signal_range(cls):  # override
        return 'unipolar'


class MouseY(MouseX):
    pass


class MouseButton(ugn.UGen):
    _default_rate = 'control'

    @classmethod
    def kr(cls, minval=0, maxval=1, lag=0.2):
        return cls._multi_new('control', minval, maxval, lag)

    @classmethod
    def signal_range(cls):  # override
        return 'unipolar'


class KeyState(ugn.UGen):
    _default_rate = 'control'

    @classmethod
    def kr(cls, keycode=0, minval=0, maxval=1, lag=0.2):
        return cls._multi_new('control', keycode, minval, maxval, lag)

    @classmethod
    def signal_range(cls):  # override
        return 'unipolar'
