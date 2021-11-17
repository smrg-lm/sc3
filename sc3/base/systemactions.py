"""SystemActions.sc"""

from ..synth import server as srv
from . import clock as clk


__all__ = [
    'CmdPeriod', 'StartUp', 'ShutDown',  # 'OnError',
    'ServerBoot', 'ServerQuit', 'ServerTree']


class SystemAction():
    # _actions is {action: (args, kwargs), ...}

    @classmethod
    def add(cls, action, *args, **kwargs):
        '''
        Register a function to be evaluated after a specific library state.

        Parameters
        ----------
        action : function
            The action function.
        args :
            Optional positional arguments passed to `action` when evaluated.
        kwargs:
            Optional keyword arguments passed to `action` when evaluated.
        '''

        cls._actions[action] = (args, kwargs)

    @classmethod
    def remove(cls, action):
        '''Remove a function from the evaluation queue.'''
        if action in cls._actions:
            del cls._actions[action]

    @classmethod
    def remove_all(cls):
        '''Remove all registered functions.'''
        cls._actions = dict()

    @classmethod
    def run(cls):
        '''Evaluate functions in order of registration.'''
        for action in cls._actions.copy():
            cls._do_action(action)

    @classmethod
    def _do_action(cls, action):
        if action in cls._actions:  # May be removed by a previous action.
            args, kwargs = cls._actions[action]
            action(*args, **kwargs)


class CmdPeriod(SystemAction):
    '''Register functions to be called when a reset is needed.

    This singleton class clears clocks and reset servers' nodes when `run`
    or `hard_run` is called. It is similar to a MIDI panic action.
    '''

    _actions = dict()
    era = 0
    clear_clocks = True
    free_servers = True
    free_remote = False

    @classmethod
    def do_once(cls, action, *args, **kwargs):
        '''Register a function to be evaluated once and then removed.

        Parameters
        ----------
        action : function
            The action function.
        args :
            Optional positional arguments passed to `action` when evaluated.
        kwargs:
            Optional keyword arguments passed to `action` when evaluated.
        '''

        def once_action(action, *args, **kwargs):
            cls.remove(once_action)
            action(*args, **kwargs)

        cls.add(once_action, action, *args, **kwargs)

    @classmethod
    def run(cls):
        '''Reset clocks and servers.

        This method clears all clocks' scheduling queues and stop all non
        permanent `TempoClock` instances and frees all the nodes of the
        registered servers through `Server.free_all` class method.
        '''

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
        '''Reset clocks and servers.

        This method clears all clocks' scheduling queues and stop all non
        permanent `TempoClock` instances and frees all the nodes of the
        running servers through `Server.hard_free_all` class method.
        '''

        clk.SystemClock.clear()
        clk.AppClock.clear()
        for action in cls._actions.copy():
            cls._do_action(action)
        srv.Server.hard_free_all()  # // stop all sounds on local servers
        srv.Server._resume_status_threads()
        cls.era += 1


class StartUp(SystemAction):
    '''Register functions to be evaluated after the startup is finished.

    A singleton class to register functions to perform an action after the
    library has been initialized, and after the startup file has run.
    '''

    _actions = dict()
    done = False

    @classmethod
    def run(cls):
        '''Evaluate functions in order of registration.'''
        cls.done = True
        for action in cls._actions.copy():
            cls._do_action(action)  # NOTE: '__on_start_up'

    @classmethod
    def defer(cls, action, *args, **kwargs):
        '''
        Register a function to be evaluated after startup is finished, or
        immediately, if this has happened already. Optional positional or
        keyword arguments can be supplied.

        Parameters
        ----------
        action : function
            Post startup action function.
        args :
            Optional positional arguments passed to `action` when evaluated.
        kwargs:
            Optional keyword arguments passed to `action` when evaluated.
        '''

        if cls.done:
            action(*args, **kwargs)
        else:
            cls.add(action, *args, **kwargs)


class ShutDown(SystemAction):
    '''Register functions to be evaluated before system shuts down.

    A singleton class to register functions to perform an action before
    system shut down.
    '''

    _actions = dict()
    pass # NOTE: '__on_shut_down'


# class OnError(SystemAction):
#     # // Things to do on a system reset.
#     _actions = dict()
#     pass # NOTE: '__do_on_error'


class ServerAction():
    '''Register server state related functions.

    This is a base superclass for singletons like `ServerQuit`, which
    provides a place for registering functions for events that should happen
    when something happens in the server.
    '''

    # _servers is {server: {action: (args, kwargs)}, ...},

    @classmethod
    def add(cls, server, action, *args, **kwargs):
        '''Register a function for a specific server.

        Parameters
        ----------
        server : Server
            The server for which the action is evaluated.
        action : function
            The function to be evaluated for the specific server state.
        args :
            Optional positional arguments passed to `action` when called.
        kwargs :
            Optional keyword arguments passed to `action` when called.
        '''

        # server='all' actions are always called for any server passed to run.
        # server='default' actions are always called for default server.
        if server not in cls._servers:
            cls._servers[server] = dict()
        cls._servers[server].update({action: (args, kwargs)})

    @classmethod
    def remove(cls, server, action):
        '''Remove a function for the specified server.'''
        if server in cls._servers:
            cls._servers[server].get(action, None)  # discard

    @classmethod
    def remove_server(cls, server):
        '''Remove a server from all server actions.'''
        if server in cls._servers:
            del cls._servers[server]

    @classmethod
    def remove_all(cls):
        '''Remove all servers from server actions.'''
        cls._servers = dict()

    @classmethod
    def run(cls, server=None):
        '''Evaluate functions in order of registration of each server.'''
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
    '''Register actions to be taken when a server has booted.

    Singleton class that provides a place for registering functions for
    events that should happen when a given server has booted.
    '''

    _servers = dict()
    pass # NOTE: '__on_server_boot'


class ServerQuit(ServerAction):
    '''Register actions to be taken when a server quits.

    Singleton class that provides a place for registering functions for
    events that should happen when a given server quits.
    '''

    _servers = dict()
    pass # NOTE: '__on_server_quit'


class ServerTree(ServerAction):
    '''Register actions to initialise a basic tree of groups on the server.

    Singleton class that provides a place for registering functions for
    events that should happen when a given server has booted and initialised
    or when all synths are freed. This is to initialise a basic tree of groups
    on the server.
    '''

    # FIXME: Documentation says "when all synths are freed" but I think
    # this wasn't implemented, does it means after s.free_all()?

    # // Things to do after server has booted and initialised.
    _servers = dict()
    pass # NOTE: '__on_server_tree'
