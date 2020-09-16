"""
Import related hooks.
"""

import importlib as _importlib
import pkgutil as _pkgutil
import inspect as _inspect
import sys as _sys


def import_all_module(name, package=None, *, bind):
    '''
    Imports all non internal clases and make the available from the
    module passed to bind. The module referred by bind must be already
    available in sys.modules dict. Return value is a mapping of the form
    {'class_name': class_obj, ...}. Parameters name and package are the
    arguments of importlib.import_module().
    '''
    module = _importlib.import_module(name, package)
    mapping = dict(_inspect.getmembers(module, _inspect.isclass))
    _sys.modules[bind].__dict__.update(mapping)
    return mapping


def import_all_package(path, name, *, bind):
    '''
    Same as import_all_module but imports all non internal classes from all
    non internal modules within a package and makes them available from the
    module passed to bind.
    '''
    ret = dict()
    for module_info in _pkgutil.walk_packages(path, name + '.'):
        if module_info.name.split('.')[-1][0] == '_':
            continue
        module = _importlib.import_module(module_info.name)
        mapping = dict(_inspect.getmembers(module, _inspect.isclass))
        _sys.modules[bind].__dict__.update(mapping)
        ret.update(mapping)
    return ret
