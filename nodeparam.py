"""Support for built in or extensions data types as Node parameters."""

# BUG: todos los Node heredan o reimplementan esta interfaz, sin tener
# NodeParameter de parent.

from supercollie.ugenparam import ugen_param


def node_param(obj):
    import supercollie.node as nod

    if isinstance(obj, (NodeParameter, nod.Node)):
        return obj
    new_cls = None
    for sub_class in NodeParameter.__subclasses__():
        if isinstance(obj, sub_class.param_type()):
            new_cls = sub_class
            break
    if new_cls is None:
        msg = "NodeParameter: type '{}' not supported"
        raise TypeError(msg.format(type(obj).__name__))
    return new_cls(obj)


class NodeParameter():
    def __init__(self, value):
        self._value = value

    # def __repr__(self):
    #     return "{}({})".format(type(self).__name__, repr(self.value))

    @property
    def value(self):
        return self._value

    @classmethod
    def param_type(cls):
        return (cls,)

    ### asTarget.sc interface ###

    def as_target(self):
        msg = "invalid value for Node target: '{}'"
        raise TypeError(msg.format(type(self.value).__name__))

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
        import supercollie.server as srv
        return srv.Server.default.default_group

    def as_osc_arg_list(self):
        return self.value


class NodeInt(NodeParameter):
    @classmethod
    def param_type(cls):
        return (int,)

    def as_target(self):
        import supercollie.node as nod
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
    # nunca usa este método (además de que no parece consistente).
    def as_osc_arg_bundle(self):
        raise Exeption('BUG: NodeString as_osc_arg_bundle') # BUG: TEST
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
