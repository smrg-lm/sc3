"""
Builtin UGen classes submodule.
"""

from ...base import _importall


installed_ugens =  _importall.import_all_classes(__path__, __name__)
