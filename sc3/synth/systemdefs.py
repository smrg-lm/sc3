"""SystemSynthdefs.sc // synthdefs needed by classes."""

from ..base import classlibrary as clb
from ..base import systemactions as sac
from . import synthdef as sdf
from . import ugens as ugns
from . import envelope as evp


__all__ = ['SystemDefs']


class MetaSystemDefs(type):
    CHANNELS = 16
    PREFIX = 'temp__'
    MAX_TMP_DEF_NAMES = 512
    _tmp_def_count = 0
    _sdefs = dict()

    def __init__(cls, *_):
        clb.ClassLibrary.add(cls, lambda _: cls._build())

    @property
    def synthdefs(cls):
        return list(cls._sdefs.values())

    def generate_tmp_name(cls):
        name = cls.PREFIX + str(cls._tmp_def_count)
        cls._tmp_def_count += 1
        cls._tmp_def_count %= cls.MAX_TMP_DEF_NAMES
        return name

    def add_synthdef(cls, name):
        sdef = cls._sdefs[name]
        sdef.add()  # Running servers or offline patterns.
        sac.ServerBoot.add('all', lambda server: sdef.add())  # Next boot.

    def add_all(cls):
        for sdef in cls._sdefs.values():
            sdef.add()  # Running servers or offline patterns.
            sac.ServerBoot.add('all', lambda server: sdef.add())  # Next boot.

    def _build(cls):
        def default(freq=220, index=2.5, fmh=1, amp=0.1, pan=0, gate=1):
            fc = freq
            fm = fc * fmh.lag()
            d = index.lag() * fm
            mod = ugns.SinOsc.ar(fm) * d
            car = ugns.SinOsc.ar(fc + mod) * amp.lag()
            res = car * ugns.EnvGen.kr(
                evp.Env.adsr(0.05, 0.1, 0.8, 0.1), gate, done_action=2)
            res = ugns.LPF.ar(res, freq * 3)
            ugns.Out.ar(0, ugns.Pan2.ar(res, pan))

        cls._sdefs['default'] = sdf.SynthDef('default', default)
        cls._sdefs['fm'] = sdf.SynthDef('fm', default)

        def test(out, amp=0.1, gate=1):
            sig = ugns.PinkNoise.ar() * amp
            env = ugns.EnvGen.kr(
                evp.Env.asr(0.01, 1, 0.01), gate, done_action=2)
            ugns.Out(out, sig * env)

        cls._sdefs['test'] = sdf.SynthDef('test', test)

        # There are other defs in not used by now.


class SystemDefs(metaclass=MetaSystemDefs):
    pass
