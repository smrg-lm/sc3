"""UGens.sc

Development note for UGen classes
---------------------------------
Subclasses should not use __init__ to implement graph logic, interface
methods are _new1, _multi_new, _multi_new_list, _init_ugen, _init_outputs
(from MultiOutUGen). UGen instances are created internally with
_create_ugen_object. This is because ugens build a graph with multichannel
expansion and optimizations so they might not return an instace object or
an instance of the same type.
"""

import inspect
import operator
import logging

from ..base import classlibrary as clb
from ..base import utils as utl
from ..base import builtins as bi
from ..base import absobject as aob
from . import _specialindex as _si
from . import _graphparam as gpp
from . import _fmtrw as frw


clb.ClassLibrary.late_imports(__name__,
    ('sc3.base.main', '_libsc3'),
    ('sc3.synth.ugens.trig', 'trg'),
    ('sc3.synth.ugens.pan', 'pan'),
    ('sc3.synth.ugens.infougens', 'ifu'),
    ('sc3.synth.ugens.filter', 'flr'),
    ('sc3.synth.ugens.oscillators', 'ocl'),
    ('sc3.synth.ugens.testugens', 'tsu'),
    ('sc3.synth.ugens.line', 'lne'),
    ('sc3.synth.ugens.demand', 'dmd'),
    ('sc3.synth.ugens.poll', 'pll'),
)


__all__ = []


_logger = logging.getLogger(__name__)


class ChannelList(list, gpp.UGenSequence, aob.AbstractObject):
    '''List wrapper for multichannel expansion graph operations.'''

    def __init__(self, obj=None):
        if obj is None:
            super().__init__()
        elif isinstance(obj, (str, tuple)):
            super().__init__([obj])
        elif hasattr(obj, '__iter__'):
            super().__init__(obj)
        else:
            super().__init__([obj])
        super(gpp.UGenSequence, self).__init__(self)


    ### AbstractObject interface ###

    def _compose_unop(self, selector):
        return utl.list_unop(selector, self, type(self))

    def _compose_binop(self, selector, other):
        return utl.list_binop(selector, self, other, type(self))

    def _rcompose_binop(self, selector, other):
        return utl.list_binop(selector, other, self, type(self))

    def _compose_narop(self, selector, *args):
        return utl.list_narop(selector, self, *args, t=type(self))


    ### UGen convenience methods (keep in sync) ###

    def _multichannel_perform(self, selector, *args):
        ret = type(self)()
        for item in self:
            item = gpp.ugen_param(item)
            ret.append(getattr(item, selector)(*args))
        return ret

    def dup(self, n=2):
        return ChannelList([self] * n)

    def sum(self):  # Implemented by Collection with optional function.
        return utl.list_sum(self, type(self))

    def madd(self, mul=1.0, add=0.0):
        return type(self)(MulAdd.new(i, mul, add) for i in self)

    # in SequenceableCollection L1148.

    def range(self, lo=0.0, hi=1.0):
        return self._multichannel_perform('range', lo, hi)

    def exprange(self, lo=0.01, hi=1.0):
        return self._multichannel_perform('exprange', lo, hi)

    def curverange(self, lo=0.0, hi=1.0, curve=-4):
        return self._multichannel_perform('curverange', lo, hi, curve)

    def unipolar(self, mul=1):
        return self._multichannel_perform('unipolar', mul)

    def bipolar(self, mul=1):
        return self._multichannel_perform('bipolar', mul)

    def clip(self, lo=0.0, hi=1.0):
        return self._multichannel_perform('clip', lo, hi)

    def fold(self, lo=0.0, hi=1.0):
        return self._multichannel_perform('fold', lo, hi)

    def wrap(self, lo=0.0, hi=1.0):
        return self._multichannel_perform('wrap', lo, hi)

    def min_nyquist(self):
        return type(self)(bi.min(item, ifu.SampleRate.ir * 0.5) for item in self)

    # degrad implemented with performUnaryOp, is not overridden here
    # raddeg implemented with performUnaryOp, is not overridden here

    def blend(self, other, frac=0.5):
        return self._multichannel_perform('blend', other, frac)

    def lag(self, time=0.1):
        return self._multichannel_perform('lag', time)

    def lag2(self, time=0.1):
        return self._multichannel_perform('lag2', time)

    def lag3(self, time=0.1):
        return self._multichannel_perform('lag3', time)

    def lagud(self, utime=0.1, dtime=0.1):
        return self._multichannel_perform('lagud', utime, dtime)

    def lag2ud(self, utime=0.1, dtime=0.1):
        return self._multichannel_perform('lag2ud', utime, dtime)

    def lag3ud(self, utime=0.1, dtime=0.1):
        return self._multichannel_perform('lag3ud', utime, dtime)

    def varlag(self, time=0.1, curvature=0, wrap=5, start=None):
        return self._multichannel_perform('varlag', time, curvature, wrap, start)

    def slew(self, up=1, down=1):
        return self._multichannel_perform('slew', up, down)

    def prune(self, min, max, type='minmax'):
        return self._multichannel_perform('prune', min, max, type)

    # snap is not implemented
    # softround is not implemented

    def linlin(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return self._multichannel_perform('linlin', inmin, inmax, outmin,
                                          outmax, clip)

    def linexp(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return self._multichannel_perform('linexp', inmin, inmax, outmin,
                                          outmax, clip)

    def explin(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return self._multichannel_perform('explin', inmin, inmax, outmin,
                                          outmax, clip)

    def expexp(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return self._multichannel_perform('expexp', inmin, inmax, outmin,
                                          outmax, clip)

    def lincurve(self, inmin, inmax, outmin, outmax, curve=-4, clip='minmax'):
        return self._multichannel_perform('lincurve', inmin, inmax, outmin,
                                          outmax, curve, clip)

    def curvelin(self, inmin, inmax, outmin, outmax, curve=-4, clip='minmax'):
        return self._multichannel_perform('curvelin', inmin, inmax, outmin,
                                          outmax, curve, clip)

    def bilin(self, incenter, inmin, inmax, outcenter, outmin, outmax,
              clip='minmax'):
        return self._multichannel_perform('bilin', incenter, inmin, inmax,
                                          outcenter, outmin, outmax, clip)

    def biexp(self, incenter, inmin, inmax, outcenter, outmin, outmax,
              clip='minmax'):
        return self._multichannel_perform('biexp', incenter, inmin, inmax,
                                          outcenter, outmin, outmax, clip)

    def moddif(self, that=0.0, mod=1.0):
        return self._multichannel_perform('moddif', that, mod)

    # in Array.sc

    # num_channels, no (is len, UGen don't really know about channels), TODO: ensure consistency.
    # source_ugen, no if not needed.

    # Synth debug

    def poll(self, trig=10, label=None, trig_id=-1):
        if label is None:
            label = [f'ChannelList UGen [{i}]' for i in range(len(self))]
        return pll.Poll.new(trig, self, label, trig_id)

    def dpoll(self, label=None, run=1, trig_id=-1):
        if label is None:
            label = [f'ChannelList UGen [{i}]' for i in range(len(self))]
        return dmd.Dpoll(self, label, run, trig_id)

    def check_bad_values(self, id=0, post=2):
        return self._multichannel_perform('check_bad_values', id, post)


    ### Override list methods ###

    def __add__(self, other): # +
        return self._compose_binop(operator.add, other)

    def __iadd__(self, other): # +=
        return self._compose_binop(operator.add, other)

    def __mul__(self, other): # *
        return self._compose_binop(operator.mul, other)

    def __rmul__(self, other):
        return self._rcompose_binop(operator.mul, other)

    def __imul__(self, other): # *=
        return self._compose_binop(operator.mul, other)

    def __lt__(self, other): # <
        return self._compose_binop(operator.lt, other)

    def __le__(self, other): # <=
        return self._compose_binop(operator.le, other)

    # def __eq__(self, other):
    #     return self._compose_binop(operator.eq, other)

    # def __ne__(self, other):
    #     return self._compose_binop(operator.ne, other)

    def __gt__(self, other): # >
        return self._compose_binop(operator.gt, other)

    def __ge__(self, other): # >=
        return self._compose_binop(operator.ge, other)


    def __repr__(self):
        return f'ChannelList({super().__repr__()})'


class MetaSynthObject(type):
    # NOTE: Do not use default rate within the library.
    def __call__(cls, *args, **kwargs):
        if 'urate' in kwargs:
            rate = kwargs.pop('urate')
        else:
            rate = cls._default_rate
        rate = cls._method_selector_for_rate(rate)
        return getattr(cls, rate)(*args, **kwargs)


class SynthObject(gpp.UGenParameter, metaclass=MetaSynthObject):
    # NOTE: Sum3 and Sum4 don't define rate before calling _multi_new_list.
    _valid_rates = {'audio', 'control', 'demand', 'scalar', None}
    _default_rate = 'audio'

    @classmethod
    def _create_ugen_object(cls, rate):
        obj = cls.__new__(cls)
        super(SynthObject, obj).__init__(obj)
        obj._rate = rate
        obj._inputs = ()

        obj._synthdef = None  # Is_current_synthdef after _add_to_synth.
        obj._channels = []  # For MultiOutUGen, related to _synth_index.
        obj._synth_index = -1  # Order in built graph.
        obj._output_index = 0  # Used by OutputProxy.
        obj._special_index = 0  # Server op index.

        # Topo sort.
        obj._antecedents = None  # set()  # _init_topo_sort
        obj._descendants = None  # set()  # _init_topo_sort
        obj._width_first_antecedents = None  # list()  # _width_first_ugens[:].

        return obj

    @property
    def rate(self):
        return self._rate

    @property
    def inputs(self):
        return self._inputs

    @classmethod
    def _new1(cls, rate, *args):
        '''
        This method returns a single instance of the UGen, not multichannel
        expanded. It is called inside _multi_new_list, whenever a new single
        instance is needed.
        '''
        obj = cls._create_ugen_object(rate)
        obj._add_to_synth()
        return obj._init_ugen(*args)

    @classmethod
    def _multi_new(cls, *args):
        return cls._multi_new_list(list(args))

    @classmethod
    def _multi_new_list(cls, args):
        '''
        These methods are responsible for multichannel expansion. They call
        UGen._new1(rate, *args) for each parallel combination. Most UGen.ar/kr
        methods delegate to UGen.multiNewList. The first argument is rate, then
        the rest of the arguments as in UGen._new1(rate, *args).
        '''

        # Single channel, one ugen.
        length = 0
        args = gpp.ugen_param(args)._as_ugen_input(cls)
        for item in args:
            if isinstance(item, list):
                length = max(length, len(item))
        if length == 0:
            cls._check_valid_rate_name(args[0])
            return cls._new1(*args)

        # Multichannel expansion.
        new_args = [None] * len(args)
        results = [None] * length
        for i in range(length):
            for j, item in enumerate(args):
                new_args[j] = (
                    item[i % len(item)] if isinstance(item, list) else item)
            cls._check_valid_rate_name(new_args[0])
            results[i] = cls._multi_new(*new_args)
        return ChannelList(results)

    @classmethod
    def _check_valid_rate_name(cls, string):
        # Added check, not in sclang.
        if string not in cls._valid_rates:
            raise ValueError(f"{cls.__name__} invalid rate: '{string}'")

    def _init_ugen(self, *inputs):
        '''
        This method is called by _new1 that uses its return value. It must
        return self or ChannelList (cases of MultiOutUGen). Optimizations
        returning scalars or None (for no output) are usually returned by
        public UGen constructors (ar, kr, dr, ir or new).
        '''
        self._inputs = inputs
        return self

    @classmethod
    def _new_from_desc(cls, rate, num_outputs, inputs, special_index):
        obj = cls._create_ugen_object(rate)
        obj._inputs = tuple(inputs)
        obj._special_index = special_index
        return obj

    def __copy__(self):
        # // You can't really copy a UGen without disturbing the Synth.
        # // Usually you want the same object.
        return self


    ### SynthDef build ###

    def _add_to_synth(self):
        self._synthdef = _libsc3.main._current_synthdef
        if self._synthdef is not None:
            self._synthdef._add_ugen(self)

    def _collect_constants(self): # pong
        for input in self.inputs:
            if isinstance(input, (int, float)):
                self._synthdef._add_constant(float(input))

    def _check_inputs(self):  # pong
        '''Returns error msg or None.'''
        return self._check_valid_inputs()

    def _check_valid_inputs(self):
        '''Returns error msg or None.'''
        for i, input in enumerate(self.inputs):
            if not gpp.ugen_param(input)._is_valid_ugen_input():
                arg_name = self._arg_name_for_input_at(i)
                if arg_name is None: arg_name = i
                return f'arg: {arg_name} has bad input: {input}'
        return None

    def _check_n_inputs(self, n):
        if self.rate == 'audio':
            if n > len(self.inputs):
                n = len(self.inputs)
            for i in range(n):
                if gpp.ugen_param(self.inputs[i])._as_ugen_rate() != 'audio':
                    return (f'input {i} is not audio rate: {self.inputs[i]} '
                            f'{gpp.ugen_param(self.inputs[i])._as_ugen_rate()}')
        return self._check_valid_inputs()

    def _check_sr_as_first_input(self):  # Was checkSameRateAsFirstInput.
        if self.rate != gpp.ugen_param(self.inputs[0])._as_ugen_rate():
            return (f'first input is not {self.rate} rate: {self.inputs[0]} '
                    f'{gpp.ugen_param(self.inputs[0])._as_ugen_rate()}')
        return self._check_valid_inputs()

    def _arg_name_for_input_at(self, i):
        try:
            selector = type(self)._method_selector_for_rate(self.rate)
            method = getattr(type(self), selector)
            sig = inspect.signature(method)
            params = list(sig.parameters.values())
            arg_names = [x.name for x in params]
            if len(arg_names) == 0:
                return None
            i += self._arg_names_inputs_offset()
            if i < len(arg_names):
                return arg_names[i]
            else:
                return None
        except AttributeError:
            return None

    def _arg_names_inputs_offset(self):
        '''
        This method exist for two reasons, one is to skip 'this' argument in
        sclang introspection which is not needed in Python, the other reason is
        that many 'spec' ugens, such as EnvGen, Klang, etc., receive the
        specification array as the first argument in the language constructors
        but becomes a variable length list of arguments at the end of the
        server's ugen instruction so is moved at the end of the stored inputs.
        '''
        return 0  # NOTE: Is one less than sclang.

    @classmethod
    def _method_selector_for_rate(cls, rate):
        if rate == 'audio' or rate == 'ar':
            if hasattr(cls, 'ar'):
                return 'ar'
        elif rate == 'control' or rate == 'kr':
            if hasattr(cls, 'kr'):
                return 'kr'
        elif rate == 'scalar' or rate == 'ir':
            if hasattr(cls, 'ir'):
                return 'ir'
        elif rate == 'demand' or rate == 'dr':
            if hasattr(cls, 'dr'):
                return 'dr'
        elif rate is None:
            if hasattr(cls, 'new'):
                return 'new'
        # return None  # original behaviour
        raise AttributeError(f'{cls.__name__} has no {rate} rate constructor')

    def _dump_args(self):
        '''Used for error messages.'''
        msg = 'ARGS:\n'
        tab = ' ' * 4
        arg_name = None
        for i, input in enumerate(self.inputs):
            arg_name = self._arg_name_for_input_at(i)
            if arg_name is None:
                arg_name = str(i)
            msg += tab + arg_name + ': ' + str(input)
            msg += ' ' + type(input).__name__ + '\n'
        print(msg, end='')

    def _dump_name(self):
        '''Used for SynthDef.dump_ugens().'''
        return str(self._synth_index) + '_' + self.name


    @classmethod
    def _replace_zeroes_with_silence(cls, lst):
        # // This replaces zeroes with audio rate silence.
        # // Sub collections are deep replaced.
        num_zeroes = lst.count(0.0)
        if num_zeroes == 0:
            return lst
        silent_channels = ChannelList(lne.Silent.ar(num_zeroes))
        pos = 0
        for i, item in enumerate(lst):
            if item == 0.0:
                lst[i] = silent_channels[pos]
                pos += 1
            elif isinstance(item, list):
                res = cls._replace_zeroes_with_silence(item)
                lst[i] = res
        return lst


    ### SynthDef binary format ###

    def _write_def(self, file):
        try:
            frw.write_pascal_str(file, self.name)
            frw.write_i8(file, self._rate_number())
            frw.write_i32(file, self._num_inputs())
            frw.write_i32(file, self._num_outputs())
            frw.write_i16(file, self._special_index)
            # // write wire spec indices.
            for input in self.inputs:
                gpp.ugen_param(input)._write_input_spec(file, self._synthdef)
            self._write_output_specs(file)
        except Exception as e:
            raise Exception('SynthDef: could not write def') from e

    @property
    def name(self):  # Was a method, see OutputPorxy
        return type(self).__name__

    def _rate_number(self):
        if self.rate == 'audio': return 2
        if self.rate == 'control': return 1
        if self.rate == 'demand': return 3
        return 0  # 'scalar'

    def _num_inputs(self):
        return len(self.inputs)

    def _num_outputs(self):
        return 1

    def _write_input_spec(self, file, synthdef):
        frw.write_i32(file, self._synth_index)
        frw.write_i32(file, self._output_index)

    def _write_output_spec(self, file):
        frw.write_i8(file, self._rate_number())

    def _write_output_specs(self, file): # TODO: variación con 's' que llama a la sin 's', este método sería para las ugens con salidas múltiples, el nombre del método debería ser más descriptivo porque es fácil de confundir, además. # lo implementan AbstractOut, MultiOutUGen, SendPeakRMS, SendTrig y UGen.
        self._write_output_spec(file)


    ### Topo sort methods ###

    def _init_topo_sort(self):  # pong
        for input in self.inputs:
            if isinstance(input, UGen):
                if isinstance(input, OutputProxy):
                    ugen = input.source_ugen
                else:
                    ugen = input
                self._antecedents.add(ugen)
                ugen._descendants.add(self)
        for ugen in self._width_first_antecedents:
            self._antecedents.add(ugen)
            ugen._descendants.add(self)

    def _make_available(self):
        if len(self._antecedents) == 0:
            self._synthdef._available.append(self)

    def _remove_antecedent(self, ugen):
        self._antecedents.remove(ugen)
        self._make_available()

    def _arrange(self, out_stack):  # Was schedule.
        descendants = list(self._descendants)
        descendants.sort(key=lambda x: x._synth_index)
        for ugen in reversed(descendants):
            ugen._remove_antecedent(self)
        out_stack.append(self)

    def _optimize_graph(self):  # pong
        pass

    def _perform_dead_code_elimination(self):
        if len(self._descendants) == 0:
            # for input in self.inputs:  # It should be _antecedents, check sclang.
            for input in self._antecedents:
                if isinstance(input, UGen):
                    input._descendants.remove(self)
                    input._optimize_graph()
            self._synthdef._remove_ugen(self)
            return True
        return False


    ### SynthDesc interface ###

    # def _writes_to_bus(self):
    #     return False

    # def _can_free_synth(self):  # Non core interface, removed.
    #     return False

    # def is_control_ugen(cls):  # Use issubclass(cls, AbstractControl).
    # def is_input_ugen(cls):  # Use issubclass(cls, AbstractIn).
    # def is_output_ugen(cls):  # Use issubclass(cls, AbstractOut).
    # def is_ugen(self):  # Use isinstance(obj, UGen) (not used in sclang).
    # def _output_index(self): # Is attribute now.


    ### UGen graph parameter interface ###

    def _is_valid_ugen_input(self):
        return True

    def _as_ugen_input(self, *ugen_cls):
        return self

    # def _as_control_input(self):  # Is NodeParameter interface.
    #     raise TypeError("UGen can't be set as control input")

    def _as_audio_rate_input(self):
        if self.rate != 'audio':
            return lne.K2A.ar(self)
        return self

    def _as_ugen_rate(self): # Was rate.
        return self.rate


class UGen(SynthObject, aob.AbstractObject):
    @classmethod
    def signal_range(cls):
        return 'bipolar'


    ### AbstractObject interface ###

    def _compose_unop(self, selector):
        selector = _si.sc_opname(selector.__name__)
        return UnaryOpUGen.new(selector, self)

    def _compose_binop(self, selector, input):
        param = gpp.ugen_param(input)
        if param._is_valid_ugen_input():
            selector = _si.sc_opname(selector.__name__)
            return BinaryOpUGen.new(selector, self, input)
        else:
            return param._perform_binary_op_on_ugen(selector, self)

    def _rcompose_binop(self, selector, input):
        param = gpp.ugen_param(input)
        if param._is_valid_ugen_input():
            selector = _si.sc_opname(selector.__name__)
            return BinaryOpUGen.new(selector, input, self)
        else:
            return param._r_perform_binary_op_on_ugen(selector, self)

    def _compose_narop(self, selector, *args):
        raise NotImplementedError('UGen _compose_narop is not supported')

    # L426
    # // Complex support
    # asComplex
    # performBinaryOpOnComplex
    # def _perform_binary_op_on_ugen(input, selector, thing):


    ### Convenience methods (sync with ChannelList) ###

    def dup(self, n=2):
        return ChannelList([self] * n)

    def madd(self, mul=1.0, add=0.0):
        return MulAdd.new(self, mul, add)

    def range(self, lo=0.0, hi=1.0):
        if type(self).signal_range() == 'bipolar':
            mul = (hi - lo) * 0.5
            add = mul + lo
        else:
            mul = (hi - lo)
            add = lo
        return MulAdd.new(self, mul, add)

    def exprange(self, lo=0.01, hi=1.0):
        if type(self).signal_range() == 'bipolar':
            return self.linexp(-1, 1, lo, hi, None)
        else:
            return self.linexp(0, 1, lo, hi, None)

    def curverange(self, lo=0.0, hi=1.0, curve=-4):
        if type(self).signal_range() == 'bipolar':
            return self.lincurve(-1, 1, lo, hi, curve, None)
        else:
            return self.lincurve(0, 1, lo, hi, curve, None)

    def unipolar(self, mul=1):
        return self.range(0, mul)

    def bipolar(self, mul=1):
        return self.range(-mul, mul)

    def clip(self, lo=0.0, hi=1.0):
        if self.rate == 'demand':
            bi.max(lo, bi.min(hi, self))
        else:
            selector = trg.Clip._method_selector_for_rate(self.rate)
            return getattr(trg.Clip, selector)(self, lo, hi)

    def fold(self, lo=0.0, hi=0.0):
        if self.rate == 'demand':
            raise NotImplementedError('fold is not implemented for dr ugens')
        else:
            selector = trg.Fold._method_selector_for_rate(self.rate)
            return getattr(trg.Fold, selector)(self, lo, hi)

    def wrap(self, lo=0.0, hi=1.0):
        if self.rate == 'demand':
            raise NotImplementedError('wrap is not implemented for dr ugens')
        else:
            selector = trg.Wrap._method_selector_for_rate(self.rate)
            return getattr(trg.Wrap, selector)(self, lo, hi)

    def degrad(self):  # override (not to call bi.degrad)
        return self * (bi.pi / 180.)

    def raddeg(self):  # override (not to call bi.raddeg)
        return self * (180. / bi.pi)

    def blend(self, other, frac=0.5):
        if self.range == 'demand' or gpp.ugen_param(other).rate == 'demand':
            raise NotImplementedError('blend is not implemented for dr ugens')
        else:
            pan = bi.linlin(frec, 0.0, 1.0, -1.0, 1.0)
            if self.rate == 'audio':
                return pan.XFade2.ar(self, other, pan)
            if gpp.ugen_param(other).rate == 'audio':
                return pan.XFade2.ar(other, self, -pan)
            selector = pan.LinXFade2._method_selector_for_rate(self.rate)
            return getattr(pan.LinXFade2, selector)(self, other, pan)

    def min_nyquist(self):
        return bi.min(self, ifu.SampleRate.ir * 0.5)

    def lag(self, time=0.1):
        selector = flr.Lag._method_selector_for_rate(self.rate)
        return getattr(flr.Lag, selector)(self, time)

    def lag2(self, time=0.1):
        selector = flr.Lag2._method_selector_for_rate(self.rate)
        return getattr(flr.Lag2, selector)(self, time)

    def lag3(self, time=0.1):
        selector = flr.Lag3._method_selector_for_rate(self.rate)
        return getattr(flr.Lag3, selector)(self, time)

    def lagud(self, utime=0.1, dtime=0.1):
        selector = flr.LagUD._method_selector_for_rate(self.rate)
        return getattr(flr.LagUD, selector)(self, utime, dtime)

    def lag2ud(self, utime=0.1, dtime=0.1):
        selector = flr.Lag2UD._method_selector_for_rate(self.rate)
        return getattr(flr.Lag2UD, selector)(self, utime, dtime)

    def lag3ud(self, utime=0.1, dtime=0.1):
        selector = flr.Lag3UD._method_selector_for_rate(self.rate)
        return getattr(flr.Lag3UD, selector)(self, utime, dtime)

    def varlag(self, time=0.1, curvature=0, wrap=5, start=None):
        selector = flr.VarLag._method_selector_for_rate(self.rate)
        return getattr(flr.VarLag, selector)(self, time, curvature, wrap, start)

    def slew(self, up=1, down=1):
        selector = flr.Slew._method_selector_for_rate(self.rate)
        return getattr(flr.Slew, selector)(self, up, down)

    def prune(self, min, max, type='minmax'):
        if type == 'minmax':
            return self.clip(min, max)
        elif type == 'min':
            return self.max(min)
        elif type == 'max':
            return self.min(max)
        return self

    def snap(self, resolution=1.0, margin=0.05, strengh=1.0):  # NOTE: UGen/SimpleNumber, not in AbstractFunction
        selector = ocl.Select._method_selector_for_rate(self.rate)
        diff = round(self, resolution) - self
        return getattr(ocl.Select, selector)(
            abs(diff) < margin, [self, self + strengh * diff])

    def softround(self, resolution=1.0, margin=0.05, strengh=1.0):  # NOTE: UGen/SimpleNumber, not in AbstractFunction
        selector = ocl.Select._method_selector_for_rate(self.rate)
        diff = round(self, resolution) - self
        return getattr(ocl.Select, selector)(
            abs(diff) > margin, [self, self + strengh * diff])

    def linlin(self, inmin, inmax, outmin, outmax, clip='minmax'):
        selector = lne.LinLin._method_selector_for_rate(self.rate)  # BUG: I see these can fail for ir/dr ugens however sclang implementation semantics is diverse and not clear.
        return getattr(lne.LinLin, selector)(
            self.prune(inmin, inmax, clip), inmin, inmax, outmin, outmax)

    def linexp(self, inmin, inmax, outmin, outmax, clip='minmax'):
        selector = lne.LinExp._method_selector_for_rate(self.rate)
        return getattr(lne.LinExp, selector)(
            self.prune(inmin, inmax, clip), inmin, inmax, outmin, outmax)

    def explin(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return (
            bi.log(self.prune(inmin, inmax, clip) / inmin) /
            bi.log(inmax / inmin) * (outmax - outmin) + outmin)  # // no separate ugen yet

    def expexp(self, inmin, inmax, outmin, outmax, clip='minmax'):
        return pow(
            outmax / outmin,
            bi.log(self.prune(inmin, inmax, clip) / inmin) /
            bi.log(inmax / inmin)) * outmin

    def lincurve(self, inmin, inmax, outmin, outmax, curve=-4, clip='minmax'):
        if isinstance(curve, (int, float)) and abs(curve) < 0.125:
            return self.linlin(inmin, inmax, outmin, outmax, clip)
        grow = bi.exp(curve)
        a = (outmax - outmin) / (1.0 - grow)
        b = outmin + a
        scaled = (self.prune(inmin, inmax, clip) - inmin) / (inmax - inmin)
        curved_res = b - a * pow(grow, scaled)
        if gpp.ugen_param(curve).rate == 'scalar':
            return curved_res
        else:
            selector = ocl.Select._method_selector_for_rate(self.rate)
            return getattr(ocl.Select, selector)(abs(curve) >= 0.125,
                [self.linlin(inmin, inmax, outmin, outmax, clip), curved_res])

    def curvelin(self, inmin, inmax, outmin, outmax, curve=-4, clip='minmax'):
        if isinstance(curve, (int, float)) and abs(curve) < 0.125:
            return self.linlin(inmin, inmax, outmin, outmax, clip)
        grow = bi.exp(curve)
        a = (inmax - inmin) / (1.0 - grow)
        b = inmin + a
        lin_res = (
            bi.log((b - this.prune(inmin, inmax, clip)) / a) *
            (outmax - outmin) / curve + outmin)
        if gpp.ugen_param(curve).rate == 'scalar':
            return lin_res
        else:
            selector = ocl.Select._method_selector_for_rate(self.rate)
            return getattr(ocl.Select, selector)(abs(curve) >= 0.125,
                [self.linlin(inmin, inmax, outmin, outmax, clip), lin_res])

    def bilin(self, incenter, inmin, inmax, outcenter, outmin, outmax,
              clip='minmax'):
        selector = ocl.Select._method_selector_for_rate(self.rate)  # BUG: in sclang the call is over the wrong class and doesn't uses _multi_new as above.
        return getattr(ocl.Select, selector)(self < incenter, [
            self.linlin(incenter, inmax, outcenter, outmax, clip),
            self.linlin(inmin, incenter, outmin, outcenter, clip)])

    # biexp is not overridden

    def moddif(self, that=0.0, mod=1.0):
        selector = trg.ModDif._method_selector_for_rate(self.rate)
        return getattr(trg.ModDif, selector)(self, that, mod)

    def sanitize(self):
        selector = tsu.Sanitize._method_selector_for_rate(self.rate)  # BUG: in sclang the call is over the wrong class.
        return getattr(tsu.Sanitize, selector)(self)

    # degreeToKey (I don't know why this method is important)

    # Synth debug convenience methods

    def poll(self, trig=10, label=None, trig_id=-1):
        return pll.Poll.new(trig, self, label, trig_id)

    def dpoll(self, label=None, run=1, trig_id=-1):
        return dmd.Dpoll.new(self, label, run, trig_id)

    def check_bad_values(self, id=0, post=2):
        selector = tsu.CheckBadValues._method_selector_for_rate(self.rate)
        getattr(tsu.CheckBadValues, selector)(self, id, post)
        # // add the UGen to the tree but keep self as the output
        return self


class PureUGen():
    # // UGen which has no side effect and can therefore be considered for
    # // a dead code elimination. Read access to buffers/busses are allowed.
    def _optimize_graph(self):  # override
        self._perform_dead_code_elimination()


class MultiOutUGen(UGen):
    @property
    def _synth_index(self):
        return self.__synth_index

    @_synth_index.setter
    def _synth_index(self, value):
        self.__synth_index = value
        for output in self._channels:
            output._synth_index = value

    @_synth_index.deleter
    def _synth_index(self):
        del self.__synth_index

    @classmethod
    def _new_from_desc(cls, rate, num_outputs, inputs, special_index=None):  # override
        obj = cls._create_ugen_object(rate)
        obj._inputs = tuple(inputs)
        obj._init_outputs(num_outputs, rate)
        return obj

    def _init_outputs(self, num_channels, rate):
        '''
        Return value of this method is used as return value of _init_ugen
        in subclasses.
        '''
        if num_channels is None or num_channels < 1:
            raise Exception(
                f'{self.name}: wrong number of channels ({num_channels})')
        self._channels = ChannelList(
            [OutputProxy.new(rate, self, i) for i in range(num_channels)])
        if num_channels == 1:
            return self._channels[0]
        return self._channels

    def _num_outputs(self):  # override
        return len(self._channels)

    def _write_output_specs(self, file):  # override
        for output in self._channels:
            output._write_output_spec(file)


class OutputProxy(UGen):
    @classmethod
    def new(cls, rate, source_ugen, index):
        return cls._new1(rate, source_ugen, index)

    def _init_ugen(self, source_ugen, index):  # override
        self.source_ugen = source_ugen  # Was just source.
        self._output_index = index
        self._synth_index = source_ugen._synth_index
        return self  # NOTE: Must return self.

    def _add_to_synth(self):  # override
        # OutputProxy is not part of the SynthDef graph but source_ugen.
        self._synthdef = _libsc3.main._current_synthdef

    def _dump_name(self):  # override
        return f'{self.source_ugen._dump_name()}[{self._output_index}]'

    @property
    def name(self):
        # NOTE: OutputProxy define <>name, Control UGen return OutputPorxy
        # in SynthDef _set_control_names and change this property but can't
        # find where this getter is used (if used).
        try:
            return self.__name
        except AttributeError:
            return None

    @name.setter
    def name(self, value):
        self.__name = value


class WidthFirstUGen(SynthObject):  # Was in fft.py
    _default_rate = None
    # bufio.py uses new to create 'scalar'
    # fft uses new to create 'control'

    def _add_to_synth(self):  # override
        self._synthdef = _libsc3.main._current_synthdef
        if self._synthdef is not None:
            self._synthdef._add_ugen(self)
            self._synthdef._width_first_ugens.append(self)

    def _add_copies_if_needed(self):
        pass


### BasicOpUGens.sc ###

class BasicOpUGen(UGen):
    def __init__(self):
        super().__init__()
        self._operator = None

    # writeName commented method, no other standard UGen class defines it.

    @property
    def operator(self):
        return self._operator

    @operator.setter
    def operator(self, value):
        index, operator = _si.sc_spindex_opname(value)
        self._operator = operator
        self._special_index = index
        if self._special_index < 0:
            raise Exception(
                f"operator '{value}' applied to a UGen "
                "is not supported by the server")

    @operator.deleter
    def operator(self):
        del self._operator

    def _arg_name_for_input_at(self, i):  # override
        try:
            method = getattr(type(self), 'new')
            sig = inspect.signature(method)
            params = list(sig.parameters.values())
            arg_names = [x.name for x in params]
            if len(arg_names) == 0:
                return None
            i += self._arg_names_inputs_offset()
            if i < len(arg_names):
                return arg_names[i]
            else:
                return None
        except AttributeError:
            return None

    def _arg_names_inputs_offset(self):  # override
        return 1  # One less than sclang

    def _dump_args(self):  # override
        msg = 'ARGS:\n'
        tab = ' ' * 4
        msg += tab + 'operator: ' + self.operator + '\n'
        arg_name = None
        for i, input in enumerate(self.inputs):
            arg_name = self._arg_name_for_input_at(i)
            if not arg_name:
                arg_name = str(i)
            msg += tab + arg_name + ': ' + str(input)
            msg += ' ' + type(input).__name__ + '\n'
        print(msg, end='')

    def _dump_name(self):  # override
        return str(self._synth_index) + '_' + self.operator


class UnaryOpUGen(BasicOpUGen):
    @classmethod
    def new(cls, selector, a):
        return cls._multi_new('audio', selector, a)

    @classmethod
    def _new_from_desc(cls, rate, num_outputs, inputs, special_index):  # override
        # *** BUG: this method is missing in sclang
        obj = super()._new_from_desc(rate, num_outputs, inputs, special_index)
        obj._operator = _si.sc_opname_from_index(special_index, 'unary')
        return obj

    def _init_ugen(self, operator, input):  # override
        self.operator = operator
        self._rate = gpp.ugen_param(input)._as_ugen_rate()
        self._inputs = (input,)
        return self  # Must return self.

    def _optimize_graph(self):  # override
        self._perform_dead_code_elimination()


class BinaryOpUGen(BasicOpUGen):
    @classmethod
    def _new1(cls, rate, selector, a, b):  # override
        if selector == '*':
            if a == 0.0: return 0.0
            if b == 0.0: return 0.0
            if a == 1.0: return b
            if a == -1.0: return -b  # neg
            if b == 1.0: return a
            if b == -1.0: return -a  # neg
        if selector == '+':
            if a == 0.0: return b
            if b == 0.0: return a
        if selector == '-':
            if a == 0.0: return -b  # neg
            if b == 0.0: return a
        if selector == '/':
            if b == 1.0: return a
            if b == -1.0: return -a  # neg
        return super()._new1(rate, selector, a, b)

    @classmethod
    def new(cls, selector, a, b):
        return cls._multi_new('audio', selector, a, b)

    @classmethod
    def _new_from_desc(cls, rate, num_outputs, inputs, special_index):  # override
        obj = super()._new_from_desc(rate, num_outputs, inputs, special_index)
        obj._operator = _si.sc_opname_from_index(special_index, 'binary')
        return obj

    def _init_ugen(self, operator, a, b):  # override
        self.operator = operator
        self._rate = self._determine_rate(a, b)
        self._inputs = (a, b)
        return self  # Must return self.

    def _determine_rate(self, a, b):
        a_rate = gpp.ugen_param(a)._as_ugen_rate()
        b_rate = gpp.ugen_param(b)._as_ugen_rate()
        # Order matters.
        if a_rate == 'demand': return 'demand'
        if b_rate == 'demand': return 'demand'
        if a_rate == 'audio': return 'audio'
        if b_rate == 'audio': return 'audio'
        if a_rate == 'control': return 'control'
        if b_rate == 'control': return 'control'
        return 'scalar'

    def _optimize_graph(self):  # override
        # // this.constantFolding;
        if self._perform_dead_code_elimination():
            return self
        if self.operator == '+':
            self._optimize_add()
            return self
        if self.operator == '-':
            self._optimize_sub()
            return self

    def _optimize_add(self):
        # // create a Sum3 if possible
        optimized_ugen = self._optimize_to_sum3()
        # // create a Sum4 if possible
        if not optimized_ugen:
            optimized_ugen = self._optimize_to_sum4()
        # // create a MulAdd if possible.
        if not optimized_ugen:
            optimized_ugen = self._optimize_to_muladd()
        # // optimize negative additions
        if not optimized_ugen:
            optimized_ugen = self._optimize_addneg()

        if optimized_ugen:
            self._synthdef._replace_ugen(self, optimized_ugen)

    def _optimize_to_sum3(self):
        a, b = self.inputs
        if gpp.ugen_param(a)._as_ugen_rate() == 'demand'\
        or gpp.ugen_param(b)._as_ugen_rate() == 'demand':
            return None

        if isinstance(a, BinaryOpUGen) and a.operator == '+'\
        and len(a._descendants) == 1:
            self._synthdef._remove_ugen(a)
            if a is b:  # Edge case fixed in supercollider/supercollider#5048
                replacement = Sum4.new(
                    a.inputs[0], a.inputs[0], a.inputs[1], a.inputs[1])
            else:
                replacement = Sum3.new(a.inputs[0], a.inputs[1], b)
            replacement._descendants = self._descendants
            self._optimize_update_descendants(replacement, a)
            return replacement

        if isinstance(b, BinaryOpUGen) and b.operator == '+'\
        and len(b._descendants) == 1:
            self._synthdef._remove_ugen(b)
            replacement = Sum3.new(b.inputs[0], b.inputs[1], a)
            replacement._descendants = self._descendants
            self._optimize_update_descendants(replacement, b)
            return replacement

        return None

    def _optimize_to_sum4(self):
        a, b = self.inputs
        if gpp.ugen_param(a)._as_ugen_rate() == 'demand'\
        or gpp.ugen_param(b)._as_ugen_rate() == 'demand':
            return None

        if isinstance(a, Sum3) and len(a._descendants) == 1:
            self._synthdef._remove_ugen(a)
            replacement = Sum4.new(a.inputs[0], a.inputs[1], a.inputs[2], b)
            replacement._descendants = self._descendants
            self._optimize_update_descendants(replacement, a)
            return replacement

        if isinstance(b, Sum3) and len(b._descendants) == 1:
            self._synthdef._remove_ugen(b)
            replacement = Sum4.new(b.inputs[0], b.inputs[1], b.inputs[2], a)
            replacement._descendants = self._descendants
            self._optimize_update_descendants(replacement, b)
            return replacement

        return None

    def _optimize_to_muladd(self):
        a, b = self.inputs

        if isinstance(a, BinaryOpUGen) and a.operator == '*'\
        and len(a._descendants) == 1:

            if MulAdd._can_be_muladd(a.inputs[0], a.inputs[1], b):
                self._synthdef._remove_ugen(a)
                replacement = MulAdd.new(a.inputs[0], a.inputs[1], b)
                replacement._descendants = self._descendants
                self._optimize_update_descendants(replacement, a)
                return replacement

            if MulAdd._can_be_muladd(a.inputs[1], a.inputs[0], b):
                self._synthdef._remove_ugen(a)
                replacement = MulAdd.new(a.inputs[1], a.inputs[0], b)
                replacement._descendants = self._descendants
                self._optimize_update_descendants(replacement, a)
                return replacement

        # does optimization code need to be optimized?
        if isinstance(b, BinaryOpUGen) and b.operator == '*'\
        and len(b._descendants) == 1:

            if MulAdd._can_be_muladd(b.inputs[0], b.inputs[1], a):
                self._synthdef._remove_ugen(b)
                replacement = MulAdd.new(b.inputs[0], b.inputs[1], a)
                replacement._descendants = self._descendants
                self._optimize_update_descendants(replacement, b)
                return replacement

            if MulAdd._can_be_muladd(b.inputs[1], b.inputs[0], a):
                self._synthdef._remove_ugen(b)
                replacement = MulAdd.new(b.inputs[1], b.inputs[0], a)
                replacement._descendants = self._descendants
                self._optimize_update_descendants(replacement, b)
                return replacement

        return None

    def _optimize_addneg(self):
        a, b = self.inputs

        if isinstance(b, UnaryOpUGen) and b.operator == 'neg'\
        and len(b._descendants) == 1:
            # // a + b.neg -> a - b
            self._synthdef._remove_ugen(b)
            replacement = a - b.inputs[0]
            # // This is the first time the dependants logic appears. It's
            # // repeated below. We will remove 'self' from the synthdef, and
            # // replace it with 'replacement'. 'replacement' should then have
            # // all the same descendants as 'self'.
            replacement._descendants = self._descendants
            # // Drop 'self' and 'b' from all of replacement's inputs'
            # // descendant lists so that future optimizations decide correctly.
            self._optimize_update_descendants(replacement, b)
            return replacement

        if isinstance(a, UnaryOpUGen) and a.operator == 'neg'\
        and len(a._descendants) == 1:
            # // a.neg + b -> b - a
            self._synthdef._remove_ugen(a)
            replacement = b - a.inputs[0]
            replacement._descendants = self._descendants
            self._optimize_update_descendants(replacement, a)
            return replacement

        return None

    def _optimize_sub(self):
        a, b = self.inputs

        if isinstance(b, UnaryOpUGen) and b.operator == 'neg'\
        and len(b._descendants) == 1:
            # // a - b.neg -> a + b
            self._synthdef._remove_ugen(b)
            replacement = BinaryOpUGen.new('+', a, b.inputs[0])
            replacement._descendants = self._descendants
            self._optimize_update_descendants(replacement, b)
            self._synthdef._replace_ugen(self, replacement)
            replacement._optimize_graph()  # // Not called from _optimize_add, no need to return ugen here.

        return None

    def _optimize_update_descendants(self, replacement, deleted_unit):
        # // 'this' = old ugen being replaced
        # // replacement = this's replacement
        # // deletedUnit = auxiliary unit being removed, not replaced
        for input in replacement.inputs:
            if isinstance(input, UGen):
                if isinstance(input, OutputProxy):
                    input = input.source_ugen
                if input._descendants is None:
                    return
                input._descendants.add(replacement)
                input._descendants.discard(self)
                input._descendants.discard(deleted_unit)

    def _constant_folding(self): # Not sure if used.
        ... # BUG, boring to copy.


class MulAdd(UGen):
    @classmethod
    def new(cls, input, mul=1.0, add=0.0):
        params = gpp.ugen_param([input, mul, add])
        rate = params._as_ugen_rate()
        args = params._as_ugen_input(cls)
        return cls._multi_new_list([rate] + args)

    @classmethod
    def _new1(cls, rate, input, mul, add):  # override
        if mul == 0.0: return add
        minus = mul == -1.0
        nomul = mul == 1.0
        noadd = add == 0.0
        if nomul and noadd: return input
        if minus and noadd: return -input  # neg
        if noadd: return input * mul
        if minus: return add - input
        if nomul: return input + add

        if cls._can_be_muladd(input, mul, add):
            return super()._new1(rate, input, mul, add)
        if cls._can_be_muladd(mul, input, add):
            return super()._new1(rate, mul, input, add)
        return (input * mul) + add

    def _init_ugen(self, input, mul, add):  # override
        self._inputs = (input, mul, add)
        self._rate = gpp.ugen_param(self.inputs)._as_ugen_rate()
        return self  # Must return self.

    @classmethod
    def _can_be_muladd(cls, input, mul, add):
        # // see if these inputs satisfy the constraints of a MulAdd ugen.
        in_rate = gpp.ugen_param(input)._as_ugen_rate()
        if in_rate == 'audio':
            return True
        mul_rate = gpp.ugen_param(mul)._as_ugen_rate()
        add_rate = gpp.ugen_param(add)._as_ugen_rate()
        if in_rate == 'control'\
        and (mul_rate == 'control' or mul_rate == 'scalar')\
        and (add_rate == 'control' or add_rate == 'scalar'):
            return True
        return False


class Sum3(UGen):
    @classmethod
    def new(cls, in0, in1, in2):
        return cls._multi_new(None, in0, in1, in2)

    @classmethod
    def _new1(cls, _, in0, in1, in2):  # override
        if in2 == 0.0: return in0 + in1
        if in1 == 0.0: return in0 + in2
        if in0 == 0.0: return in1 + in2

        arg_list = [in0, in1, in2]
        rate = gpp.ugen_param(arg_list)._as_ugen_rate()
        arg_list.sort(key=lambda x: gpp.ugen_param(x)._as_ugen_rate())  # NOTE: Why sort?

        return super()._new1(rate, *arg_list)


class Sum4(UGen):
    @classmethod
    def new(cls, in0, in1, in2, in3):
        return cls._multi_new(None, in0, in1, in2, in3)

    @classmethod
    def _new1(cls, _, in0, in1, in2, in3):  # override
        if in0 == 0.0: return Sum3._new1(None, in1, in2, in3)
        if in1 == 0.0: return Sum3._new1(None, in0, in2, in3)
        if in2 == 0.0: return Sum3._new1(None, in0, in1, in3)
        if in3 == 0.0: return Sum3._new1(None, in0, in1, in2)

        arg_list = [in0, in1, in2, in3]
        rate = gpp.ugen_param(arg_list)._as_ugen_rate()
        arg_list.sort(key=lambda x: gpp.ugen_param(x)._as_ugen_rate())  # NOTE: Why sort?

        return super()._new1(rate, *arg_list)


class PseudoUGen(SynthObject):
    # Base class to reinforce the interface. Pseudo UGens never
    # return instances of themselves but of another UGen subclass.
    pass
