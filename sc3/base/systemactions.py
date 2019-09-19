"""SystemActions.sc"""

from abc import ABC, abstractclassmethod

from ..synth import server as srv
from ..seq import clock as clk


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
        if cls.objects is not None:
            if obj in cls.objects:
                cls.objects.remove(obj)

    @classmethod
    def remove_all(cls):
        cls.init()

    @abstractclassmethod
    def run(cls):
        pass


# // things to clear when hitting cmd-.
class CmdPeriod(AbstractSystemAction):
    era = 0
    clear_clocks = True
    free_servers = True
    free_remote = False

    @classmethod
    def do_once(cls, object):
        def do_func():
            cls.remove(do_func)
            object.do_on_cmd_period() # BUG: ver extSystemActions.sc, tiene que ser algo como atexit, también cambiaría AbstractServerAction
        cls.add(do_func)

    @classmethod
    def run(cls):
        if cls.clear_clocks:
            clk.SystemClock.clear()
            clk.AppClock.clear()
        for item in cls.objects[:]:
            item.do_on_cmd_period() # BUG: ver extSystemActions.sc, tal vez es solo comprobar por un método mágico
        if cls.free_servers:
            srv.Server.free_all(cls.free_remote) # // stop all sounds on local, or remote servers
            srv.Server.resume_threads()
        cls.era += 1

    @classmethod
    def hard_run(cls):
        clk.SystemClock.clear()
        clk.AppClock.clear()
        clk.TempoClock.default.clear()
        for item in cls.objects[:]:
            item.do_on_cmd_period() # BUG: ver extSystemActions.sc, voy a tener que cambiar la interfaz y que registren la función junto con el objeto, que recibe al objeto
        srv.Server.hard_free_all() # // stop all sounds on local servers
        srv.Server.resume_threads()
        cls.era += 1


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

    @classmethod
    def run(cls, server):
        selector = cls.function_selector()
        cls.perform_function(server, lambda obj: getattr(obj, selector, obj)(server)) # NOTE: o es un objeto que responde a los selectores do_on_server_* o es una función/callable

    @classmethod
    def perform_function(cls, server, function): # server es str o srv.Server)
        if cls.objects is not None:
            if server in cls.objects:
                for item in cls.objects[server][:]:
                    function(item)
            if server is srv.Server.default:
                if 'default' in cls.objects:
                    for item in cls.objects['default'][:]:
                        function(item)
            if 'all' in cls.objects:
                for item in cls.objects['all'][:]:
                    function(item)

    @abstractclassmethod
    def function_selector(cls):
        pass


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
