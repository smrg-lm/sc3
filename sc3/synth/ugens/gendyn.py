# GENDYN by Iannis Xenakis implemented for SC3
# by sicklincoln with some refinements.

from .. import ugen as ugn


class Gendy1(ugn.UGen):
    @classmethod
    def ar(cls, ampdist=1, durdist=1, adparam=1.0, ddparam=1.0, minfreq=440,
           maxfreq=660, ampscale=0.5, durscale=0.5, initcps=12, knum=None):
        knum = initcps if knum is None else knum
        return cls._multi_new(
            'audio', ampdist, durdist, adparam, ddparam, minfreq,
            maxfreq, ampscale, durscale, initcps, knum)

    @classmethod
    def kr(cls, ampdist=1, durdist=1, adparam=1.0, ddparam=1.0, minfreq=440,
           maxfreq=660, ampscale=0.5, durscale=0.5, initcps=12, knum=None):
        knum = initcps if knum is None else knum
        return cls._multi_new(
            'control', ampdist, durdist, adparam, ddparam, minfreq,
            maxfreq, ampscale, durscale, initcps, knum)


class Gendy2(ugn.UGen):
    @classmethod
    def ar(cls, ampdist=1, durdist=1, adparam=1.0, ddparam=1.0, minfreq=440,
           maxfreq=660, ampscale=0.5, durscale=0.5, initcps=12, knum=None,
           a=1.17, c=0.31):
        knum = initcps if knum is None else knum
        return cls._multi_new(
            'audio', ampdist, durdist, adparam, ddparam, minfreq,
            maxfreq, ampscale, durscale, initcps, knum, a, c)

    @classmethod
    def kr(cls, ampdist=1, durdist=1, adparam=1.0, ddparam=1.0, minfreq=440,
           maxfreq=660, ampscale=0.5, durscale=0.5, initcps=12, knum=None,
           a=1.17, c=0.31):
        knum = initcps if knum is None else knum
        return cls._multi_new(
            'control', ampdist, durdist, adparam, ddparam, minfreq,
            maxfreq, ampscale, durscale, initcps, knum, a, c)


class Gendy3(ugn.UGen):
    @classmethod
    def ar(cls, ampdist=1, durdist=1, adparam=1.0, ddparam=1.0, freq=440,
           ampscale=0.5, durscale=0.5, initcps=12, knum=None):
        knum = initcps if knum is None else knum
        return cls._multi_new(
            'audio', ampdist, durdist, adparam, ddparam,
            freq, ampscale, durscale, initcps, knum)

    @classmethod
    def kr(cls, ampdist=1, durdist=1, adparam=1.0, ddparam=1.0, freq=440,
           ampscale=0.5, durscale=0.5, initcps=12, knum=None):
        knum = initcps if knum is None else knum
        return cls._multi_new(
            'control', ampdist, durdist, adparam, ddparam,
            freq, ampscale, durscale, initcps, knum)
