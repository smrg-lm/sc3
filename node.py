"""Node.sc"""

import threading as _threading

import supercollie.utils as ut
import supercollie.ugens as ug
import supercollie.server as sv

# Node:asTarget se implementa para Integer, Nil, y Server
# como extensión en el archivo Common/Control/asTarget.sc
# junto con nodeID. Como no lo implementa Object puede question
# no sea necesario implementarlo como multiple dispatch.
# se usa en Server:reorder, Synth, Function:(plot/asBuffer/play)
# y AbstractGroup. Tengo que revisar la librería y buscar y organizar.


class Node():
    add_actions = {
        'addToHead': 0,
        'addToTail': 1,
        'addBefore': 2,
        'addAfter': 3,
        'addReplace': 4,
        'h': 0,
        't': 1,
        # // valid action numbers should stay the same
        0: 0, 1: 1, 2: 2, 3: 3, 4: 4
    }

    @classmethod
    def basic_new(cls, server=None, node_id=None):
        obj = cls.__new__(cls)
        obj.server = server or sv.Server.default
        obj.node_id = node_id or obj.server.next_node_id()
        obj.group = None
        obj.is_playing = False
        obj.is_running = False
        return obj

    @classmethod
    def action_number_for(cls, add_action): # ='addToHead'): BUG: en sclang, semánticamente no tiene sentido el valor por defecto
        return cls.add_actions[add_action]

    def free(self, send_flag=True):
        if send_flag:
            self.server.send_msg('/n_free', self.node_id) # 11
        self.group = None
        self.is_playing = False
        self.is_running = False

    def free_msg(self):
        return ('/n_free', self.node_id) # 11

    def run(self, flag=True):
        self.server.send_msg('/n_run', self.node_id, int(flag)) # 12

    def run_msg(self, flag=True):
        return ('/n_run', self.node_id, int(flag)) # 12

    def map(self, *args):
        bundle = self.map_msg(*args)
        if isinstance(bundle[0], str):
            self.server.send_bundle(0, bundle) # BUG: timetag es opcional en liblo, tengo que implementar None para que lo evite
        else:
            self.server.send_bundle(0, *bundle) # BUG: ídem

    def map_msg(self, *args):
        kr_values = []
        ar_values = []
        result = []
        for control, bus in ut.gen_cclumps(args):
            bus = xxx.as_bus(bus) # BUG usa asBus que se implementa en Bus, Integer, Nil y Server.
            if bus.rate == 'control':
                kr_values.extend([
                    ug.as_control_input(control), # BUG: ug.as_control_input no está implementada, es como as_ugen_input
                    bus.index,
                    bus.num_channels
                ])
            elif bus.rate == 'audio':
                ar_values.extend([
                    ug.as_control_input(control), # BUG: ídem, además no entiendo porque tiene que ser un símbolo, de los contrario el mensaje no sería válido si un bus devuelve un entero por ejemplo?
                    bus.index,
                    bus.num_channels
                ])
            # // no default case, ignore others
        if len(kr_values) > 0:
            result.append(['/n_mapn', self.node_id] + kr_values)
        if len(ar_values) > 0:
            result.append(['/n_mapan', self.node_id] + ar_values)
        if len(result) < 2:
            result = ut.flatten(result)
        return result

    def mapn(self, *args):
        self.server.send_msg(
            '/n_mapn', # 48
            self.node_id,
            *ug.as_control_input(args)
        )

    def mapn_msg(self, *args):
        return ['/n_mapn', self.node_id]\
               + ug.as_control_input(list(args)) # 48

    def set(self, *args):
        self.server.send_msg(
            '/n_set', # 15
            self.node_id,
            xxx.as_osc_arg_list(list(args)) # BUG: asOSCArgArray no está implementada, viene desde object
        )

    def set_msg(self, *args):
        return ['/n_set', self.node_id]\
               + xxx.as_osc_arg_list(list(args)) # 15

    def setn(self, *args):
        self.server.send_msg(*self.setn_msg(*args))

    @classmethod
    def setn_msg_args(cls, *args):
        nargs = []
        args = ug.as_control_input(list(args)) # BUG: args es tupla, tengo que ver porque no están implementadas estas funciones.
        for control, more_vals in ut.gen_cclumps(args):
            if isinstance(more_vals, list): # BUG: ídem acá arriba, more_vals TIENE QUE SER LISTA
                nargs.extend([control, len(more_vals)] + more_vals)
            else:
                nargs.extend([control, 1, more_vals])
        return nargs

    def setn_msg(self, *args):
        return ['/n_setn', self.node_id] + Node.setn_msg_args(*args) # 16

    def fill(self, cname, num_controls, value, *args):
        self.server.send_msg(
            '/n_fill', self.node_id, # 17
            cname, num_controls, value,
            *ug.as_control_input(list(args))
        )

    def fill_msg(self, cname, num_controls, value, *args):
        return ['n_fill', self.node_id, cname, num_controls, value]\
               + ug.as_control_input(list(args)) # 17

    def release(self, release_time=None):
        self.server.send_msg(*self.release_msg(release_time))

    def release_msg(self, release_time=None):
        # // assumes a control called 'gate' in the synth
        if release_time is not None:
            if release_time <= 0:
                release_time = -1
            else:
                release_time = -(release_time + 1)
        else:
            release_time = 0
        return ['/n_set', self.node_id, 'gate', release_time] # 15

    def trace(self):
        self.server.send_msg('/n_trace', self.node_id) # 10

    def query(self, action):
        raise Exception('implementar Node:query con OSCFunc') # BUG
    def register(self):
        raise Exception('implementar Node:register con NodeWatcher') # BUG
    def unregister(self):
        raise Exception('implementar Node:unregister con NodeWatcher') # BUG
    def on_free(self, func):
        raise Exception('implementar Node:on_free con NodeWatcher y NotificationCenter') # BUG

    def wait_for_free(self):
        condition = _threading.Condition()
        def unhang():
            with condition:
                condition.notify()
        self.on_free(unhang)
        with condition:
            condition.wait()

    def move_before(self, node):
        self.group = node.group
        self.server.send_msg('/n_before', self.node_id, node.node_id) # 18

    def move_before_msg(self, node):
        self.group = node.group # TODO: estos msg podrían tener un parámetros update=True por defecto, pero no sé dónde se usan estas funciones aún.
        return ['/n_before', self.node_id, node.node_id] # 18

    def move_after(self, node):
        self.group = node.group
        self.server.send_msg('/n_after', self.node_id, node.node_id) # 19

    def move_after_msg(self, node):
        self.group = node.group
        return ['/n_after', self.node_id, node.node_id] # 19

    def move_to_head(self, group=None):
        group = group or self.server.default_group
        group.move_node_to_head(self) # se implementa en AbstractGroup

    def move_to_head_msg(self, group=None):
        group = group or self.server.default_group
        return group.move_node_to_head_msg(self) # se implementa en AbstractGroup

    def move_to_tail(self, group=None):
        group = group or self.server.default_group
        group.move_node_to_tail(self) # se implementa en AbstractGroup

    def move_to_tail_msg(self, group=None):
        group = group or self.server.default_group
        return group.move_node_to_tail_msg(self) # se implementa en AbstractGroup

    def order_nodes_msg(self, nodes):
        msg = ['/n_before'] # 18 # BUG: en sclang, 18 es '/n_before', el comentario está mal. Revisar todos los números.
        for first, to_move_after in ut.pairwise(nodes):
            msg.append(to_move_after.node_id)
            msg.append(first.node_id)
        return msg

    # TODO: VER:
    # ==
    # hash
    # printOn
    # asUGenInput # TODO: ver si va separado
    # asControlInput # TODO: ver si va separado


# // common base for Group and ParGroup classes
class AbstractGroup(Node):
    # TODO

    @staticmethod
    def creation_cmd():
        raise NotImplementedError()


class Group(AbstractGroup):
    @staticmethod
    def creation_cmd():
        return 21 # '/g_new'


class ParGroup(AbstractGroup):
    @staticmethod
	def creation_cmd():
        return 63 # '/p_new'


class Synth(Node):
    pass


class RootNode(Group):
    pass
