
import unittest

import sys
import importlib
import pkgutil


class ImportsTestCase(unittest.TestCase):
    # Check cyclic import issues.

    @classmethod
    def setUpClass(cls):
        import sc3
        path = sc3.__path__
        name = sc3.__name__
        cls.all_modules = []
        for module_info in pkgutil.walk_packages(path, name + '.'):
            cls.all_modules.append(module_info.name)
        cls.all_modules.remove('sc3.__main__')
        if sys.platform != 'win32':
            cls.all_modules.remove('sc3.base._knownpaths')

    def test_all(self):
        for module in self.all_modules:
            for name in sys.modules.copy():
                if name.startswith('sc3'):
                    del sys.modules[name]
            with self.subTest(module=module):
                try:
                    importlib.import_module(module)
                except NameError as e:
                    raise AssertionError(f'import failed {e}') from None


if __name__ == '__main__':
    unittest.main()
