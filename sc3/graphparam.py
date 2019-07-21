"""Support for built in or extensions data types as UGen/Node parameters."""

from math import isnan
import struct

from . import server as srv

# BUG: están dentro de las funciones, no se pueden importar
# BUG: por los símbolos de herencia en relación a UGen.
# from . import ugen as ugn
# from . import node as nod


def graph_param(obj, param_cls):
    if isinstance(obj, GraphParameter):
        obj = obj.value
    new_cls = None
    for sub_class in param_cls.__subclasses__():
        if isinstance(obj, sub_class.param_type()):
            new_cls = sub_class
            break
    if new_cls is None:
        raise TypeError(
            f"{param_cls.__name__}: type '{type(obj).__name__}' not supported")
    return new_cls(obj)


def ugen_param(obj):
    from . import ugen as ugn

    if isinstance(obj, (UGenParameter, ugn.UGen)):
        return obj
    return graph_param(obj, UGenParameter)


def node_param(obj):
    from . import node as nod

    if isinstance(obj, (NodeParameter, nod.Node)):
        return obj
    return graph_param(obj, NodeParameter)


### Graphs Parameter Base Class ###

class GraphParameter():
    def __init__(self, value):
        self.__value = value

    # def __repr__(self):
    #     return "{}({})".format(type(self).__name__, repr(self.value))

    @property
    def value(self): # TODO: tal vez sería mejor que se llame param_value
        return self.__value

    @classmethod
    def param_type(cls):
        return (cls,)


### UGen graph parameter interface ###

# BUG: todos las UGen heredan o reimplementan esta interfaz, sin tener
# UGenParameter de parent.

class UGenParameter(GraphParameter):
    def is_valid_ugen_input(self):
        return False

    def as_ugen_input(self, *_):
        return self.value

    def as_control_input(self):
        return self.value

    def as_audio_rate_input(self):
        if self.as_ugen_rate() != 'audio':
            return xxx.K2A.ar(self.value)
        else:
            return self.value

    def as_ugen_rate(self):
        try:
            return self.rate
        except AttributeError as e:
            raise AttributeError(
                f"'{type(self).__name__}' must implement "
                "rate attribute or as_ugen_rate method") from e

    def perform_binary_op_on_ugen(self, selector, thing):
        if selector == '==':
            return False
        if selector == '!=':
            return True
        raise ValueError(
            f"operations between ugens and '{self.value}' are not supported")

    def write_input_spec(self, file, synthdef):
        raise NotImplementedError(
            f"'{type(self).__name__}' does not implement write_input_spec")


class UGenNone(UGenParameter):
    @classmethod
    def param_type(cls):
        return (type(None),)

    def as_ugen_rate(self):
        return None


class UGenString(UGenParameter):
    @classmethod
    def param_type(cls):
        return (str,)

    def as_ugen_rate(self):
        return 'scalar'


class UGenScalar(UGenParameter):
    @classmethod
    def param_type(cls):
        return (int, float, bool)

    def is_valid_ugen_input(self):
        return not isnan(self.value)

    def as_audio_rate_input(self):
        if self.value == 0:
            return xxx.Silent.ar()
        else:
            return xxx.DC.ar(self.value)

    def as_ugen_rate(self):
        return 'scalar'

    def write_input_spec(self, file, synthdef):
        try:
            const_index = synthdef.constants[float(self.value)]
            file.write(struct.pack('>i', -1)) # putInt32
            file.write(struct.pack('>i', const_index)) # putInt32
        except KeyError as e:
            raise Exception(
                'write_input_spec constant not found: '
                f'{float(self.value)}') from e


class UGenList(UGenParameter):
    @classmethod
    def param_type(cls):
        return (list, tuple)  # *** BUG: tuple evita la expansión multicanal, eso lo define el constructor de ChannelList. Acá es correcto porque estas clases se usan temporalmente para acceder al polimofismo.

    # BUG: array implementa num_channels?

    def is_valid_ugen_input(self):
        return True if self.value else False  # *** BUG: en sclang, debería comprobar isEmpty porque tira error en SynthDesc (SinOsc.ar() * []). O tal vez cuando construye BinaryOpUGen? Ver el grafo generado, tal vez deba ser None.

    def as_ugen_input(self, *ugen_cls):
        lst = list(map(lambda x: ugen_param(x).as_ugen_input(*ugen_cls), self.value))
        return lst

    def as_control_input(self):
        return [ugen_param(x).as_control_input() for x in self.value]

    def as_audio_rate_input(self, *ugen_cls):
        lst = list(map(lambda x: ugen_param(x).as_audio_rate_input(*ugen_cls), self.value)) # NOTE: de Array: ^this.collect(_.asAudioRateInput(for))
        return lst

    def as_ugen_rate(self):
        if len(self.value) == 1:
            return ugen_param(self.value[0]).as_ugen_rate() # NOTE: en SequenceableCollection si this.size es 1 devuelve this.first.rate
        lst = [ugen_param(x).as_ugen_rate() for x in self.value]
        if not lst or any(x is None for x in lst): # TODO: reduce con Collection minItem, los símbolos por orden lexicográfico, si algún elemento es nil devuelve nil !!!
            return None
        return min(lst)

    def write_input_spec(self, file, synthdef):
        for item in self.value:
            ugen_param(item).write_input_spec(file, synthdef)


### asTarget.sc interface ###
### Node Graph Parameters ###

# BUG: todos los Node heredan o reimplementan esta interfaz, sin tener
# NodeParameter de parent.

class NodeParameter(GraphParameter):
    ### Node parameter interface ###

    def as_target(self):
        raise TypeError(
            f"invalid value for Node target: '{type(self.value).__name__}'")

    # BUG IMPORTANTE: VER EL VERDADERO SIGNIFICADO DE LA VIDA DE AS_CONTROL_INPUT.
    # BUG IMPORTANTE: VER LAS NOTAS EN EL TIPO DE EVENTO GRAIN EN event.py.
    # BUG IMPORTANTE: **** Podría llamarse as_osc_arg_control_input, para ser
    # BUG IMPORTANTE: coherente con la interfaz de abajo dejando claro que se
    # BUG IMPORTANTE: aplica a nodos (mensajes osc) aunque sea lo mismo que
    # BUG IMPORTANTE: as_control_input de las UGens. Así quedan más explícitos
    # BUG IMPORTANTE: los tipos de datos posibles **** Lo que no tengo claro es
    # BUG IMPORTANTE: si "control" refiere a señal kr o data para Control ugens,
    # BUG IMPORTANTE: es este caso serían tipos osc permitidos.
    def as_control_input(self):
        return ugen_param(self).as_control_input()

    ### extConvertToOSC.sc interface ###

    # // The following interface in an optimized version of asControlInput that
    # // flattens arrayed values and marks the outermost array of a value with $[ and $]
    # // These Chars are turning into typetags ([ and ]) in the OSC message to mark that array
    # // Inner arrays are flattened (they are not meaningful in the server context)
    # // This makes it possible to write Synth("test", [0, [[100,200,300], [0.1,0.2,0.3], [10,20,30]] ])
    # // and have all the arguments be assigned to consecutive controls in the synth.

    def as_osc_arg_list(self): # NOTE: incluye Env, ver @as_control_input.register(Env), tengo que ver la clase Ref que es una AbstractFunction
        return ugen_param(self).as_control_input()

    def as_osc_arg_embedded_list(self, lst): # NOTE: incluye None, tengo que ver la clase Ref que es una AbstractFunction
        lst.append(ugen_param(self).as_control_input())
        return lst

    def as_osc_arg_bundle(self): # NOTE: incluye None y Env, tengo que ver la clase Ref que es una AbstractFunction
        return ugen_param(self).as_control_input()


class NodeNone(NodeParameter):
    @classmethod
    def param_type(cls):
        return (type(None),)

    def as_target(self):
        return srv.Server.default.default_group

    def as_osc_arg_list(self):
        return self.value


class NodeScalar(NodeParameter):
    @classmethod
    def param_type(cls):
        return (int, float)

    def as_target(self):
        from . import node as nod
        return nod.Group.basic_new(srv.Server.default, obj)


class NodeString(NodeParameter):
    @classmethod
    def param_type(cls):
        return (str,)

    def as_osc_arg_list(self):
        return self.value

    def as_osc_arg_embedded_list(self, lst):
        lst.append(self.value)
        return lst

    # NOTE: porque hereda de RawArray que hereda de SequenceableCollection
    # le correspondería la misma implementación de NodeList, pero creo que
    # el único método que llama a este es as_osc_arg_embedded_list que
    # String sobreescribe de manera distinta por lo que supongo que nunca
    # usa este método (además de que no parece consistente).
    def as_osc_arg_bundle(self):
        raise Exeption('BUG: NodeString as_osc_arg_bundle') # *** BUG: TEST
        lst = []
        for e in self.value:
            lst.append(node_param(e).as_osc_arg_list())
        return lst


class NodeList(NodeParameter):
    @classmethod
    def param_type(cls):
        return (list, tuple)

    def as_osc_arg_list(self):
        lst = []
        for e in self.value:
            node_param(e).as_osc_arg_embedded_list(lst)
        return lst

    def as_osc_arg_embedded_list(self, lst):
        lst.append('[')
        for e in self.value:
            #lst.append(as_osc_arg_embedded_list(e, lst)) # NOTE: estaba mal, pero ver por qué crea elipsis!
            node_param(e).as_osc_arg_embedded_list(lst)
        lst.append(']')
        return lst

    def as_osc_arg_bundle(self):
        lst = []
        for e in self.value:
            lst.append(node_param(e).as_osc_arg_list())
        return lst


# # NOTE: se usa solo para clases de JITlib
# ### as_node_id ###
# @singledispatch
# def as_node_id(obj):
#     msg = "invalid value for Node node id: '{}'"
#     raise TypeError(msg.format(type(obj).__name__))
# @as_node_id.register(int)
# @as_node_id.register(type(None))
# def _(obj):
#     return obj
# @as_node_id.register(srv.Server)
# def _(obj):
#     return 0
# @as_node_id.register(Node)
# def _(obj):
#     return obj.node_id
