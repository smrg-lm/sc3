"""SystemActions.sc"""

from abc import ABC, abstractclassmethod

from ..synth import server as srv
from ..seq import clock as clk
from . import functions as fn


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

    @classmethod
    def _do_action(cls, obj, selector, *args):
        fn.value(getattr(obj, selector, obj), *args)


class CmdPeriod(AbstractSystemAction):
    # // Things to clear when hitting <cmd-.>.
    era = 0
    clear_clocks = True
    free_servers = True
    free_remote = False

    @classmethod
    def do_once(cls, object):
        def do_func():
            cls.remove(do_func)
            cls._do_action(item, 'do_on_cmd_period')
        cls.add(do_func)

    @classmethod
    def run(cls):
        if cls.clear_clocks:
            clk.SystemClock.clear()
            clk.AppClock.clear()
        for item in cls.objects[:]:
            cls._do_action(item, 'do_on_cmd_period')
        if cls.free_servers:
            srv.Server.free_all(cls.free_remote) # // stop all sounds on local, or remote servers
            srv.Server.resume_status_threads()
        cls.era += 1

    @classmethod
    def hard_run(cls):
        clk.SystemClock.clear()
        clk.AppClock.clear()
        clk.TempoClock.default.clear()
        for item in cls.objects[:]:
            cls._do_action(item, 'do_on_cmd_period')
        srv.Server.hard_free_all()  # // stop all sounds on local servers
        srv.Server.resume_status_threads()
        cls.era += 1


class StartUp(AbstractSystemAction):
    # // Things to do after startup file executed.
    done = False

    @classmethod
    def run(cls):
        cls.done = True
        for item in cls.objects[:]:
            cls._do_action(item, 'do_on_start_up')

    @classmethod
    def defer(cls, obj):
        if cls.done:
            cls._do_action(obj, 'do_on_start_up')
        else:
            cls.add(obj)


class ShutDown(AbstractSystemAction):
    # // Things to do before system shuts down.
    @classmethod
    def run(cls):
        for item in cls.objects[:]:
            cls._do_action(item, 'do_on_shut_down')


class OnError(AbstractSystemAction):
    # // Things to do on a system reset.
    @classmethod
    def run(cls):
        for item in cls.objects[:]:
            cls._do_action(item, 'do_on_error')


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
        cls.perform_function(
            server, lambda obj: cls._do_action(obj, selector, server))

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


class ServerBoot(AbstractServerAction):
    # // Things to do after server has booted.
    @classmethod
    def function_selector(cls):
        return 'do_on_server_boot'


class ServerQuit(AbstractServerAction):
    # // Things to do after server has quit.
    @classmethod
    def function_selector(cls):
        return 'do_on_server_quit'


class ServerTree(AbstractServerAction):
    # // Things to do after server has booted and initialised.
    @classmethod
    def function_selector(cls):
        return 'do_on_server_tree'
