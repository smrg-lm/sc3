"""Import related hooks."""

import importlib as _importlib
import pkgutil as _pkgutil
import inspect as _inspect
import sys as _sys


def import_all_module(name, package=None, *, bind):
    '''
    Imports all non internal clases and make the available from the
    module passed to bind. The module referred by bind must be already
    available in sys.modules dict. The return value is a tuple of two dict
    containing the full namespace and the import * namespace.
    Parameters name and package are the arguments of importlib.import_module().
    '''
    module = _importlib.import_module(name, package)
    full_cs = dict(_inspect.getmembers(module, _inspect.isclass))
    if hasattr(module, '__all__'):
        all_cs = {name: full_cs[name] for name in module.__all__ if full_cs.get(name, False)}
    else:
        all_cs = full_cs
    _sys.modules[bind].__dict__.update(all_cs)
    return full_cs, all_cs


def import_all_package(path, name, *, bind):
    '''
    Same as import_all_module but imports all non internal classes from all
    non internal modules within a package and makes them available from the
    module passed to bind.
    '''
    full_cs = dict()
    all_cs = dict()
    for module_info in _pkgutil.walk_packages(path, name + '.'):
        if module_info.name.split('.')[-1][0] == '_':
            continue
        a, p = import_all_module(module_info.name, bind=bind)
        full_cs.update(a)
        all_cs.update(p)
    return full_cs, all_cs



class OptionalModuleNotFound(ModuleNotFoundError):
    pass


class OptionalModuleProxy():
    def __init__(self, name):
        super().__setattr__(
            'msg', f'optional module {repr(name)} is not installed')

    def __getattr__(self, name):
        raise OptionalModuleNotFound(super().__getattribute__('msg'))

    def __setattr__(self, name, value):
        raise OptionalModuleNotFound(super().__getattribute__('msg'))


def import_optional_module(name, package=None):
    try:
        return _importlib.import_module(name, package)
    except ModuleNotFoundError:
        return OptionalModuleProxy(name)
