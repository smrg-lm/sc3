"""Builtin UGen classes package."""

import sys as _sys

from ...base import _hooks as hks


installed_ugens = dict()  # Must contain the full list of ugens.
all_ugens = dict()


def install_ugen(ugen):
    '''
    Makes a single ugen available to sc3.synth.ugens.installed_ugens (required
    by SynthDesc for the ugen to be valid).
    '''
    entry = {ugen.__name__: ugen}
    _sys.modules[__name__].__dict__.update(entry)
    installed_ugens.update(entry)


def install_ugens_module(name, package=None):
    '''
    At the end of an external ugens module call install_ugens_module(__name__)
    to make all classes available in sc3.synth.ugens.installed_ugens.
    Parameters name and package are the arguments of importlib.import_module().
    '''
    full_us, all_us = hks.import_all_module(name, package, bind=__name__)
    installed_ugens.update(full_us)
    all_ugens.update(all_us)


def install_ugens_package(path, name):
    '''
    Call this function in the __init__.py file of an ugens package with
    __path__ and __name__ as arguments to make all classes available in
    sc3.synth.ugens.installed_ugens. Parameters path and name are used as
    arguments for pkgutil.walk_packages().
    '''
    full_us, all_us = hks.import_all_package(path, name, bind=__name__)
    installed_ugens.update(full_us)
    all_ugens.update(all_us)


install_ugens_module('sc3.synth.ugen')
install_ugens_package(__path__, __name__)

__all__ = list(all_ugens.keys())
