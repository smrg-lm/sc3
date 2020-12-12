"""BEQSuite.sc"""

from ...base import builtins as bi
from .. import ugen as ugn
from . import filter as flt
from . import infougens as ifu


class BEQSuite(flt.Filter):
    pass


class BLowPass(BEQSuite):
    @classmethod
    def ar(cls, input, freq=1200.0, rq=1.0):
        return cls._multi_new('audio', input, freq, rq)

    @classmethod
    def sc(cls, dummy=None, freq=1200.0, rq=1.0):
        sr = ifu.SampleRate.ir()
        w0 = bi.pi * 2 * freq * ifu.SampleDur.ir()
        cos_w0 = bi.cos(w0)
        i = 1 - cos_w0
        alpha = bi.sin(w0) * 0.5 * rq
        b0rz = bi.reciprocal(1 + alpha)
        a0 = i * 0.5 * b0rz
        a1 = i * b0rz
        b1 = cos_w0 * 2 * b0rz
        b2 = (1 - alpha) * -b0rz
        return [a0, a1, a0, b1, b2]


class BHiPass(BEQSuite):
    @classmethod
    def ar(cls, input, freq=1200.0, rq=1.0):
        return cls._multi_new('audio', input, freq, rq)

    @classmethod
    def sc(cls, dummy=None, freq=1200.0, rq=1.0):
        sr = ifu.SampleRate.ir()
        w0 = bi.pi * 2 * freq * ifu.SampleDur.ir()
        cos_w0 = bi.cos(w0)
        i = 1 + cos_w0
        alpha = bi.sin(w0) * 0.5 * rq
        b0rz = bi.reciprocal(1 + alpha)
        a0 = i * 0.5 * b0rz
        a1 = -i * b0rz
        b1 = cos_w0 * 2 * b0rz
        b2 = (1 - alpha) * -b0rz
        return [a0, a1, a0, b1, b2]


class BAllPass(BEQSuite):
    @classmethod
    def ar(cls, input, freq=1200.0, rq=1.0):
        return cls._multi_new('audio', input, freq, rq)

    @classmethod
    def sc(cls, dummy=None, freq=1200.0, rq=1.0):
        sr = ifu.SampleRate.ir()
        w0 = bi.pi * 2 * freq * ifu.SampleDur.ir()
        alpha = bi.sin(w0) * 0.5 * rq
        b0rz = bi.reciprocal(1 + alpha)
        a0 = (1 - alpha) * b0rz
        b1 = 2.0 * bi.cos(w0) * b0rz
        return [a0, -b1, 1.0, b1, -a0]


class BBandPass(BEQSuite):
    @classmethod
    def ar(cls, input, freq=1200.0, bw=1.0):
        return cls._multi_new('audio', input, freq, bw)

    @classmethod
    def sc(cls, dummy=None, freq=1200.0, bw=1.0):
        sr = ifu.SampleRate.ir()
        w0 = bi.pi * 2 * freq * ifu.SampleDur.ir()
        sin_w0 = bi.sin(w0)
        # // alpha = bi.sin(w0) * 0.5 * rq
        alpha = sin_w0 * bi.sinh(0.34657359027997 * bw * w0 / sin_w0)
        b0rz = bi.reciprocal(1 + alpha)
        a0 = alpha * b0rz
        b1 = bi.cos(w0) * 2 * b0rz
        b2 = (1 - alpha) * -b0rz
        return [a0, 0.0, -a0, b1, b2]


class BBandStop(BEQSuite):
    @classmethod
    def ar(cls, input, freq=1200.0, bw=1.0):
        return cls._multi_new('audio', input, freq, bw)

    @classmethod
    def sc(cls, dummy=None, freq=1200.0, bw=1.0):
        sr = ifu.SampleRate.ir()
        w0 = bi.pi * 2 * freq * ifu.SampleDur.ir()
        sin_w0 = bi.sin(w0)
        # // alpha = w0.sin * 0.5 * rq;
        alpha = sin_w0 * bi.sinh(0.34657359027997 * bw * w0 / sin_w0);
        b0rz = bi.reciprocal(1 + alpha)
        b1 = 2.0 * bi.cos(w0) * b0rz;
        b2 = (1 - alpha) * -b0rz
        return [b0rz, -b1, b0rz, b1, b2]


class BPeakEQ(BEQSuite):
    @classmethod
    def ar(cls, input, freq=1200.0, rq=1.0, db=0.0):
        return cls._multi_new('audio', input, freq, rq, db)

    @classmethod
    def sc(cls, dummy=None, freq=1200.0, rq=1.0, db=0.0):
        sr = ifu.SampleRate.ir()
        a = bi.pow(10, db/40)
        w0 = bi.pi * 2 * freq * ifu.SampleDur.ir()
        alpha = bi.sin(w0) * 0.5 * rq
        b0rz = bi.reciprocal(1 + (alpha / a))
        a0 = (1 + (alpha * a)) * b0rz
        a2 = (1 - (alpha * a)) * b0rz
        b1 = 2.0 * bi.cos(w0) * b0rz
        b2 = (1 - (alpha / a)) * -b0rz
        return [a0, -b1, a2, b1, b2]


class BLowShelf(BEQSuite):
    @classmethod
    def ar(cls, input, freq=1200.0, rs=1.0, db=0.0):
        return cls._multi_new('audio', input, freq, rs, db)

    @classmethod
    def sc(cls, dummy=None, freq=1200.0, rs=1.0, db=0.0):
        sr = ifu.SampleRate.ir()
        a = bi.pow(10, db/40)
        w0 = bi.pi * 2 * freq * ifu.SampleDur.ir()
        cos_w0 = bi.cos(w0)
        sin_w0 = bi.sin(w0)
        alpha = sin_w0 * 0.5 * bi.sqrt((a + bi.reciprocal(a)) * (rs - 1) + 2.0)
        i = (a+1) * cos_w0
        j = (a-1) * cos_w0
        k = 2 * bi.sqrt(a) * alpha
        b0rz = bi.reciprocal((a+1) + j + k)
        a0 = a * ((a+1) - j + k) * b0rz
        a1 = 2 * a * ((a-1) - i) * b0rz
        a2 = a * ((a+1) - j - k) * b0rz
        b1 = 2.0 * ((a-1) + i) * b0rz
        b2 = ((a+1) + j - k) * -b0rz
        return [a0, a1, a2, b1, b2]


class BHiShelf(BEQSuite):
    @classmethod
    def ar(cls, input, freq=1200.0, rs=1.0, db=0.0):
        return cls._multi_new('audio', input, freq, rs, db)

    @classmethod
    def sc(cls, dummy=None, freq=1200.0, rs=1.0, db=0.0):
        sr = ifu.SampleRate.ir()
        a = bi.pow(10, db/40)
        w0 = bi.pi * 2 * freq * ifu.SampleDur.ir()
        cos_w0 = bi.cos(w0)
        sin_w0 = bi.sin(w0)
        alpha = sin_w0 * 0.5 * bi.sqrt((a + bi.reciprocal(a)) * (rs - 1) + 2.0)
        i = (a+1) * cos_w0
        j = (a-1) * cos_w0
        k = 2 * bi.sqrt(a) * alpha
        b0rz = bi.reciprocal((a+1) - j + k)
        a0 = a * ((a+1) + j + k) * b0rz
        a1 = -2.0 * a * ((a-1) + i) * b0rz
        a2 = a * ((a+1) + j - k) * b0rz
        b1 = -2.0 * ((a-1) - i) * b0rz
        b2 = ((a+1) - j - k) * -b0rz
        return [a0, a1, a2, b1, b2]


class BLowPass4(ugn.PseudoUGen):
    @classmethod
    def ar(cls, input, freq=1200.0, rq=1.0):
        rq = bi.sqrt(rq)
        coefs = BLowPass.sc(None, freq, rq)
        return flt.SOS.ar(flt.SOS.ar(input, *coefs), *coefs)


class BHiPass4(ugn.PseudoUGen):
    @classmethod
    def ar(cls, input, freq=1200.0, rq=1.0):
        rq = bi.sqrt(rq)
        coefs = BHiPass.sc(None, freq, rq)
        return flt.SOS.ar(flt.SOS.ar(input, *coefs), *coefs)
