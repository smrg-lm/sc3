"""Noise.sc"""

import supercollie.ugens as ugn


# TODO: varias...


class Rand(ugn.UGen):
    # // uniform distribution
    @classmethod
    def ir(cls, lo=0.0, hi=127): # NOTE: en sclang es *new, pero en esta implementación no se puede llamar a __init__ como constructor, por eso directamente pongo ir (dr, etc, nombre de contructor acertado para el rate).
        return cls.multi_new('scalar', lo, hi)


# TODO: muchas...
