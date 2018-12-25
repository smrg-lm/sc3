"""Line.sc"""

import supercollie.ugens as ug


# SON LAS DOS ÚLTIMAS
class DC(ug.PureMultiOutUGen):
    @classmethod
    def ar(cls, input=0.0):
        return cls.multi_new('audio', input)

    @classmethod
    def kr(cls, input=0.0):
        return cls.multi_new('control', input)

    def init_ugen(self, *inputs):
        self.inputs = inputs # TODO: es tupla. En sclang es nil si no hay inputs.
        return self.init_outputs(len(inputs), self.rate)

class Silent(): # No es una UGen.
    @classmethod
    def ar(cls, num_channels=1):
        sig = DC.ar(0)
        if num_channels == 1:
            return sig
        else:
            return [sig] * num_channels
