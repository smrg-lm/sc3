"""NodeWatcher.sc"""

from ..base import responsedefs as rdf
from ..base import systemactions as sac
from ..base import model as mdl


# // Watches a server address for node-related messages


class NodeWatcher():
    # // Watches registered nodes and sets their isPlaying/isRunning flag.
    # // A node needs to be registered to be addressed, other nodes are ignored.

    def __init__(self, server):
        self._server = server
        self._nodes = dict()
        self._responders = []
        self._is_watching = False
        for cmd in self.cmds:
            method = '_' + cmd[1:]
            osc_func = rdf.OscFunc(
                (lambda mthd: lambda msg, *_: self.respond(mthd, msg))(method),
                cmd, self._server.addr)
            osc_func.permanent = True
            # osc_func.disable()  # *** NOTE: no sense if self.start() is not manual.
            self._responders.append(osc_func)
        sac.CmdPeriod.add(self.__on_cmd_period)
        sac.ServerBoot.add(self._server, self.__on_server_boot)
        sac.ServerQuit.add(self._server, self.__on_server_quit)
        self.start()  # *** NOTE: could be manual: server._node_watcher.start().

    @property
    def server(self):
        return self._server

    @property
    def nodes(self):
        return self._nodes

    @property
    def responders(self):
        return self._responders

    @property
    def is_watching(self):
        return self._is_watching

    @property
    def cmds(self):
        return ('/n_go', '/n_end', '/n_off', '/n_on', '/n_move', '/n_info')

    def respond(self, method, msg):
        node = self._nodes.get(msg[1])
        if node is not None:
            getattr(self, method)(node)  # *** NOTE: podría pasar también msg completo.

    def start(self):
        if not self._is_watching:
            for item in self._responders:
                item.enable()
                self._is_watching = True

    def stop(self):
        if self._is_watching:
            for item in self._responders:
                item.free()
            self._is_watching = False
            # self.free()  # *** BUG: sclang call Object.free that does nothing.

    def register(self, node, playing=True, running=True):
        if not self._server._status_watcher.server_running:
            # self._nodes.clear()  # *** BUG: sclang usa removeAll sin argumentos, que no hace nada!
            return
        if self._is_watching:
            if self._nodes.get(node.node_id) is None:
                if playing: node._is_playing = True
                if running: node._is_running = True
            self._nodes[node.node_id] = node

    def unregister(self, node):
        self._nodes.pop(node.node_id, None)

    def registered(self, node):  # Was node_is_playing, better not to use is_*.
        return node.node_id in self._nodes

    def _clear(self):
        # // we must copy 'nodes' b/c a /n_end dependant (NotificationCenter)
        # // might add or remove nodes from the collection
        # // NEVER iterate over a collection that might change
        for node in self._nodes.copy().values():
            node._is_playing = None
            node._is_running = None
            mdl.NotificationCenter.notify(node, '/n_end')
        self._nodes = dict()

    def _n_go(self, node):
        node._is_playing = True
        node._is_running = True
        mdl.NotificationCenter.notify(node, '/n_go')

    def _n_end(self, node):
        self.unregister(node)
        node._is_playing = False
        node._is_running = False
        mdl.NotificationCenter.notify(node, '/n_end')

    def _n_off(self, node):  # response to /n_run 0
        node._is_running = False
        mdl.NotificationCenter.notify(node, '/n_off')

    def _n_on(self, node):  # response to /n_run 1
        node._is_running = True
        mdl.NotificationCenter.notify(node, '/n_on')

    def _n_move(self, node):  # response to /n_before, /n_after, /n_order
        mdl.NotificationCenter.notify(node, '/n_move')

    def _n_info(self, node):  # response to /n_query
        mdl.NotificationCenter.notify(node, '/n_info')


    ### System Actions ###

    def __on_cmd_period(self):
        self._clear()

    def __on_server_boot(self, _):
        self._clear()

    def __on_server_quit(self, _):
        self._clear()
