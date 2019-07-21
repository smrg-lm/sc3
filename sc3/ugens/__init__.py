"""
Builtin UGen classes submodule.
"""

import importlib as _importlib
import inspect as _inspect
import pathlib as _pathlib
# import sys as _sys


installed_ugens = dict()


_package_path = _pathlib.Path(__file__).parent

_module = _importlib.import_module(_package_path.parent.name + '.ugen')
_mapping = _inspect.getmembers(_module, _inspect.isclass)  # NOTE: abajo
installed_ugens.update(dict(_mapping))

_package_qual = _package_path.parent.name + '.' + _package_path.name
_sub_modules = _package_path.glob('**/[!_]*.py')

for _module_filename in _sub_modules:
    _full_name = _package_qual + '.' + _module_filename.stem
    print('@@@ full_name:', _full_name)
    _module = _importlib.import_module(_full_name)
    _mapping = _inspect.getmembers(_module, _inspect.isclass)  # *** NOTE: y también tiene que ser UGen... # es un array de tuplas # el formato se convierte en diccionario con dict(_mapping)
    installed_ugens.update(dict(_mapping))
    # _sys.modules[__name__].__dict__.update(dict(_mapping))  # *** NOTE: leer todo https://docs.python.org/3/reference/import.html
