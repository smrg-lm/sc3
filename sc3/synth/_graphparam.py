"""
Support for built in or extensions data types as UGen or Node
parameters. This module is an internal interface. To extend type
support classes inherit either from UGenParameter or NodeParameter
or both, define _param_type() for the extending type and override
the needed interface methods.

UGenParameter and NodeParameter are values intended for UGens parameters
and Node messages respectively. UGen, Node, SynthDef and SynthDescLib
classes make use of this interface to prepare data in the right format.
This functionality shoudln't be exposed to the user interface, supported
data types must just work with its own interface.
"""

from math import isnan

from ..base import classlibrary as clb
from ..base import utils as utl
from . import _specialindex as _si
from . import _fmtrw as frw


clb.ClassLibrary.late_imports(__name__,
    ('sc3.synth.server', 'srv'),
    ('sc3.synth.node', 'nod'),
    ('sc3.synth.ugens.line', 'lne')
)


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
        if self is self._param_value:
            return super().__repr__()   # *** BUG: MRO/MULTIPLE INHERITANCE
        else:
            return f'{type(self).__name__}({repr(self._param_value)})'


### UGen graph parameter interface ###

class UGenParameter(GraphParameter):
    def _is_valid_ugen_input(self):
        return False

    def _as_ugen_input(self, *_):
        return self._param_value

    def _as_audio_rate_input(self):
        if self._as_ugen_rate() != 'audio':
            return lne.K2A.ar(self._param_value)
        else:
            return self._param_value

    def _as_ugen_rate(self):  # Was rate for many non UGen objects in sclang.
        try:
            return self.rate
        except AttributeError as e:
            raise AttributeError(
                f'{type(self).__name__} does not implement '
                'rate attribute or _as_ugen_rate method') from e

    def _perform_binary_op_on_ugen(self, selector, ugen):
        selector = _si.sc_opname(selector.__name__)
        raise TypeError(
            f"operation '{selector}' is not supported between "
            f"UGen and {type(self._param_value).__name__}")

    def _r_perform_binary_op_on_ugen(self, selector, ugen):
        selector = _si.sc_opname(selector.__name__)
        raise TypeError(
            f"operation '{selector}' is not supported between "
            f"{type(self._param_value).__name__} and UGen")

    def _write_input_spec(self, file, synthdef):
        raise NotImplementedError(
            f'{type(self).__name__} does '
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
            return lne.Silent.ar()
        else:
            return lne.DC.ar(self._param_value)

    def _as_ugen_rate(self):
        return 'scalar'

    def _write_input_spec(self, file, synthdef):
        try:
            const_index = synthdef._constants[float(self._param_value)]
            frw.write_i32(file, -1)
            frw.write_i32(file, const_index)
        except KeyError as e:
            raise Exception(
                '_write_input_spec constant not found: '
                f'{float(self._param_value)}') from e


    ### UGen convenience methods (keep in sync) ###
    # These methods are only for ChannelList _multichannel_perform (multichannel
    # expansion UGen compatibility). Some of them could be used in different
    # places within ugens however I prefer to avoid its use. For them to work
    # consistently ugens inputs should be stored as UGenParameter instances and
    # I'm reluctant to do that at least by now, mostly because UGenScalar is
    # the only type compatible with signal operations and graph parameters are
    # being used as input translators so far.

    # def dup(self, n=2):  # Function and Object.
    # def madd(self, mul=1.0, add=0.0):  # Array, SimpleNumber and UGen.
    # def range(self, lo=0.0, hi=1.0):  # SimpleNumber (wslib!) and UGen. # *** BUG: two signatures in builtins
    # def exprange(self, lo=0.01, hi=1.0):  # SequenceableCollection and UGen (and Env).
    # def curverange(self, lo=0.0, hi=1.0, curve=-4):  # SequenceableCollection and UGen (and Env).
    # def unipolar(self, mul=1):  # SequenceableCollection and UGen.
    # def bipolar(self, mul=1):  # SequenceableCollection and UGen.

    def clip(self, lo=0.0, hi=1.0):
        return bi.clip(self._param_value, lo, hi)

    def fold(self, lo=0.0, hi=1.0):  # *** BUG: two signatures in builtins
        return bi.fold(self._param_value, lo, hi)

    def wrap(self, lo=0.0, hi=1.0):  # *** BUG: two signatures in builtins
        return bi.wrap(self._param_value, lo, hi)

    # def min_nyquist(self):  # SequenceableCollection and UGen.

    def degrad(self):
        return bi.degrad(self._param_value)

    def raddeg(self):
        return bi.raddeg(self._param_value)

    def blend(self, other, frac=0.5):
        return bi.blend(self._param_value, other, frac)

    def lag(self, time=0.1):  # SimpleNumber (^this) SequenceableCollection and UGen, idem until prune.
        return self._param_value

    def lag2(self, time=0.1):
        return self._param_value

    def lag3(self, time=0.1):
        return self._param_value

    def lagud(self, utime=0.1, dtime=0.1):
        return self._param_value

    def lag2ud(self, utime=0.1, dtime=0.1):
        return self._param_value

    def lag3ud(self, utime=0.1, dtime=0.1):
        return self._param_value

    def varlag(self, time=0.1, curvature=0, wrap=5, start=None):
        return self._param_value

    def slew(self, up=1, down=1):
        return self._param_value

    def prune(self, min, max, type='minmax'):
        return self._param_value

    # snap is not implemented
    # softround is not implemented

    def linlin(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return bi.linlin(self._param_value, inmin, inmax, outmin, outmax, clip)

    def linexp(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return bi.linexp(self._param_value, inmin, inmax, outmin, outmax, clip)

    def explin(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return bi.explin(self._param_value, inmin, inmax, outmin, outmax, clip)

    def expexp(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return bi.expexp(self._param_value, inmin, inmax, outmin, outmax, clip)

    def lincurve(self, inmin, inmax, outmin, outmax, curve=-4, clip='minmax'):
        return bi.lincurve(
            self._param_value, inmin, inmax, outmin, outmax, curve, clip)

    def curvelin(self, inmin, inmax, outmin, outmax, curve=-4, clip='minmax'):
        return bi.curvelin(
            self._param_value, inmin, inmax, outmin, outmax, curve, clip)

    def bilin(self, incenter, inmin, inmax, outcenter, outmin, outmax,
              clip='minmax'):
        return bi.bilin(
            self._param_value, incenter, inmin, inmax,
            outcenter, outmin, outmax, clip)

    def biexp(self, incenter, inmin, inmax, outcenter, outmin, outmax,
              clip='minmax'):
        return bi.biexp(
            self._param_value, incenter, inmin, inmax,
            outcenter, outmin, outmax, clip)

    def moddif(self, that=0.0, mod=1.0):
        return bi.moddif(self._param_value, that, mod)


class UGenSequence(UGenParameter):
    @classmethod
    def _param_type(cls):
        # tuple prevents multichannel expansion,
        # type must be kept for UGen inputs.
        return (list, tuple)

    def _is_valid_ugen_input(self):
        return True if self._param_value else False  # *** BUG: en sclang, debería comprobar isEmpty porque tira error en SynthDesc (SinOsc.ar() * []). O tal vez cuando construye BinaryOpUGen? Ver el grafo generado, tal vez deba ser None.

    def _as_ugen_input(self, *ugen_cls):
        m = map(
            lambda x: ugen_param(x)._as_ugen_input(*ugen_cls),
            self._param_value)
        return type(self._param_value)(m)

    def _as_audio_rate_input(self, *ugen_cls):
        m = map(
            lambda x: ugen_param(x)._as_audio_rate_input(*ugen_cls),
            self._param_value)
        return type(self._param_value)(m)

    def _as_ugen_rate(self):
        if len(self._param_value) == 1:
            return ugen_param(self._param_value[0])._as_ugen_rate()
        else:
            return utl.list_min(
                [ugen_param(item)._as_ugen_rate() or 'scalar'
                for item in self._param_value])

    def _write_input_spec(self, file, synthdef):
        for item in self._param_value:
            ugen_param(item)._write_input_spec(file, synthdef)


### Node Graph Parameters ###

class NodeParameter(GraphParameter):
    # asTarget.sc interface
    def _as_target(self):
        raise TypeError(
            'invalid value for Node target: '
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
        return [self._as_control_input()]

    def _embed_as_osc_arg(self, lst):
        lst.append(self._as_control_input())


class NodeNone(NodeParameter):
    @classmethod
    def _param_type(cls):
        return (type(None),)

    def _as_target(self):
        return srv.Server.default.default_group


class NodeScalar(NodeParameter):
    @classmethod
    def _param_type(cls):
        return (int, float)

    def _as_target(self):
        return nod.Group.basic_new(srv.Server.default, self._param_value)


class NodeString(NodeParameter):
    @classmethod
    def _param_type(cls):
        return (str,)


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
            node_param(e)._embed_as_osc_arg(lst)
        return lst

    def _embed_as_osc_arg(self, lst):
        lst.append('[')
        for e in self._param_value:
            node_param(e)._embed_as_osc_arg(lst)
        lst.append(']')


class NodeDictionary(NodeParameter):
    # Used to convert dict to a flat list of key-value pairs.

    @classmethod
    def _param_type(cls):
        return (dict,)

    def _as_control_input(self):
        return list(
            node_param(x)._as_control_input()
            for items in self._param_value.items() for x in items)

    def _as_osc_arg_list(self):
        return self._as_control_input()

    def _embed_as_osc_arg(self, lst):
        lst.append('[')
        for item in self._param_value.items():
            for e in item:
                node_param(e)._embed_as_osc_arg(lst)
        lst.append(']')


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
