"""Random wrapped for Routines"""

from . import main as _libsc3


def random():
    return _libsc3.main.rgen.random()


# TODO ....
