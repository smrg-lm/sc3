"""
Builtin Pattern classes package.
"""

from ...base import _hooks as hks


lst = list(hks.import_all_module('sc3.seq.pattern', bind=__name__).keys())
lst.extend(hks.import_all_package(__path__, __name__, bind=__name__).keys())

__all__ = lst
