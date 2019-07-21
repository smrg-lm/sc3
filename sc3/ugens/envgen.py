# EnvGen.sc

from .. import ugen as ugn

# TODO: todo...

class Linen(ugn.UGen):
    @classmethod
    def kr(cls, gate=1.0, attack_time=0.01, sus_level=1.0,
           release_time=1.0, done_action=0):
        return cls.multi_new('control', gate, attack_time, sus_level,
                             release_time, done_action)
