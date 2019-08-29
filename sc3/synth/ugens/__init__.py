"""
Builtin UGen classes submodule.
"""

import importlib as _importlib
import pkgutil as _pkgutil
import inspect as _inspect
import sys as _sys


_module = _importlib.import_module('sc3.synth.ugen')
_mapping = _inspect.getmembers(_module, _inspect.isclass)
_sys.modules[__name__].__dict__.update(dict(_mapping))
installed_ugens = dict(_mapping)

for module_info in _pkgutil.walk_packages(__path__, __name__ + '.'):
    if module_info.name.split('.')[-1][0] == '_':
        continue
    _module = _importlib.import_module(module_info.name)
    _mapping = _inspect.getmembers(_module, _inspect.isclass)
    _sys.modules[__name__].__dict__.update(dict(_mapping))
    installed_ugens.update(dict(_mapping))
