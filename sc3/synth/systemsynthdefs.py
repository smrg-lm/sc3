"""SystemSynthdefs.sc // synthdefs needed by classes."""

from . import synthdef as sdf
from . import ugens as ugns
from . import env


CHANNELS = 16
PREFIX = 'temp__'
MAX_TMP_DEF_NAMES = 512
_tmp_def_count = 0


def generate_tmp_name(cls):
    name = PREFIX + _tmp_def_count
    _tmp_def_count += 1
    _tmp_def_count %= MAX_TMP_DEF_NAMES
    return name


def add_system_synthdefs():
    @sdf.synthdef
    def default(freq=220, index=2, fmh=2, amp=0.1, pan=0, gate=1):
        fc = freq
        fm = fc * fmh.lag()
        d = index.lag() * fm
        mod = ugns.SinOsc.ar(fm) * d
        car = ugns.SinOsc.ar(fc + mod) * amp.lag()
        res = car * ugns.EnvGen.kr(
            env.Env.adsr(0.05, 0.1, 0.8, 0.1), gate, done_action=2)
        res = ugns.LPF.ar(res, freq * 3)
        ugns.Out.ar(0, ugns.Pan2.ar(res, pan))

    # There are other defs in not used by now.
