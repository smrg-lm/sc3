"""TestUGens.sc"""

from .. import ugen as ugn


class CheckBadValues(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, id=0, post=2):
        return cls._multi_new('audio', input, id, post)

    @classmethod
    def kr(cls, input=0.0, id=0, post=2):
        return cls._multi_new('control', input, id, post)

    def _check_inputs(self):  # override
        if self.rate == 'audio':
            return self._check_sr_as_first_input()
        else:
            return self._check_valid_inputs()


class Sanitize(ugn.UGen):
    @classmethod
    def ar(cls, input=0.0, replace=0.0):
        return cls._multi_new('audio', input, replace)

    @classmethod
    def kr(cls, input=0.0, replace=0.0):
        return cls._multi_new('control', input, replace)

    def _check_inputs(self):  # override
        if self.rate == 'audio':
            return self._check_sr_as_first_input()
        else:
            return self._check_valid_inputs()
