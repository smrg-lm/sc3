"""FFTUnpacking.sc"""

# // "Unpack FFT" UGens (c) 2007 Dan Stowell.
# // Magical UGens for treating FFT data as demand-rate streams.

from .. import ugen as ugn


# // Actually this just wraps up a bundle of Unpack1FFT UGens.
class UnpackFFT(ugn.MultiOutUGen):
    ...


class Unpack1FFT(ugn.UGen):
    ...


# // Conveniences to apply calculations to an FFT chain.
class PV_ChainUGen(ugn.WidthFirstUGen):
    ...


# // This does the demanding, to push the data back into an FFT buffer.
class PackFFT(PV_ChainUGen):
    ...
