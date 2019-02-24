"""Node.sc"""

import threading as _threading
import warnings as _warnings
from functools import singledispatch

import supercollie.utils as utl
from . import ugens as ugn
from . import server as srv # es cíclico con sí mismo a través de node
import supercollie.synthdesc as dsc

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
        obj.server = server or srv.Server.default
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
        for control, bus in utl.gen_cclumps(args, 2):
            bus = xxx.as_bus(bus) # BUG usa asBus que se implementa en Bus, Integer, Nil y Server.
            if bus.rate == 'control':
                kr_values.extend([
                    ugn.as_control_input(control), # BUG: ugn.as_control_input no está implementada, es como as_ugen_input
                    bus.index,
                    bus.num_channels
                ])
            elif bus.rate == 'audio':
                ar_values.extend([
                    ugn.as_control_input(control), # BUG: ídem, además no entiendo porque tiene que ser un símbolo, de los contrario el mensaje no sería válido si un bus devuelve un entero por ejemplo?
                    bus.index,
                    bus.num_channels
                ])
            # // no default case, ignore others
        if len(kr_values) > 0:
            result.append(['/n_mapn', self.node_id] + kr_values)
        if len(ar_values) > 0:
            result.append(['/n_mapan', self.node_id] + ar_values)
        if len(result) < 2:
            result = utl.flatten(result)
        return result

    def mapn(self, *args):
        self.server.send_msg(
            '/n_mapn', # 48
            self.node_id,
            *ugn.as_control_input(args)
        )

    def mapn_msg(self, *args):
        return ['/n_mapn', self.node_id]\
            + ugn.as_control_input(list(args)) # 48

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
        args = ugn.as_control_input(list(args)) # BUG: args es tupla, tengo que ver porque no están implementadas estas funciones.
        for control, more_vals in utl.gen_cclumps(args, 2):
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
            *ugn.as_control_input(list(args))
        )

    def fill_msg(self, cname, num_controls, value, *args):
        return ['n_fill', self.node_id, cname, num_controls, value]\
            + ugn.as_control_input(list(args)) # 17

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
        for first, to_move_after in utl.pairwise(nodes):
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
    # /** immediately sends **/
    def __init__(cls, target=None, add_action='addToHead'):
        target = as_target(target)
        server = target.server
        group = cls.basic_new(server)
        add_action_id = cls.add_actions[add_action]
        if add_action_id < 2:
            group.group = target
        else:
            group.group = target.group
        group.server.send_msg(
            cls.creation_cmd(), group.node_id,
            add_action_id, target.node_id
        )
        return group

    def new_msg(self, target=None, add_action='addToHead'):
        # // if target is nil set to default group of server specified when basicNew was called
        target = as_target(target) # BUG: acá es un caso de asTarget sobre Nil
        add_action_id = self.add_actions[add_action]
        if add_action_id < 2:
            self.group = target
        else:
            self.group = target.group
        return [self.creation_cmd(), self.node_id,
                add_action_id, target.node_id]

    # // for bundling
    def add_to_head_msg(self, group=None):
        # // if group is nil set to default group of server specified when basicNew was called
        self.group = group or self.server.default_group
        return [self.creation_cmd(), self.node_id, 0, self.group.node_id]

    def add_to_tail_msg(self, group=None):
        # // if group is nil set to default group of server specified when basicNew was called
        self.group = group or self.server.default_group
        return [self.creation_cmd(), self.node_id, 1, self.group.node_id]

    def add_after_msg(self, node):
        self.group = node.group
        return [self.creation_cmd(), self.node_id, 3, self.group.node_id]

    def add_before_msg(self, node):
        self.group = node.group
        return [self.creation_cmd(), self.node_id, 2, self.group.node_id]

    def add_replace_msg(self, node_to_replace):
        self.group = node_to_replace.group
        return [self.creation_cmd(), self.node_id, 4, node_to_replace.node_id]

    @classmethod
    def after(cls, node):
        return cls(node, 'addAfter')
    @classmethod
    def before(cls, node):
        return cls(node, 'addBefore')
    @classmethod
    def head(cls, group):
        return cls(group, 'addToHead')
    @classmethod
    def tail(cls, group):
        return cls(group, 'addToTail')
    @classmethod
    def replace(cls, node_to_replace):
        return cls(node_to_replace, 'addReplace')

    # // move Nodes to this group

    def move_node_to_head(self, node):
        node.group = self
        self.server.send_msg('/g_head', self.node_id, node.node_id) # 22

    def move_node_to_head_msg(self, node):
        node.group = self
        return ['/g_head', self.node_id, node.node_id] # 22

    def move_node_to_tail(self, node):
        node.group = self
        self.server.send_msg('/g_tail', self.node_id, node.node_id) # 23

    def move_node_to_tail_msg(self, node):
        node.group = self
        return ['/g_tail', self.node_id, node.node_id] # 23

    def free_all(self):
        # // free my children, but this node is still playing
        self.server.send_msg('/g_freeAll', self.node_id) # 24

    def free_all_msg(self):
        # // free my children, but this node is still playing
        return ['/g_freeAll', self.node_id] # 24

    def deep_free(self):
        self.server.send_msg('/g_deepFree', self.node_id) # 50

    def deep_free_msg(self):
        return ['/g_deepFree', self.node_id] # 50

    # // Introspection

    def dump_tree(self, post_controls=False):
        self.server.send_msg('/g_dumpTree', self.node_id, int(post_controls))

    def query_tree(self):
        raise Exception('implementar AbstractGroup:query_tree con OSCFunc y SystemClock') # BUG

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


class RootNode(Group):
    roots = dict()

    def __init__(cls, server):
        server = server or srv.Server.default
        if server.name in cls.roots:
            return cls.roots[server.name]
        else:
            return cls.basic_new(server, 0).rninit() # BUG: no entiendo por qué sclang llama con super, creo que es lo mismo, en Python es lo mismo

    def rninit(self):
        self.roots[self.server.name] = self
        self.is_playing = self.is_running = True
        self.group = self

    def run(self):
        _warnings.warn('run has no effect on RootNode')
    def free(self):
        _warnings.warn('free has no effect on RootNode')
    def move_before(self):
        _warnings.warn('moveBefore has no effect on RootNode')
    def move_after(self):
        _warnings.warn('move_after has no effect on RootNode')
    def move_to_head(self):
        _warnings.warn('move_to_head has no effect on RootNode')
    def move_to_tail(self):
        _warnings.warn('move_to_tail has no effect on RootNode')

    @classmethod
    def free_all(cls):
        for rn in cls.roots.values():
            rn.free_all()


class Synth(Node):
    # /** immediately sends **/
    def __init__(cls, def_name, args=[], target=None, add_action='addToHead'):
        target = as_target(target)
        server = target.server
        add_action_id = cls.add_actions[add_action]
        synth = cls.basic_new(def_name, server)
        if add_action_id < 2:
            synth.group = target
        else:
            synth.group = target.group
        synth.server.send_msg(
            '/s_new', # 9
            synth.def_name, synth.node_id,
            add_action_id, target.node_id,
            *xxx.as_osc_arg_list(args)
        )
        return synth

    # // does not send (used for bundling)
    @classmethod
    def basic_new(cls, def_name, server, node_id):
        obj = super().basic_new(server, node_id)
        obj.def_name = def_name
        return obj

    @classmethod
    def new_paused(cls, def_name, args=[], target=None, add_action='addToHead'):
        target = as_target(target)
        server = target.server
        add_action_id = cls.add_actions[add_action]
        synth = cls.basic_new(def_name, server)
        if add_action_id < 2:
            synth.group = target
        else:
            synth.group = target.group
        synth.server.send_bundle(
            0,
            [
                '/s_new', # 9
                synth.def_name, synth.node_id,
                add_action_id, target.node_id,
                *xxx.as_osc_arg_list(args)
            ],
            [
                '/n_run', # 12
                synth.node_id, 0
            ]
        )
        return synth

    @classmethod
    def new_replace(cls, node_to_replace, def_name, args=[], same_id=False): # BUG: renombrado porque no pueden haber métodos de instancia y clase con el mismo nombre.
        if same_id:
            new_node_id = node_to_replace.node_id
        else:
            new_node_id = None
        server = node_to_replace.server
        synth = cls.basic_new(def_name, server, new_node_id)
        synth.server.send_msg(
            '/s_new', # 9
            synth.def_name, synth.node_id,
            4, node_to_replace.node_id, # 4 -> 'addReplace'
            *xxx.as_osc_arg_list(args)
        )
        return synth

    # node_id -1
    @classmethod # TODO: este tal vez debería ir arriba
    def grain(cls, def_name, args=[], target=None, add_action='addToHead'):
        target = as_target(target)
        server = target.server
        server.send_msg(
            '/s_new', # 9
            def_name.as_def_name(), -1, # BUG: as_def_name no está implementado puede ser método de Object
            cls.add_actions[add_action], target.node_id,
            *xxx.as_osc_arg_list(args)
        )

    def new_msg(self, target=None, args=[], add_action='addToHead'):
        add_action_id = self.add_actions[add_action]
        target = as_target(target)
        if add_action_id < 2:
            self.group = target
        else:
            self.group = target.group
        return ['/s_new', self.def_name, self.node_id, add_action_id,
                target.node_id, *xxx.as_osc_arg_list(args)] # 9

    @classmethod
    def after(cls, node, def_name, args=[]):
        return cls(def_name, args, node, 'addAfter')
    @classmethod
    def before(cls, node, def_name, args=[]):
        return cls(def_name, args, node, 'addBefore')
    @classmethod
    def head(cls, group, def_name, args=[]):
        return cls(def_name, args, group, 'addToHead')
    @classmethod
    def tail(cls, group, def_name, args=[]):
        return cls(def_name, args, group, 'addToTail')

    def replace(self, def_name, args=[], same_id=False):
        return type(self).new_replace(self, def_name, args, same_id)

    # // for bundling
    def add_to_head_msg(self, group, args):
        # // if aGroup is nil set to default group of server specified when basicNew was called
        if group is not None:
            self.group = group
        else:
            self.group = self.server.default_group
        return ['/s_new', self.def_name, self.node_id, 0,
                self.group.node_id, *xxx.as_osc_arg_list(args)] # 9

    def add_to_tail_msg(self, group, args):
        # // if aGroup is nil set to default group of server specified when basicNew was called
        if group is not None:
            self.group = group
        else:
            self.group = self.server.default_group
        return ['/s_new', self.def_name, self.node_id, 1,
                self.group.node_id, *xxx.as_osc_arg_list(args)] # 9

    def add_after_msg(self, node, args=[]):
        self.group = node.group
        return ['/s_new', self.def_name, self.node_id, 3,
                node.node_id, *xxx.as_osc_arg_list(args)] # 9

    def add_before_msg(self, node, args=[]):
        self.group = node.group
        return ['/s_new', self.def_name, self.node_id, 2,
                node.node_id, *xxx.as_osc_arg_list(args)] # 9

    def add_replace_msg(self, node_to_replace, args):
        self.group = node_to_replace.group
        return ['/s_new', self.def_name, self.node_id, 4,
                node_to_replace.node_id, *xxx.as_osc_arg_list(args)] # 9

    def get(self, index, action):
        raise Exception('implementar Synth:get con OSCFunc') # BUG

    def get_msg(self, index):
        return ['/s_get', self.node_id, index] # 44

    def getn(self, index, count, action):
        raise Exception('implementar Synth:getn con OSCFunc') # BUG

    def getn_msg(self, index, count):
        return ['/s_getn', self.node_id, index, count] # 45

    def seti(self, *args): # // args are [key, index, value, key, index, value ...]
        osc_msg = []
        synth_desc = dsc.SynthDescLib.at(self.def_name)
        if synth_desc is None:
            msg = 'message seti failed, because SynthDef {} was not added'
            _warnings.warn(msg.format(self.def_name))
            return
        for key, offset, value in utl.gen_cclumps(args, 3):
            if key in synth_desc.control_dict:
                cname = synth_desc.control_dict[key]
                if offset < cname.num_channels:
                    osc_msg.append(cname.index + offset)
                    if isinstance(value, list):
                        osc_msg.append(value[:cname.num_channels - offset]) # keep
                    else:
                        osc_msg.append(value)
        self.server.send_msg(
            '/n_set', self.node_id,
            *xxx.as_osc_arg_list(osc_msg)
        )

    # TODO, VER
    #printOn


### asTarget.sc ###


# as_target

@singledispatch
def as_target(obj):
    msg = "invalid value for Node target: '{}'"
    raise TypeError(msg.format(type(obj).__name__))


@as_target.register(int)
def _(obj):
    return Group.basic_new(srv.Server.default, obj)


@as_target.register(type(None))
def _(obj):
    return srv.Server.default.default_group


class Server():
    print('+ fordward declaration of Server in node.py')


@as_target.register(Server)
def _(obj):
    return obj.default_group


@as_target.register(Node)
def _(obj):
    return obj


# # NOTE: se usa solo para clases de JITlib
# ### as_node_id ###
#
# @singledispatch
# def as_node_id(obj):
#     msg = "invalid value for Node node id: '{}'"
#     raise TypeError(msg.format(type(obj).__name__))
#
#
# @as_node_id.register(int)
# @as_node_id.register(type(None))
# def _(obj):
#     return obj
#
#
# @as_node_id.register(srv.Server)
# def _(obj):
#     return 0
#
#
# @as_node_id.register(Node)
# def _(obj):
#     return obj.node_id


### extConvertToOSC.sc ###

# // The following interface in an optimized version of asControlInput that
# // flattens arrayed values and marks the outermost array of a value with $[ and $]
# // These Chars are turning into typetags ([ and ]) in the OSC message to mark that array
# // Inner arrays are flattened (they are not meaningful in the server context)
# // This makes it possible to write Synth("test", [0, [[100,200,300], [0.1,0.2,0.3], [10,20,30]] ])
# // and have all the arguments be assigned to consecutive controls in the synth.


# as_osc_arg_list

@singledispatch
def as_osc_arg_list(obj): # NOTE: incluye Env, ver @as_control_input.register(Env), tengo que ver la clase Ref que es una AbstractFunction
    return ugn.as_control_input(obj)


@as_osc_arg_list.register(str)
@as_osc_arg_list.register(type(None))
def _(obj):
    return obj


@as_osc_arg_list.register(tuple)
@as_osc_arg_list.register(list)
def _(obj):
    arr = []
    for e in obj:
        arr.append(as_osc_arg_embedded_list(e, arr))
    return arr


# as_osc_arg_embedded_list

@singledispatch
def as_osc_arg_embedded_list(obj, arr): # NOTE: incluye None, tengo que ver la clase Ref que es una AbstractFunction
    arr.append(as_control_input(obj))
    return arr


class Env():
    print('+ fordward declaration of Env in node.py')


@as_osc_arg_embedded_list.register(Env)
def _(obj, arr):
    env_arr = ugn.as_control_input(obj)
    return as_osc_arg_embedded_list(env_arr, arr)


@as_osc_arg_embedded_list.register(str)
def _(obj, arr):
    arr.append(obj)
    return arr


@as_osc_arg_embedded_list.register(tuple)
@as_osc_arg_embedded_list.register(list)
def _(obj, arr):
    arr.append('[')
    for e in obj:
        arr.append(as_osc_arg_embedded_list(e, arr))
    arr.append(']')
    return arr


# as_osc_arg_bundle

@singledispatch
def as_osc_arg_bundle(obj): # NOTE: incluye None y Env, tengo que ver la clase Ref que es una AbstractFunction
    return ugn.as_control_input(obj)


@as_osc_arg_bundle.register(str)
@as_osc_arg_bundle.register(tuple)
@as_osc_arg_bundle.register(list)
def _(obj):
    arr = []
    for e in obj:
        arr.append(as_osc_arg_list(e))
    return arr
