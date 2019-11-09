"""NodeWatcher.sc"""

from ..base import responsedefs as rdf
from ..base import systemactions as sac
from ..base import model as mdl


# // Watches a server address for node-related messages


class AbstractNodeWatcher():
    def __init__(self, server):
        self._server = server
        self._nodes = dict()  # *** BUG: es set para BasicNodeWatcher y DebugNodeWatcher pero dict para NodeWatcher. Y se inicializa en clear().
        self._responders = []
        self._is_watching = False
        self.clear()
        # NOTE: why multiple addr in sclang? a Server should only have one addr.
        for cmd in self.cmds:
            method = '_' + cmd[1:]
            print(f"@@@ INIT {method}, {cmd}")
            osc_func = rdf.OSCFunc(
                (lambda mthd: lambda msg, *_: self.respond(mthd, msg))(method),  # *** BUG: ver argumentos variables en OSCFunc function y fn.value
                cmd, self._server.addr)
            osc_func.permanent = True
            osc_func.disable()
            self.responders.append(osc_func)

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
        return tuple()

    def clear(self):
        pass

    def respond(self, method, msg):
        getattr(self, method)(*msg[1:])

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


class BasicNodeWatcher(AbstractNodeWatcher):
    def node_is_playing(self, node_id):
        return node_id in self._nodes

    def add_playing_node(self, node_id):
        # // Sometimes it is needed to set this before the server reply.
        return self._nodes.add(node_id)  # *** BUG: es inconsistente no son los mismos métodos para set y dict.

    def clear(self):
        self._nodes = set()

    @property
    def cmds(self):
        return ('/n_go', '/n_end')

    def _n_end(self, node_id):
        self._nodes.remove(node_id)  # *** BUG: es inconsistente no son los mismos métodos para set y dict.

    def _n_go(self, node_id):
        self._nodes.add(node_id)  # *** BUG: es inconsistente no son los mismos métodos para set y dict.


class MetaNodeWatcher(type):
    def __init__(cls, *_):
        cls.all = dict()
        sac.CmdPeriod.add(cls)
        sac.ServerBoot.add(cls)
        sac.ServerQuit.add(cls)

    def new_from(cls, server):
        res = cls.all.get(server.name)
        if res is None:
            res = cls(server)
            res.start()
            cls.all[server.name] = res
        return res

    def global_register(cls, node, assume_playing=False):
        watcher = cls.new_from(node.server)
        watcher.register(node, assume_playing)

    def global_unregister(cls, node):
        watcher = cls.new_from(node.server)
        watcher.unregister(node)

    def cmd_period(cls):
        for item in cls.all:
            item.clear()

    def do_on_server_quit(cls, server):
        cls.do_on_server_boot(server)

    def do_on_server_boot(cls, server):
        node_watchers = cls.all.pop(server.name, None)
        if node_watchers is not None:
            node_watchers.clear()


class NodeWatcher(BasicNodeWatcher, metaclass=MetaNodeWatcher):
    # FIXME: A NodeWatcher instance is one by server but NodeWatcher class
    # contains NodeWatchers for all servers.
    # // Watches registered nodes and sets their isPlaying/isRunning flag.
    # // A node needs to be registered to be addressed, other nodes are ignored.
    @property
    def cmds(self):
        return ('/n_go', '/n_end', '/n_off', '/n_on')

    def respond(self, method, msg):
        print(f"@@@ RESPOND {method}, {msg}")
        node = self._nodes.get(msg[1])  # FIXME: is a dict here a set elsewhere.
        if node is not None:
            # group = self._nodes.get(msg[2])  # *** BUG: no sirve si ignora el segundo argumento en sclang, lo usa DebugNodeWatcher.
            getattr(self, method)(node)  #, group)  # *** BUG: el segundo argumento está de más para NodeWatcher, se soluciona con fn.value, pero me parece poco claro.

    def clear(self):
        # // we must copy 'nodes' b/c a /n_end dependant (NotificationCenter)
		# // might add or remove nodes from the collection
		# // NEVER iterate over a collection that might change
        for node in self._nodes.copy().values():
            node.is_playing = False  # BUG: estos atributos de Node podrían ser internos si la librería es quién les cambia el estado, dejarlo visible puede crear confusión o mal uso.
            node.is_running = False  # BUG: o podría ser una propiedad y acá se setea _is_running/playing.
            mdl.NotificationCenter.notify(node, '/n_end', node, '/n_end') # *** BUG: cómo pasa '/n_end', node? sclang??
        self._nodes = dict()

    def register(self, node, assume_playing=False):
        if not self._server.status_watcher.server_running:
            # self._nodes.clear()  # *** BUG: sclang usa removeAll sin argumentos, que no hace nada!
            return
        if self._is_watching:
            if assume_playing and self._nodes.get(node.node_id) is None:
                node.is_playing = True
            self._nodes[node.node_id] = node

    def unregister(self, node):
        self._nodes.pop(node.node_id, None)

    def _n_go(self, node):
        print(f"@@@ N_GO {node}")
        node.is_playing = False
        node.is_running = False
        mdl.NotificationCenter.notify(node, '/n_go')

    def _n_end(self, node):
        print(f"@@@ N_END {node}")
        self.unregister(node)
        node.is_playing = False
        node.is_running = False
        mdl.NotificationCenter.notify(node, '/n_end', node, '/n_end')  # *** BUG: los argumentos agregados, ver NotificationCenter.

    def _n_off(self, node):
        print(f"@@@ N_OFF {node}")
        node.is_running = False
        mdl.NotificationCenter.notify(node, '/n_off')

    def _n_on(self, node):
        print(f"@@@ N_ON {node}")
        node.is_running = False
        mdl.NotificationCenter.notify(node, '/n_on')


class DebugNodeWatcher(BasicNodeWatcher):
    ...
