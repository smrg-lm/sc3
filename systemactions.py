"""SystemActions.sc"""

from abc import ABC, abstractclassmethod
import warnings

import supercollie.server as srv


class AbstractSystemAction(ABC):
    objects = None

    @classmethod
    def init(cls):
        cls.objects = []

    @classmethod
    def add(cls, obj):
        cls.objects or cls.init() # // lazy init
        if obj not in cls.objects:
            cls.objects.append(obj)

    @classmethod
    def remove(cls, obj):
        # BUG: sclang no tira error si el elemento no está, ver si es necesario el comportamiento, y ver todos los métodos similares
        #if obj in cls.objects:
        cls.objects.remove(obj)

    @classmethod
    def remove_all(cls):
        cls.init()

    @abstractclassmethod
    def run(cls):
        pass


# // things to clear when hitting cmd-.
class CmdPeriod(AbstractSystemAction):
    pass


# // things to do after startup file executed
class StartUp(AbstractSystemAction): # TODO
    @classmethod
    def defer(cls, obj):
        obj() # BUG: TEST para probar SynthDef


# // things to do before system shuts down
class ShutDown(AbstractSystemAction):
    pass


# // things to do on a system reset
class OnError(AbstractSystemAction):
    pass


class AbstractServerAction(AbstractSystemAction):
    @classmethod
    def init(cls):
        cls.objects = dict()

    @classmethod
    def perform_function(cls, server: (str, srv.Server), function):
        if cls.objects is not None:
            if server in cls.objects:
                for item in cls.objects[server][:]:
                    function(item)
            else:
                msg = "{} server '{}' not added"
                warnings.warn(msg.format(cls, server))
            if server is srv.Server.default:
                if 'default' in cls.objects:
                    for item in cls.objects['default'][:]:
                        function(item)
                else:
                    msg = "{} key 'default' not initialized"
                    warnings.warn(msg.format(cls))
            if 'all' in cls.objects:
                for item in cls.objects['all'][:]:
                    function(item)
            else:
                msg = "{} key 'all' not initialized"
                warnings.warn(msg.format(cls))

    @classmethod
    def run(cls, server):
        selector = cls.function_selector()
        cls.perform_function(server, lambda obj: getattr(obj, selector)(server))

    @abstractclassmethod
    def function_selector(cls):
        pass

    @classmethod
    def add(cls, obj, server=None):
        server = server or 'all'
        cls.objects or cls.init()
        if server in cls.objects:
            list = cls.objects[server]
        else:
            list = []
            cls.objects[server] = list
        if obj not in list:
            list.append(obj)

    @classmethod
    def add_to_all(cls, obj):
        cls.add(obj, 'all')

    @classmethod
    def remove(cls, obj, server=None):
        server = server or 'all'
        if cls.objects is not None:
            if server in cls.objects:
                cls.objects[server].remove(obj)

    @classmethod
    def remove_server(cls, server):
        if server in cls.objects:
            del cls.objects[server]


# // things to do after server has booted
class ServerBoot(AbstractServerAction):
    @classmethod
    def function_selector(cls):
        return 'do_on_server_boot'


# // things to do after server has quit
class ServerQuit(AbstractServerAction):
    @classmethod
    def function_selector(cls):
        return 'do_on_server_quit'


# // things to do after server has booted and initialised
class ServerTree(AbstractServerAction):
    @classmethod
    def function_selector(cls):
        return 'do_on_server_tree'
