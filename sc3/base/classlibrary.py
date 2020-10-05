
import logging
import importlib
import sys


_logger = logging.getLogger(__name__)


class ClassLibrary():
    '''
    This class is a hack to avoid class attribute initialization
    problems caused by very nasty nested cyclic imports. The method
    init() is called at the end of main.
    '''

    _init_list = []
    _imports_list = []
    _initialized = False

    @classmethod
    def add(cls, item, func):
        if cls._initialized:
            func(item)
        else:
            entry = {'item': item, 'func': func}
            cls._init_list.append(entry)

    @classmethod
    def late_imports(cls, module_name, *imports):
        '''
        For imports in cyclic conflict used only at runtime.
        Hack: late imports own imports still can have cyclic conflicts.
        '''
        cls._imports_list.append((module_name, imports))
        if cls._initialized:
            cls._init_imports()

    @classmethod
    def init(cls):
        cls._init_imports()
        while len(cls._init_list) > 0:
            entry = cls._init_list.pop()
            entry['func'](entry['item'])
            _logger.debug('+ init: %s', entry['item'].__name__)
        cls._initialized = True

    @classmethod
    def _init_imports(cls):
        while len(cls._imports_list) > 0:
            name, imports = cls._imports_list.pop()
            for item in imports:
                if isinstance(item, tuple):
                    module = importlib.import_module(item[0])
                    alias = item[1]
                    sys.modules[name].__dict__.update({alias: module})
                else:
                    module = importlib.import_module(item)
                    sys.modules[name].__dict__.update({item: module})
