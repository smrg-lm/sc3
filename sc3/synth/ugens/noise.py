"""Noise.sc"""

from .. import ugen as ugn


class RandSeed(ugn.WidthFirstUGen):
    ...


class RandID(ugn.WidthFirstUGen):
    ...


class Rand(ugn.UGen):
    # // uniform distribution
    @classmethod
    def ir(cls, lo=0.0, hi=127): # NOTE: en sclang es *new, pero en esta implementación no se puede llamar a __init__ como constructor, por eso directamente pongo ir (dr, etc, nombre de contructor acertado para el rate).
        return cls._multi_new('scalar', lo, hi)


class IRand(ugn.UGen):
    ...


class TRand(ugn.UGen):
    ...


class TIRand(ugn.UGen):
    ...


class LinRand(ugn.UGen):
    ...


class NRand(ugn.UGen):
    ...


class ExpRand(ugn.UGen):
    ...


class TExpRand(ugn.UGen):
    ...


class CoinGate(ugn.UGen):
    ...


class TWindex(ugn.UGen):
    ...


class WhiteNoise(ugn.UGen):
    ...


class BrownNoise(WhiteNoise):
    pass


class PinkNoise(WhiteNoise):
    pass


class ClipNoise(WhiteNoise):
    pass


class GrayNoise(WhiteNoise):
    pass


# NoahNoise, commented ugen.


class Crackle(ugn.UGen):
    ...


class Logistic(ugn.UGen):
    ...


# Rossler, commented ugen.


class LFNoise0(ugn.UGen):
    ...


class LFNoise1(LFNoise0):
    ...


class LFNoise2(LFNoise0):
    ...


class LFClipNoise(LFNoise0):
    ...


class LFDNoise0(LFNoise0):
    ...


class LFDNoise1(LFNoise0):
    ...


class LFDNoise3(LFNoise0):
    ...


class LFDClipNoise(LFNoise0):
    ...


class Hasher(ugn.UGen):
    ...


class MantissaMask(ugn.UGen):
    ...


class Dust(ugn.UGen):
    ...


class Dust2(ugn.UGen):
    ...
