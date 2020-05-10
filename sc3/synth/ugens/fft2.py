"""FFT2.sc"""

from .. import ugen as ugn
from . import fftunpacking as ffu


class Convolution(ugn.UGen):
    # // input and kernel are both audio rate changing signals.
    @classmethod
    def ar(cls, input, kernel, frame_size=512):
        return cls._multi_new('audio', input, kernel, frame_size)


class Convolution2(ugn.UGen):
    # // Fixed kernel convolver with fix by nescivi to update
    # // the kernel on receipt of a trigger message.
    @classmethod
    def ar(cls, input, kernel, trigger=0, frame_size=2048):  # NOTE: wrong kernel size crashes the server.
        return cls._multi_new('audio', input, kernel, trigger, frame_size)


class Convolution2L(ugn.UGen):
    # // Fixed kernel convolver with linear crossfade.
    @classmethod
    def ar(cls, input, kernel, trigger=0, frame_size=2048, crossfade=1):
        return cls._multi_new(
            'audio', input, kernel, trigger, frame_size, int(crossfade))


class StereoConvolution2L(ugn.MultiOutUGen):
    # // Fixed kernel stereo convolver with linear crossfade.
    @classmethod
    def ar(cls, input, kernel_L, kernel_R,
           trigger=0, frame_size=2048, crossfade=1):
        return cls._multi_new(
            'audio', input, kernel_L, kernel_R,
            trigger, frame_size, int(crossfade))

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        self._channels = ugn.ChannelList(
            [ugn.OutputProxy.new(self.rate, self, 0),
             ugn.OutputProxy.new(self.rate, self, 1)])
        return self._channels


class Convolution3(ugn.UGen):
    # // Time based convolution by nescivi.
    @classmethod
    def ar(cls, input, kernel, trigger=0, frame_size=2048):
        return cls._multi_new('audio', input, kernel, trigger, frame_size)

    @classmethod
    def kr(cls, input, kernel, trigger=0, frame_size=2048):
        return cls._multi_new('control', input, kernel, trigger, frame_size)


# *** NOTE: CREAR UN ARCHIVO pvugnes.py Y PASAR ESTAS Y LAS DE FFT.sc.
# *** NOTE: TAL VEZ PASAR LAS CONVOLUCIONES A FFT O RENOMBRAR ESTE ARCHIVO
# *** NOTE: A convolution.py, FALTAN PartConv Y OTRAS DE OTROS ARCHIVOS SC.
# *** NOTE: VER QUÉ HACER CON fftunpacking.py QUE DEFINE LA CLAS BASE
# *** NOTE: PV_ChainUGen, FFT ES UN PV_ChainUGen.


class PV_ConformalMap(ffu.PV_ChainUGen):
    # // Sick Lincoln remembers complex analysis courses.
    @classmethod
    def new(cls, buf, areal=0.0, aimag=0.0):
        return cls._multi_new('control', buf, areal, aimag)


class PV_JensenAndersen(ffu.PV_ChainUGen):
    # *** Not sure why this is ar, see _add_to_synth and prefix name.
    # // Jensen andersen inspired FFT feature detector.
    @classmethod
    def ar(cls, buf, propsc=0.25, prophfe=0.25, prophfc=0.25, propsf=0.25,
           threshold=1.0, wait_time=0.04):
        return cls._multi_new('audio', buf, propsc, prophfe, prophfc,
                              propsf, threshold, wait_time)


class PV_HainsworthFoote(ffu.PV_ChainUGen):
    # *** Not sure why this is ar, _add_to_synth and prefix name.
    @classmethod
    def ar(cls, buf, proph=0.0, propf=0.0, threshold=1.0, wait_time=0.04):
        return cls._multi_new('audio', buf, proph, propf, threshold, wait_time)


class RunningSum(ugn.UGen):
    # // Not FFT but useful for time domain onset detection.
    @classmethod
    def ar(cls, input, num_samples=40):
        return cls._multi_new('audio', input, num_samples)

    @classmethod
    def kr(cls, input, num_samples=40):
        return cls._multi_new('control', input, num_samples)

    @classmethod
    def rms(cls, input, num_samples=40):
        sig = RunningSum.ar(input.squared(), num_samples)  # NOTE: si se pasa un valor erróneo a input va a tirar un error distinto al habitual.
        return (sig * (1 / num_samples)).sqrt()
