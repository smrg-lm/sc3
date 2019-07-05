"""Node.sc"""

import threading as _threading
import warnings as _warnings
from functools import singledispatch

from . import utils as utl
from . import ugens as ugn
from . import server as srv
from . import synthdesc as sdc
from . import graphparam as gpp


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
                    gpp.ugen_param(control).as_control_input(),
                    bus.index,
                    bus.num_channels
                ])
            elif bus.rate == 'audio':
                ar_values.extend([
                    gpp.ugen_param(control).as_control_input(), # BUG: no entiendo porque tiene que ser un símbolo, de los contrario el mensaje no sería válido si un bus devuelve un entero por ejemplo?
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
            *gpp.ugen_param(args).as_control_input()
        )

    def mapn_msg(self, *args):
        return ['/n_mapn', self.node_id]\
            + gpp.ugen_param(args).as_control_input() # 48

    def set(self, *args):
        self.server.send_msg(
            '/n_set', # 15
            self.node_id,
            *gpp.node_param(args).as_osc_arg_list()
        )

    def set_msg(self, *args):
        return ['/n_set', self.node_id]\
            + gpp.node_param(args).as_osc_arg_list() # 15

    def setn(self, *args):
        self.server.send_msg(*self.setn_msg(*args))

    @classmethod
    def setn_msg_args(cls, *args):
        nargs = []
        args = gpp.ugen_param(args).as_control_input()
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
            *gpp.ugen_param(args).as_control_input()
        )

    def fill_msg(self, cname, num_controls, value, *args):
        return ['n_fill', self.node_id, cname, num_controls, value]\
            + gpp.ugen_param(args).as_control_input() # 17

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

    # UGen graph parameter interface #
    # TODO: ver el resto en UGenParameter

    def as_ugen_input(self, *_):
        raise NotImplementedError('should not use a Node inside a SynthDef') # NOTE: dice esto pero implmente as_control_input, por qué?

    def as_control_input(self):
        return gpp.ugen_param(self.node_id).as_control_input()

    ### Node parameter interface ###

    def as_target(self):
        return self


# // common base for Group and ParGroup classes
class AbstractGroup(Node):
    # /** immediately sends **/
    def __init__(self, target=None, add_action='addToHead'):
        target = gpp.node_param(target).as_target()
        # BUG: revisar, estoy reemplazando la llamada a basic_new, que estaba mal...
        # BUG: basic_new lo único que hace se setear self -> server, node_id, group is_playing e is_running
        #server = target.server
        #group = cls.basic_new(server) # group es self, obj allá es self acá
        self.server = target.server
        self.node_id = self.server.next_node_id()
        add_action_id = type(self).add_actions[add_action]
        if add_action_id < 2:
            self.group = target
        else:
            self.group = target.group
        self.is_playing = False # BUG: me resulta raro, esto es así en basic_new, acá no sobreescribe, en rootnode setea a true
        self.is_running = False # BUG: me resulta raro, esto es así en basic_new, acá no sobreescribe, en rootnode setea a true
        self.server.send_msg(
            self.creation_cmd(), self.node_id,
            add_action_id, target.node_id
        )

    def new_msg(self, target=None, add_action='addToHead'):
        # // if target is nil set to default group of server specified when basicNew was called
        target = gpp.node_param(target).as_target()
        add_action_id = type(self).add_actions[add_action]
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
        return '/g_new' # 21


class ParGroup(AbstractGroup):
    @staticmethod
    def creation_cmd():
        return '/p_new' # 63


class RootNode(Group):
    roots = dict()

    def __init__(self, server=None):
        if server.name in type(self).roots:
            type(self).roots[server.name]
        else:
            # BUG: revisar, solo estoy reemplazando la llamada a basic_new, e integrando rinit
            #cls.basic_new(server, 0).rninit() # BUG: no entiendo por qué sclang llama con super, creo que es lo mismo, en Python es lo mismo
            self.server = server or srv.Server.default
            self.node_id = self.server.next_node_id()
            self.group = self
            self.is_playing = True # NOTE: a diferencia de los grupos comunes acá playling/running es true
            self.is_running = True
            type(self).roots[self.server.name] = self

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
            super(cls, rn).free_all() # NOTE: esto es un tanto complicado, llama al método de instancia definido en la superclass


class Synth(Node):
    # /** immediately sends **/
    def __init__(self, def_name, args=None, target=None, add_action='addToHead'):
        target = gpp.node_param(target).as_target()
        # BUG: revisar, estoy reemplazando la llamada a basic_new (que acá reimplementa además)
        # server = target.server
        # synth = cls.basic_new(def_name, server) # synth es self
        self.server = target.server
        self.node_id = self.server.next_node_id()
        add_action_id = type(self).add_actions[add_action]
        if add_action_id < 2:
            self.group = target
        else:
            self.group = target.group
        self.is_playing = False # BUG: me resulta raro, esto es así en basic_new, acá no sobreescribe, en rootnode setea a true
        self.is_running = False # BUG: me resulta raro, esto es así en basic_new, acá no sobreescribe, en rootnode setea a true
        self.def_name = def_name
        self.server.send_msg(
            '/s_new', # 9
            self.def_name, self.node_id,
            add_action_id, target.node_id,
            *gpp.node_param(args or []).as_osc_arg_list()
        )

    # // does not send (used for bundling)
    @classmethod
    def basic_new(cls, def_name, server=None, node_id=None):
        obj = super().basic_new(server, node_id)
        obj.def_name = def_name
        return obj

    @classmethod
    def new_paused(cls, def_name, args=None, target=None, add_action='addToHead'):
        target = gpp.node_param(target).as_target()
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
                *gpp.node_param(args or []).as_osc_arg_list()
            ],
            [
                '/n_run', # 12
                synth.node_id, 0
            ]
        )
        return synth

    @classmethod
    def new_replace(cls, node_to_replace, def_name, args=None, same_id=False): # BUG: renombrado porque no pueden haber métodos de instancia y clase con el mismo nombre.
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
            *gpp.node_param(args or []).as_osc_arg_list()
        )
        return synth

    # node_id -1
    @classmethod # TODO: este tal vez debería ir arriba
    def grain(cls, def_name, args=None, target=None, add_action='addToHead'):
        target = gpp.node_param(target).as_target()
        server = target.server
        server.send_msg(
            '/s_new', # 9
            def_name.as_def_name(), -1, # BUG: as_def_name no está implementado puede ser método de Object
            cls.add_actions[add_action], target.node_id,
            *gpp.node_param(args or []).as_osc_arg_list()
        )

    def new_msg(self, target=None, args=None, add_action='addToHead'):
        add_action_id = self.add_actions[add_action]
        target = gpp.node_param(target).as_target()
        if add_action_id < 2:
            self.group = target
        else:
            self.group = target.group
        return ['/s_new', self.def_name, self.node_id, add_action_id,
                target.node_id, *gpp.node_param(args or []).as_osc_arg_list()] # 9

    @classmethod
    def after(cls, node, def_name, args=None):
        return cls(def_name, args or [], node, 'addAfter')

    @classmethod
    def before(cls, node, def_name, args=None):
        return cls(def_name, args or [], node, 'addBefore')

    @classmethod
    def head(cls, group, def_name, args=None):
        return cls(def_name, args or [], group, 'addToHead')

    @classmethod
    def tail(cls, group, def_name, args=None):
        return cls(def_name, args or [], group, 'addToTail')

    def replace(self, def_name, args=None, same_id=False):
        return type(self).new_replace(self, def_name, args or [], same_id)

    # // for bundling
    def add_to_head_msg(self, group, args):
        # // if aGroup is nil set to default group of server specified when basicNew was called
        if group is not None:
            self.group = group
        else:
            self.group = self.server.default_group
        return ['/s_new', self.def_name, self.node_id, 0,
                self.group.node_id, *gpp.node_param(args).as_osc_arg_list()] # 9

    def add_to_tail_msg(self, group, args):
        # // if aGroup is nil set to default group of server specified when basicNew was called
        if group is not None:
            self.group = group
        else:
            self.group = self.server.default_group
        return ['/s_new', self.def_name, self.node_id, 1,
                self.group.node_id, *gpp.node_param(args).as_osc_arg_list()] # 9

    def add_after_msg(self, node, args=None):
        self.group = node.group
        return ['/s_new', self.def_name, self.node_id, 3,
                node.node_id, *gpp.node_param(args or []).as_osc_arg_list()] # 9

    def add_before_msg(self, node, args=None):
        self.group = node.group
        return ['/s_new', self.def_name, self.node_id, 2,
                node.node_id, *gpp.node_param(args or []).as_osc_arg_list()] # 9

    def add_replace_msg(self, node_to_replace, args):
        self.group = node_to_replace.group
        return ['/s_new', self.def_name, self.node_id, 4,
                node_to_replace.node_id, *gpp.node_param(args).as_osc_arg_list()] # 9

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
        synth_desc = sdc.SynthDescLib.at(self.def_name)
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
            *gpp.node_param(osc_msg).as_osc_arg_list()
        )

    # TODO, VER
    #printOn





### extConvertToOSC.sc ###

# // The following interface in an optimized version of asControlInput that
# // flattens arrayed values and marks the outermost array of a value with $[ and $]
# // These Chars are turning into typetags ([ and ]) in the OSC message to mark that array
# // Inner arrays are flattened (they are not meaningful in the server context)
# // This makes it possible to write Synth("test", [0, [[100,200,300], [0.1,0.2,0.3], [10,20,30]] ])
# // and have all the arguments be assigned to consecutive controls in the synth.


# as_osc_arg_list

# @singledispatch
# def as_osc_arg_list(obj): # NOTE: incluye Env, ver @as_control_input.register(Env), tengo que ver la clase Ref que es una AbstractFunction
#     return gpp.ugen_param(obj).as_control_input()


# @as_osc_arg_list.register(str)
# @as_osc_arg_list.register(type(None))
# def _(obj):
#     return obj


# @as_osc_arg_list.register(tuple)
# @as_osc_arg_list.register(list)
# def _(obj):
#     lst = []
#     for e in obj:
#         #lst.append(as_osc_arg_embedded_list(e, lst)) # NOTE: estaba mal, pero ver por qué crea elipsis!
#         as_osc_arg_embedded_list(e, lst)
#     return lst


# as_osc_arg_embedded_list

# @singledispatch
# def as_osc_arg_embedded_list(obj, lst): # NOTE: incluye None, tengo que ver la clase Ref que es una AbstractFunction
#     lst.append(gpp.ugen_param(obj).as_control_input())
#     return lst


# class Env():
#     print('+ forward declaration of Env in node.py')


# @as_osc_arg_embedded_list.register(Env)
# def _(obj, lst):
#     env_lst = gpp.ugen_param(obj).as_control_input()
#     return as_osc_arg_embedded_list(env_lst, lst)


# @as_osc_arg_embedded_list.register(str)
# def _(obj, lst):
#     lst.append(obj)
#     return lst


# @as_osc_arg_embedded_list.register(tuple)
# @as_osc_arg_embedded_list.register(list)
# def _(obj, lst):
#     lst.append('[')
#     for e in obj:
#         #lst.append(as_osc_arg_embedded_list(e, lst)) # NOTE: estaba mal, pero ver por qué crea elipsis!
#         as_osc_arg_embedded_list(e, lst)
#     lst.append(']')
#     return lst


# as_osc_arg_bundle

# @singledispatch
# def as_osc_arg_bundle(obj): # NOTE: incluye None y Env, tengo que ver la clase Ref que es una AbstractFunction
#     return gpp.ugen_param(obj).as_control_input()
#
#
# @as_osc_arg_bundle.register(str)
# @as_osc_arg_bundle.register(tuple)
# @as_osc_arg_bundle.register(list)
# def _(obj):
#     lst = []
#     for e in obj:
#         lst.append(as_osc_arg_list(e))
#     return lst
