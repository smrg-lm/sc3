"""
Osc.sc

Oiginal Comment:
    Osc - oscillator
    arguments :
        bufnum - an index to a buffer
        freq - frequency in cycles per second
        pm - phase modulation
        mul - multiply by signal or scalar
        add - add to signal or scalar
"""

import supercollie.ugens as ug


class Osc(ug.PureUGen):
    @classmethod
    def ar(cls, bufnum, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return ug.madd(cls.multi_new('audio', bufnum, freq, phase), mul, add) # TODO: TENGO QUE VER DISEÑO DE INTERFAZ. ACÁ MULTI_NEW PUEDE DEVOLVER NÚMERO, ARRAY O UGEN.

    @classmethod
    def kr(cls, bufnum, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return ug.madd(cls.multi_new('control', bufnum, freq, phase), mul, add) # TODO: TENGO QUE VER DISEÑO DE INTERFAZ.

class SinOsc(ug.PureUGen):
    @classmethod
    def ar(cls, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return ug.madd(cls.multi_new('audio', freq, phase), mul, add) # TODO: TENGO QUE VER DISEÑO DE INTERFAZ.

    @classmethod
    def kr(cls, freq=440.0, phase=0.0, mul=1.0, add=0.0):
        return ug.madd(cls.multi_new('control', freq, phase), mul, add) # TODO: TENGO QUE VER DISEÑO DE INTERFAZ.
