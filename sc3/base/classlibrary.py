
import logging


_logger = logging.getLogger(__name__)


class ClassLibrary():
    '''
    This class is a hack to avoid class attribute initialization problems
    caused by very nasty nested cyclic imports and global state. The init()
    method of this class is called at the end of main initiallization.
    '''

    _init_list = []
    _initialized = False

    @classmethod
    def add(cls, item, func):
        if cls._initialized:
            func(item)
        else:
            entry = {'item': item, 'func': func}
            cls._init_list.append(entry)

    @classmethod
    def init(cls):
        while len(cls._init_list) > 0:
            entry = cls._init_list.pop()
            entry['func'](entry['item'])
            _logger.debug('+ init: %s', entry['item'].__name__)
        cls._initialized = True
