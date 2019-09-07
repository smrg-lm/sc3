"""Demand.sc"""

from .. import ugen as ugn


class Demand(ugn.MultiOutUGen):
    ...


class Duty(ugn.UGen):
    ...


class TDuty(Duty):
    ...


class DemandEnvGen(ugn.UGen):
    ...


class DUGen(ugn.UGen):
    ...


class Dseries(DUGen):
    ...


class Dgeom(DUGen):
    ...


class Dbufrd(DUGen):
    ...


class Dbufwr(DUGen):
    ...


class ListDUGen(DUGen):
    ...


class Dseq(ListDUGen):
    pass


class Dser(ListDUGen):
    pass


class Dshuf(ListDUGen):
    pass


class Drand(ListDUGen):
    pass


class Dxrand(ListDUGen):
    pass


class Dwrand(DUGen):
    ...


class Dswitch1(DUGen):
    ...


class Dswitch(Dswitch1):
    ...


class Dwhite(DUGen):
    ...


class Dbrown(DUGen):
    ...


class Dibrown(Dbrown):
    pass


class Dstutter(DUGen):
    ...


class Dconst(DUGen):
    ...


class Dreset(DUGen):
    ...


class Dpoll(DUGen):
    ...


# // Behave as identical in multiple uses.
class Dunique(ugn.UGen):
    # TODO: todo.

    # UGen graph parameter interface #
    # TODO: ver el resto en UGenParameter

    def _as_ugen_input(self, *_):
        pass # TODO: es complicado para ahora.
