
import importlib as importlib
import pkgutil as pkgutil
import inspect as inspect
import sys as sys


def import_all_classes(path, name, update=False):  # __path__, __name__
    all_classes = dict()
    for module_info in pkgutil.walk_packages(path):
        if module_info.name[0] == '_':
            continue
        full_name = name + '.' + module_info.name
        module = importlib.import_module(full_name)
        mapping = inspect.getmembers(module, inspect.isclass)
        all_classes.update(dict(mapping))
        if update:
            sys.modules[name].__dict__.update(dict(mapping))
    return all_classes
