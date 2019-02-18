"""
_hackprovisorio_borrar.py

BORRAR Y REEMPLAZAR CUANDO SE HAGA LA ESTRUCTURA DE PAQUETE.
ESTE ARCHIVO ES SOLO PARA TENER DISPONIBLES LAS UGENS EN SYNTHDESCLIB.

Pienso: Hay que implementar un mecanismo en UGen que permita registrar
automáticamente las UGens que se agregan en tiempo de ejecución.
Está bien que el servidor no puede cargar plugins dinámicamente,
pero eso podría cambiar.
"""

import importlib as _importlib
import inspect as _inspect


installed_ugens = dict()

_ugs_modules = [
    'supercollie.ugens',
    'supercollie.inout',
    'supercollie.osc',
    'supercollie.line'
]

for _module_name in _ugs_modules:
    _module = _importlib.import_module(_module_name)
    _mapping = _inspect.getmembers(_module, _inspect.isclass) # y también tiene que ser UGen... # es un array de tuplas # el formato se convierte en diccionario con dict(_mapping)
    installed_ugens.update(dict(_mapping))
