"""BEQSuite.sc"""

from .. import ugen as ugn
from . import filter as flt


class BEQSuite(flt.Filter):
    pass


class BLowPass(BEQSuite):
    ...


class BHiPass(BEQSuite):
    ...


class BAllPass(BEQSuite):
    ...


class BBandPass(BEQSuite):
    ...


class BBandStop(BEQSuite):
    ...


class BPeakEQ(BEQSuite):
    ...


class BLowShelf(BEQSuite):
    ...


class BHiShelf(BEQSuite):
    ...


class BLowPass4(ugn.PseudoUGen):
    ...


class BHiPass4(ugn.PseudoUGen):
    ...
