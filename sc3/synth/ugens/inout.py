"""InOut.sc"""

import logging

from ...base import utils as utl
from ...base import main as _libsc3
from .. import ugen as ugn
from .. import _graphparam as gpp
from . import infougens as ifu


_logger = logging.getLogger(__name__)


# NOTE: Instead of transcribing NamedControl it could be better to
# refactor Control, AudioControl, TrigControl and LagControlto so they
# call add_name when instantiated, e.g. Control('ctlname', values), but
# it requires refactoring in SynthDef which process _args_to_controls
# and _build_controls separatelly.


### Controls ###

class ControlName():
    def __init__(self, name, index, rate, default_value, arg_num, lag=None):
        self.name = name
        self.index = index
        self.rate = rate
        self.default_value = default_value
        self.arg_num = arg_num
        self.lag = lag or 0.0

    @property
    def channels(self):
        return len(utl.as_list(self.default_value))

    def __repr__(self):  # Was printOn.
        return (
            f"{type(self).__name__}(name='{self.name}', index={self.index}, "
            f"rate='{self.rate}', default_value={self.default_value}, "
            f"arg_num={self.arg_num}, lag={self.lag})")


class AbstractControl(ugn.MultiOutUGen):
    '''Create control ugens from synthdef function's arguments.

    To instantiate a control manually it first has to be added to the
    synthdef with the `add_name` constructor and then create ugen by
    rate.

    ::

        @synthdef
        def test():
            LagControl.add_name('freq')
            freq = LagControl.kr([440, 880], [0.1, 0.2])
            Control.add_name('amp')
            amp = Control.ir(0.1)
            Out.ar(0, DC.ar(freq) * amp)

    TODO: Implement NamedControl instead, remove add_name and make control
    ugens internal.

    '''

    # Base class for control ugens not present in sclang. Using type
    # hierarchy properly simplify redundant methods like 'is_control_ugen'
    # for Control and AudioControl and is_input_ugen/is_output_ugen for
    # AbstractIn/AbstractOut ugens. Those methods are only relevant to
    # SynthDesc no need for duck typing or alike.

    def __init__(self):
        super().__init__()
        self.values = []

    def __repr__(self):
        selector = type(self)._method_selector_for_rate(self.rate)
        return f'{type(self).__name__}.{selector}({self.values})'


class Control(AbstractControl):
    _default_rate = 'control'

    @classmethod
    def add_name(cls, name):  # Was names.
        synthdef = _libsc3.main._current_synthdef
        index = synthdef._control_index
        synthdef._add_control_name(
            ControlName(
                name, index, 'control',
                None, synthdef._all_control_names))

    @classmethod
    def ir(cls, values):
        return cls._multi_new('scalar', *utl.as_list(values))

    @classmethod
    def kr(cls, values):
        return cls._multi_new('control', *utl.as_list(values))

    def _init_ugen(self, *values):  # override
        # Control ugens don't write _inputs but store cn default value.
        self.values = list(values)
        if self._synthdef is not None:
            # Special index field is reused as control type index.
            self._special_index = len(self._synthdef._controls)
            self._synthdef._controls.extend(self.values)

            ctl_names = self._synthdef._control_names
            if len(ctl_names) > 0:
                # // current control is always the last added, so:
                last_control = ctl_names[-1]
                if last_control.default_value is None:
                    # // only write if not there yet:
                    last_control.default_value = utl.unbubble(self.values)

            self._synthdef._control_index += len(self.values)
        return self._init_outputs(len(self.values), self.rate)

    # is_control_ugen(cls):  # Use issubclass(cls, AbstractControl).


class AudioControl(AbstractControl):
    @classmethod
    def add_name(cls, name):  # Was names.
        synthdef = _libsc3.main._current_synthdef
        index = synthdef._control_index
        synthdef._add_control_name(
            ControlName(
                name, index, 'audio',
                None, synthdef._all_control_names))

    @classmethod
    def ar(cls, values):
        return cls._multi_new('audio', *utl.as_list(values))

    def _init_ugen(self, *values):  # override
        # AudioControl ugens don't write _inputs but store cn default value.
        self.values = list(values)
        if self._synthdef is not None:
            # Special index field is reused as control type index.
            self._special_index = len(self._synthdef._controls)
            self._synthdef._controls.extend(self.values)
            self._synthdef._control_index += len(self.values)
        return self._init_outputs(len(self.values), self.rate)

    # is_audio_control_ugen(cls):  # Not used, see AbstractControl note.
    # is_control_ugen(cls):  # Use issubclass(cls, AbstractControl).


class TrigControl(Control):
    pass


class LagControl(Control):
    @classmethod
    def ir(cls, values, lag):
        raise NotImplementedError(
            f'{cls.__name__} should not implemet ir constructor')

    @classmethod
    def kr(cls, values, lags):
        values = utl.as_list(values)
        if isinstance(lags, (int, float)): # isNumber
            lags = [lags] * len(values)
        else:
            lags = utl.as_list(lags)

        if len(values) != len(lags):
            _logger.warning(
                f'{cls.__name__} len(values) != len(lags), '
                f'{cls.__name__}.kr returns None')
            return None

        n = 16
        values = [values[i:i + n] for i in range(0, len(values), n)]  # values.clump(16)
        lags = [lags[i:i + n] for i in range(0, len(lags), n)]  # lags.clump(16)
        outputs = ugn.ChannelList()
        for i in range(len(values)):
            out = cls._multi_new('control', *values[i], *lags[i])
            outputs.extend(utl.as_list(out))
        if len(outputs) == 1:
            return outputs[0]
        else:
            return outputs

    @classmethod
    def ar(cls, values, lags):
        return AudioControl.ar(values).lag(lags)

    def _init_ugen(self, *stuff):  # override
        size = len(stuff)
        size2 = size >> 1  # size // 2
        # LagControl wites lag values as _inputs and store cn default values.
        self._inputs = stuff[size2:size]
        self.values = list(stuff[:size2])
        if self._synthdef is not None:
            # Special index field is reused as control type index.
            self._special_index = len(self._synthdef._controls)
            self._synthdef._controls.extend(self.values)
            self._synthdef._control_index += len(self.values)
        return self._init_outputs(len(self.values), self.rate)

    def __repr__(self):
        return f'{type(self).__name__}.kr({self.values}, {list(self._inputs)})'


### Inputs ###

class AbstractIn(ugn.MultiOutUGen):
    # def is_input_ugen(self):  # NOTE: See AbstractControl note.

    def __repr__(self):
        selector = type(self)._method_selector_for_rate(self.rate)
        return (
            f'{type(self).__name__}.{selector}'
            f'({self._inputs[0]}, {len(self._channels)})')


class In(AbstractIn):
    @classmethod
    def ar(cls, bus=0, channels=1):
        return cls._multi_new('audio', channels, bus)

    @classmethod
    def kr(cls, bus=0, channels=1):
        return cls._multi_new('control', channels, bus)

    def _init_ugen(self, channels, *arg_bus):  # override
        self._inputs = arg_bus
        return self._init_outputs(channels, self.rate)


class LocalIn(AbstractIn):
    @classmethod
    def ar(cls, channels=1, default=0.0):
        return cls._multi_new('audio', channels, *utl.as_list(default))

    @classmethod
    def kr(cls, channels=1, default=0.0):
        return cls._multi_new('control', channels, *utl.as_list(default))

    def _init_ugen(self, channels, *default):  # override
        self._inputs = utl.wrap_extend(default, channels)
        return self._init_outputs(channels, self.rate)

    def __repr__(self):
        selector = type(self)._method_selector_for_rate(self.rate)
        return (
            f'{type(self).__name__}.{selector}'
            f'({len(self._channels)}, {list(self._inputs)})')


class LagIn(AbstractIn):
    _default_rate = 'control'

    @classmethod
    def kr(cls, bus=0, channels=1, lag=0.1):
        return cls._multi_new('control', channels, bus, lag)

    def _init_ugen(self, channels, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(channels, self.rate)

    def __repr__(self):
        selector = type(self)._method_selector_for_rate(self.rate)
        return (
            f'{type(self).__name__}.{selector}'
            f'({self._inputs[0]}, {len(self._channels)}, {self._inputs[1]})')


class InFeedback(AbstractIn):
    @classmethod
    def ar(cls, bus=0, channels=1):
        return cls._multi_new('audio', channels, bus)

    def _init_ugen(self, channels, *arg_bus):  # override
        self._inputs = arg_bus
        return self._init_outputs(channels, self.rate)


class InTrig(AbstractIn):
    @classmethod
    def kr(cls, bus=0, channels=1):
        return cls._multi_new('control', channels, bus)

    def _init_ugen(self, channels, *arg_bus):  # override
        self._inputs = arg_bus
        return self._init_outputs(channels, self.rate)


class SoundIn(ugn.PseudoUGen):
    @classmethod
    def ar(cls, bus=0):
        channel_offset = ifu.NumOutputBuses.ir()
        if not isinstance(bus, list):
            return In.ar(channel_offset + bus, 1)
        # Check for a list of consecutive numbers [n,n+1,n+2...].
        if all(isinstance(x, (int, float)) for x in bus)\
        and all(a + 1 == b for a, b in utl.pairwise(bus)):
            return In.ar(channel_offset + bus[0], len(bus))
        else:
            # // Allow In to multi channel expand.
            return In.ar([channel_offset + item for item in bus])


### Outputs ###

class AbstractOut(ugn.SynthObject):
    def _num_outputs(self):  # override
        return 0

    def _write_output_specs(self, file):  # override
        pass  # No output signal.

    def _check_inputs(self):  # override
        if self.rate == 'audio':
            for i in range(type(self)._num_fixed_args(), len(self.inputs)):
                if gpp.ugen_param(self.inputs[i])._as_ugen_rate() != 'audio':
                    return (f'input at index {i} is not audio rate')
        elif len(self.inputs) <= type(self)._num_fixed_args():
            return 'missing input at index 1'
        return self._check_valid_inputs()

    # def is_output_ugen(cls):  # See AbstractControl note.

    @classmethod
    def _num_fixed_args(cls):
        raise NotImplementedError('subclass responsibility')

    def _num_audio_channels(self):  # Type relative SynthDesc interface
        return len(self.inputs) - type(self)._num_fixed_args()


    ### SynthDesc interface ###

    # def _writes_to_bus(self):
    #     return True


class Out(AbstractOut):
    @classmethod
    def ar(cls, bus, output):
        output = gpp.ugen_param(utl.as_list(output))
        output = output._as_ugen_input(cls)
        output = cls._replace_zeroes_with_silence(output)
        cls._multi_new('audio', bus, *output)
        # return 0.0  # // Out has no output.

    @classmethod
    def kr(cls, bus, output):
        cls._multi_new('control', bus, *utl.as_list(output))
        # return 0.0  # // Out has no output.

    @classmethod
    def _num_fixed_args(cls):
        return 1


class ReplaceOut(Out):
    pass


class OffsetOut(Out):
    @classmethod
    def kr(cls, bus, output):
        raise NotImplementedError(
            f'{cls.__name__} should not implement kr constructor')


class LocalOut(AbstractOut):
    @classmethod
    def ar(cls, output):
        output = gpp.ugen_param(utl.as_list(output))
        output = output._as_ugen_input(cls)
        output = cls._replace_zeroes_with_silence(output)
        cls._multi_new('audio', *output)
        # return 0.0  # // LocalOut has no output.

    @classmethod
    def kr(cls, output):
        output = utl.as_list(output)
        cls._multi_new('audio', *output)
        # return 0.0  # // LocalOut has no output.

    @classmethod
    def _num_fixed_args(cls):
        return 0


    ### SynthDesc interface ###

    # def _writes_to_bus(self):
    #     return False


class XOut(AbstractOut):
    @classmethod
    def ar(cls, bus, xfade, output):
        output = gpp.ugen_param(utl.as_list(output))
        output = output._as_ugen_input(cls)
        output = cls._replace_zeroes_with_silence(output)
        cls._multi_new('audio', bus, xfade, *output)
        # return 0.0  # // XOut has no output.

    @classmethod
    def kr(cls, bus, xfade, output):
        output = utl.as_list(output)
        cls._multi_new('control', bus, xfade, *output)
        # return 0.0  # // XOut has no output.

    @classmethod
    def _num_fixed_args(cls):
        return 2
