"MachineListening.sc"

from .. import ugen as ugn


class RunningSum(ugn.UGen):
    # // Useful for time domain onset detection.
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


class SpecFlatness(ugn.UGen):
    _default_rate = 'control'

    @classmethod
    def kr(cls, chain):
        return cls._multi_new('control', chain)


class SpecPcile(ugn.UGen):
    _default_rate = 'control'

    @classmethod
    def kr(cls, chain, fraction=0.5, interpolate=0, binout=0):  # Added binout parameter, supercollider/supercollider#5097 v3.13.0
        return cls._multi_new('control', chain, fraction, interpolate, binout)


class SpecCentroid(ugn.UGen):
    _default_rate = 'control'

    @classmethod
    def kr(cls, chain):
        return cls._multi_new('control', chain)


class MFCC(ugn.MultiOutUGen):
    # // A bufnum could be added as third argument
    # // for passing arbitrary band spacing data.
    _default_rate = 'control'

    @classmethod
    def kr(cls, chain, numcoeff=13):
        return cls._multi_new('control', chain, numcoeff)

    def _init_ugen(self, *inputs):
        self._inputs = inputs
        return self._init_outputs(inputs[1], self.rate)


class Loudness(ugn.UGen):
    _default_rate = 'control'

    @classmethod
    def kr(cls, chain, smask=0.25, tmask=1):
        return cls._multi_new('control', chain, smask, tmask)


class Onsets(ugn.UGen):
    _default_rate = 'control'
    _ODF_TYPES = (
        'power', 'magsum', 'complex', 'rcomplex', 'phase', 'wphase', 'mkl')

    @classmethod
    def kr(cls, chain, threshold=0.5, odftype='rcomplex', relaxtime=1,
           floor=0.1, mingap=10, medianspan=11, whtype=1, rawodf=0):
        if isinstance(odftype, str):
            odftype = cls._ODF_TYPES.index(odftype)
        # // mingap of 10 frames, @ 44100 & 512 & 50%, is about 0.058 seconds.
        return cls._multi_new(
            'control', chain, threshold, odftype, relaxtime,
            floor, mingap, medianspan, whtype, rawodf)


class KeyTrack(ugn.UGen):
    # // Transient input not currently used but reserved for future
    # // use in downweighting frames which have high transient content.
    _default_rate = 'control'

    @classmethod
    def kr(cls, chain, keydecay=2.0, chromaleak=0.5): # transient=0.0):
        return cls._multi_new('control', chain, keydecay, chromaleak)  # transient=0.0)


class BeatTrack(ugn.MultiOutUGen):
    # 4 outputs.
    _default_rate = 'control'

    @classmethod
    def kr(cls, chain, lock=0):
        # if not isinstance(fft.FFT):
        #     # // Automatically drop in an FFT, possible now that we have LocalBuf.
        #     # chain = fft.FFT(LocalBuf(if(SampleRate.ir > 48000, 2048, 1024)), chain)
        return cls._multi_new('control', chain, lock)

    def _init_ugen(self, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(4, self.rate)


class BeatTrack2(ugn.MultiOutUGen):
    # 6 outputs.
    _default_rate = 'control'

    @classmethod
    def kr(cls, busindex, numfeatures, windowsize=2.0,
           paccuracy=0.02, lock=0, wscheme=None):
        wscheme = -2.1 if wscheme is None else wscheme
        return cls._multi_new(
            'control', busindex, numfeatures, windowsize,
            paccuracy, lock, wscheme)
