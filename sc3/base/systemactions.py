"""SystemActions.sc"""

from ..synth import server as srv
from . import clock as clk
from . import functions as fn


__all__ = [
    'CmdPeriod', 'StartUp', 'ShutDown', 'OnError',
    'ServerBoot', 'ServerQuit', 'ServerTree']


class SystemAction():
    # _actions is {action: (args, kwargs), ...}

    @classmethod
    def add(cls, action, *args, **kwargs):
        cls._actions[action] = (args, kwargs)

    @classmethod
    def remove(cls, action):
        if action in cls._actions:
            del cls._actions[action]

    @classmethod
    def remove_all(cls):
        cls._actions = dict()

    @classmethod
    def run(cls):
        for action in cls._actions.copy():
            cls._do_action(action)

    @classmethod
    def _do_action(cls, action):
        args, kwargs = cls._actions[action]
        action(*args, **kwargs)


class CmdPeriod(SystemAction):
    # // Things to clear when hitting <cmd-.>.
    _actions = dict()
    era = 0
    clear_clocks = True
    free_servers = True
    free_remote = False

    @classmethod
    def do_once(cls, action, *args, **kwargs):
        def once_action(action, *args, **kwargs):
            cls.remove(once_action)
            action(*args, **kwargs)

        cls.add(once_action, action, *args, **kwargs)

    @classmethod
    def run(cls):
        if cls.clear_clocks:
            clk.SystemClock.clear()
            clk.AppClock.clear()
        for action in cls._actions.copy():
            cls._do_action(action)  # NOTE: '__on_cmd_period'
        if cls.free_servers:
            srv.Server.free_all(cls.free_remote) # // stop all sounds on local, or remote servers
            srv.Server._resume_status_threads()
        cls.era += 1

    @classmethod
    def hard_run(cls):
        clk.SystemClock.clear()
        clk.AppClock.clear()
        for action in cls._actions.copy():
            cls._do_action(action)
        srv.Server.hard_free_all()  # // stop all sounds on local servers
        srv.Server._resume_status_threads()
        cls.era += 1


class StartUp(SystemAction):
    # // Things to do after startup file executed.
    _actions = dict()
    done = False

    @classmethod
    def run(cls):
        cls.done = True
        for action in cls._actions.copy():
            cls._do_action(action)  # NOTE: '__on_start_up'

    @classmethod
    def defer(cls, action, *args, **kwargs):
        if cls.done:
            action(*args, **kwargs)
        else:
            cls.add(action, *args, **kwargs)


class ShutDown(SystemAction):
    # // Things to do before system shuts down.
    _actions = dict()
    pass # NOTE: '__on_shut_down'


class OnError(SystemAction):
    # // Things to do on a system reset.
    _actions = dict()
    pass # NOTE: '__do_on_error'


class ServerAction():
    # _servers is {server: {action: (args, kwargs)}, ...},

    @classmethod
    def add(cls, server, action, *args, **kwargs):
        # server='all' actions are always called for any server passed to run.
        # server='default' actions are always called for default server.
        if server not in cls._servers:
            cls._servers[server] = dict()
        cls._servers[server].update({action: (args, kwargs)})

    @classmethod
    def remove(cls, server, action):
        if server in cls._servers:
            cls._servers[server].get(action, None)  # discard

    @classmethod
    def remove_server(cls, server):
        if server in cls._servers:
            del cls._servers[server]

    @classmethod
    def remove_all(cls):
        cls._servers = dict()

    @classmethod
    def run(cls, server=None):
        if server in cls._servers:
            for action, pk in cls._servers[server].copy().items():
                action(server, *pk[0], **pk[1])
        if server is srv.Server.default and 'default' in cls._servers:
            for action, pk in cls._servers['default'].copy().items():
                action(server, *pk[0], **pk[1])
        if 'all' in cls._servers:
            for action, pk in cls._servers['all'].copy().items():
                action(server, *pk[0], **pk[1])

    @classmethod
    def _do_action(cls, action):
        pass


class ServerBoot(ServerAction):
    # // Things to do after server has booted.
    _servers = dict()
    pass # NOTE: '__on_server_boot'


class ServerQuit(ServerAction):
    # // Things to do after server has quit.
    _servers = dict()
    pass # NOTE: '__on_server_quit'


class ServerTree(ServerAction):
    # // Things to do after server has booted and initialised.
    _servers = dict()
    pass # NOTE: '__on_server_tree'
