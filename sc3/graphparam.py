"""
Support for built in or extensions data types as UGen or Node parameters. This
module is an internal interface. To extend type support classes inherit either
from UGenParameter or NodeParameter or both, define _param_type() for the
extending type and override the needed interface methods.

UGenParameter are values intended for UGens parameters. NodeParameter are values
intended for Node messages. UGen, Node, SynthDef and SynthDescLib classes make
use of this interface to prepare data in the right format. This functionality
shoudln't be exposed to the user interface, supported data types must just work
with its own interface.
"""

from math import isnan
import struct

from . import server as srv
from . import _specialindex as _si
from . import utils as utl


### Graphs Parameter Base Class ###

class GraphParameter():
    def __init__(self, value):
        self.__param_value = value

    @property
    def _param_value(self):
        return self.__param_value

    @classmethod
    def _param_type(cls):
        return (cls,)

    def __repr__(self):
        return f'{type(self).__name__}({repr(self._param_value)})'


### UGen graph parameter interface ###

class UGenParameter(GraphParameter):
    def _is_valid_ugen_input(self):
        return False

    def _as_ugen_input(self, *_):
        return self._param_value

    def _as_audio_rate_input(self):
        if self._as_ugen_rate() != 'audio':
            return xxx.K2A.ar(self._param_value)
        else:
            return self._param_value

    @property
    def rate(self):
        # NOTE: Convenience for polimorfism, use _as_ugen_rate. TODO: check if used, it shouldn't, remove later.
        print('*** ERROR: should not call UGenParameter.rate')
        return self._as_ugen_rate()

    def _as_ugen_rate(self):  # Was rate for many non UGen objects in sclang.
        try:
            return self.rate
        except AttributeError as e:
            raise AttributeError(f'{type(self).__name__} does not implement '
                                 'rate attribute or _as_ugen_rate method') from e

    def _perform_binary_op_on_ugen(self, selector, ugen):
        selector = _si.sc_opname(selector.__name__)
        raise TypeError(f"operation '{selector}' is not supported between "
                        f"UGen and {type(self._param_value).__name__}")

    def _r_perform_binary_op_on_ugen(self, selector, ugen):
        selector = _si.sc_opname(selector.__name__)
        raise TypeError(f"operation '{selector}' is not supported between "
                        f"{type(self._param_value).__name__} and UGen")

    def _write_input_spec(self, file, synthdef):
        raise NotImplementedError(f'{type(self).__name__} does '
                                  'not implement _write_input_spec()')


class UGenNone(UGenParameter):
    @classmethod
    def _param_type(cls):
        return (type(None),)

    def _as_ugen_rate(self):
        return None


class UGenString(UGenParameter):
    @classmethod
    def _param_type(cls):
        return (str,)

    def _as_ugen_rate(self):
        return 'scalar'


class UGenScalar(UGenParameter):
    @classmethod
    def _param_type(cls):
        return (int, float, bool)

    def _is_valid_ugen_input(self):
        return not isnan(self._param_value)

    def _as_audio_rate_input(self):
        if self._param_value == 0:
            return xxx.Silent.ar()
        else:
            return xxx.DC.ar(self._param_value)

    def _as_ugen_rate(self):
        return 'scalar'

    def _write_input_spec(self, file, synthdef):
        try:
            const_index = synthdef.constants[float(self._param_value)]
            file.write(struct.pack('>i', -1))  # putInt32
            file.write(struct.pack('>i', const_index))  # putInt32
        except KeyError as e:
            raise Exception(
                '_write_input_spec constant not found: '
                f'{float(self._param_value)}') from e


class UGenSequence(UGenParameter):
    @classmethod
    def _param_type(cls):
        # tuple prevents multichannel expansion,
        # type must be kept for UGen inputs.
        return (list, tuple)

    def _is_valid_ugen_input(self):
        return True if self._param_value else False  # *** BUG: en sclang, debería comprobar isEmpty porque tira error en SynthDesc (SinOsc.ar() * []). O tal vez cuando construye BinaryOpUGen? Ver el grafo generado, tal vez deba ser None.

    def _as_ugen_input(self, *ugen_cls):
        m = map(lambda x: ugen_param(x)._as_ugen_input(*ugen_cls),
                self._param_value)
        return type(self._param_value)(m)

    def _as_audio_rate_input(self, *ugen_cls):
        m = map(lambda x: ugen_param(x)._as_audio_rate_input(*ugen_cls),
                self._param_value)
        return type(self._param_value)(m)

    def _as_ugen_rate(self):
        if len(self._param_value) == 1:
            return ugen_param(self._param_value[0])._as_ugen_rate()
        else:
            return utl.list_min([ugen_param(item)._as_ugen_rate() or 'scalar'\
                                 for item in self._param_value])

    def _write_input_spec(self, file, synthdef):
        for item in self._param_value:
            ugen_param(item)._write_input_spec(file, synthdef)


### Node Graph Parameters ###

class NodeParameter(GraphParameter):
    # asTarget.sc interface
    def _as_target(self):
        raise TypeError('invalid value for Node target: '
                        f'{type(self._param_value).__name__}')

    def _as_control_input(self):
        return self._param_value

    # extConvertToOSC.sc interface
    # // The following interface in an optimized version of asControlInput that
    # // flattens arrayed values and marks the outermost array of a value with
    # // '[' and ']'. These Chars are turning into typetags ([ and ]) in the OSC
    # // message to mark that array. Inner arrays are flattened (they are not
    # // meaningful in the server context), this makes it possible to write
    # // Synth("test", [0, [[100,200,300], [0.1,0.2,0.3], [10,20,30]] ]) and
    # // have all the arguments be assigned to consecutive controls in the synth.

    def _as_osc_arg_list(self):
        return self._as_control_input()

    def _as_osc_arg_embedded_list(self, lst):
        lst.append(self._as_control_input())
        return lst

    def _as_osc_arg_bundle(self):
        return self._as_control_input()


class NodeNone(NodeParameter):
    @classmethod
    def _param_type(cls):
        return (type(None),)

    def _as_target(self):
        return srv.Server.default.default_group

    def _as_osc_arg_list(self):
        return self._param_value


class NodeScalar(NodeParameter):
    @classmethod
    def _param_type(cls):
        return (int, float)

    def _as_target(self):
        from . import node as nod
        return nod.Group.basic_new(srv.Server.default, obj)


class NodeString(NodeParameter):
    @classmethod
    def _param_type(cls):
        return (str,)

    def _as_osc_arg_list(self):
        return self._param_value

    def _as_osc_arg_embedded_list(self, lst):
        lst.append(self._param_value)
        return lst

    # NOTE: porque hereda de RawArray que hereda de SequenceableCollection
    # le correspondería la misma implementación de NodeSequence, pero creo que
    # el único método que llama a este es _as_osc_arg_embedded_list que
    # String sobreescribe de manera distinta por lo que supongo que nunca
    # usa este método (además de que no parece consistente).
    def _as_osc_arg_bundle(self):
        raise Exeption('BUG: NodeString _as_osc_arg_bundle') # *** BUG: TEST
        lst = []
        for e in self._param_value:
            lst.append(node_param(e)._as_osc_arg_list())
        return lst


class NodeSequence(NodeParameter):
    @classmethod
    def _param_type(cls):
        return (list, tuple)

    def _as_control_input(self):
        return type(self._param_value)(
            node_param(x)._as_control_input() for x in self._param_value)

    def _as_osc_arg_list(self):
        lst = []
        for e in self._param_value:
            node_param(e)._as_osc_arg_embedded_list(lst)
        return lst

    def _as_osc_arg_embedded_list(self, lst):
        lst.append('[')
        for e in self._param_value:
            node_param(e)._as_osc_arg_embedded_list(lst)
        lst.append(']')
        return lst

    def _as_osc_arg_bundle(self):
        lst = []
        for e in self._param_value:
            lst.append(node_param(e)._as_osc_arg_list())
        return lst


### Module functions ###

def _graph_param(obj, param_cls):
    new_cls = None
    for sub_class in param_cls.__subclasses__():
        if isinstance(obj, sub_class._param_type()):
            new_cls = sub_class
            break
    if new_cls is None:
        raise TypeError(
            f"{param_cls.__name__}: type '{type(obj).__name__}' not supported")
    return new_cls(obj)


def ugen_param(obj):
    if isinstance(obj, UGenParameter):
        return obj
    return _graph_param(obj, UGenParameter)


def node_param(obj):
    if isinstance(obj, NodeParameter):
        return obj
    return _graph_param(obj, NodeParameter)
