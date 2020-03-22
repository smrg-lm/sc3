"""
Builtin UGen classes package.
"""

import importlib as _importlib
import pkgutil as _pkgutil
import inspect as _inspect
import sys as _sys


installed_ugens = dict()


def install_ugen(ugen):
    '''
    Make a single ugen available to sc3.synth.ugens.installed_ugens (required
    by SynthDesc for the ugen to be valid).
    '''
    entry = {ugen.__name__: ugen}
    _sys.modules[__name__].__dict__.update(entry)
    installed_ugens.update(entry)


def install_ugens_module(name, package=None):
    '''
    At the end of an external ugens mdoules call install_ugens_module(__name__)
    to make all classes available to sc3.synth.ugens.installed_ugens. name and
    package are the arguments of importlib.import_module().
    '''
    module = _importlib.import_module(name, package)
    mapping = _inspect.getmembers(module, _inspect.isclass)
    _sys.modules[__name__].__dict__.update(dict(mapping))
    installed_ugens.update(dict(mapping))


def install_ugens_package(path, name):
    '''
    Call this function in the __init__.py file of an ugens package with
    varaibles __path__ and __name__ as paramenters to make all classes
    available to sc3.synth.ugens.installed_ugens. path and name are used as
    arguments for pkgutil.walk_packages().
    '''
    for module_info in _pkgutil.walk_packages(path, name + '.'):
        if module_info.name.split('.')[-1][0] == '_':
            continue
        module = _importlib.import_module(module_info.name)
        mapping = _inspect.getmembers(module, _inspect.isclass)
        _sys.modules[__name__].__dict__.update(dict(mapping))
        installed_ugens.update(dict(mapping))


install_ugens_module('sc3.synth.ugen')
install_ugens_package(__path__, __name__)
