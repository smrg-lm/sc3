"""
Builtin Pattern classes package.
"""

import importlib as _importlib
import pkgutil as _pkgutil
import inspect as _inspect
import sys as _sys


def import_all_module(name, package=None):
    # s3.synth.ugens.__init__.install_ugens_module variation.
    # The difference is that it imports only classes.
    # This functions should be rewritten to collect form __all__
    # and optionally 'install' as in the case of UGens.
    '''
    At the end of an external module call import_all_module(__name__)
    to make all classes available to a module or package. Arguments
    name and package are passed to importlib.import_module().
    '''
    module = _importlib.import_module(name, package)
    mapping = _inspect.getmembers(module, _inspect.isclass)
    _sys.modules[__name__].__dict__.update(dict(mapping))


def import_all_package(path, name):
    # s3.synth.ugens.__init__.install_ugens_package variation.
    '''
    Call this function in the __init__.py file of a package with
    varaibles __path__ and __name__ as paramenters to make all
    classes available form package __name__. Arguments path and
    name are passed to pkgutil.walk_packages().
    '''
    for module_info in _pkgutil.walk_packages(path, name + '.'):
        if module_info.name.split('.')[-1][0] == '_':
            continue
        module = _importlib.import_module(module_info.name)
        mapping = _inspect.getmembers(module, _inspect.isclass)
        _sys.modules[__name__].__dict__.update(dict(mapping))


import_all_module('sc3.seq.pattern')
import_all_package(__path__, __name__)
