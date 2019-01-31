"""Node.sc"""

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

    # TODO: sigue...


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
