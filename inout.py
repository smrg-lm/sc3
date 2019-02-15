"""InOut.sc"""

import warnings

import supercollie.ugens as ug
import supercollie._global as _gl
import supercollie.utils as ut


# Controls

class ControlName():
    def __init__(self, name, index, rate, default_value, arg_num, lag=None):
        self.name = name
        self.index = index
        self.rate = rate
        self.default_value = default_value
        self.arg_num = arg_num
        self.lag = lag or 0.0

    def num_channels(self):
        return len(ut.as_list(self.default_value))

    #def print_on(self, stream):
    def __str__(self):
        string = 'ControlName P ' + str(self.index)
        if self.name is not None: string += ' ' + self.name
        if self.rate is not None: string += ' ' + self.rate
        if self.default_value is not None: string += ' ' + str(self.default_value)
        return string


class Control(ug.MultiOutUGen):
    def __init__(self):
        super().__init__()
        self.values = []

    @classmethod
    def names(cls, names):
        synthdef = _gl.current_synthdef
        index = synthdef.control_index
        names = ut.as_list(names)
        for i, name in enumerate(names):
            synthdef.add_control_name(
                ControlName(
                    name, index + i, 'control',
                    None, synthdef.all_control_names
                )
            )

    @classmethod
    def ir(cls, values):
        return cls.multi_new_list(['scalar'] + ut.as_list(values))

    @classmethod
    def kr(cls, values):
        return cls.multi_new_list(['control'] + ut.as_list(values))

    def init_ugen(self, *values):
        self.values = list(values)
        if self.synthdef is not None:
            self.special_index = len(self.synthdef.controls) # TODO: VER, esto se relaciona con _Symbol_SpecialIndex como?
            self.synthdef.controls.extend(self.values)

            ctl_names = self.synthdef.control_names
            if len(ctl_names) > 0:
                # // current control is always the last added, so:
                last_control = ctl_names[len(ctl_names) - 1] # VER: si no hay un método como last o algo así.
                if last_control.default_value is None:
                    # // only write if not there yet:
                    last_control.default_value = ut.unbubble(self.values)

            self.synthdef.control_index += len(self.values)
        return self.init_outputs(len(self.values), self.rate)

    @classmethod
    def is_control_ugen(cls):
        return True


class AudioControl(ug.MultiOutUGen):
    def __init__(self):
        super().__init__()
        self.values = []

    @classmethod
    def names(cls, names):
        synthdef = _gl.current_synthdef # VER: lo mimso que arriba, es local, luego init_ugen llama a self.synthdef, supongo que se inicializa en las subclases.
        index = synthdef.control_index
        names = ut.as_list(names)
        for i, name in enumerate(names):
            synthdef.add_control_name(
                ControlName(
                    name, index + i, 'audio',
                    None, synthdef.all_control_names
                )
            )

    @classmethod
    def ar(cls, values):
        return cls.multi_new_list(['audio'] + ut.as_list(values))

    def init_ugen(self, *values):
        self.values = list(values)
        if self.synthdef is not None:
            self.special_index = len(self.synthdef.controls) # TODO: VER, esto se relaciona con _Symbol_SpecialIndex como?
            self.synthdef.controls.extend(self.values)
            self.synthdef.control_index += len(self.values)
        return self.init_outputs(len(self.values), self.rate)

    @classmethod
    def is_audio_control_ugen(cls):
        return True

    @classmethod
    def is_control_ugen(cls):
        return True


class TrigControl(Control): pass # No hace nada especial.


class LagControl(Control):
    @classmethod
    def ir(cls, values):
        msg = '{} should not implemet ir constructor' # TODO: ver en qué casos se puede llamar, porque acá le agregué los argumentos si no tira error.
        raise NotImplementedError(msg.format(cls.__name__))

    @classmethod
    def kr(cls, values, lags):
        values = ut.as_list(values)
        if isinstance(lags, (int, float)): # isNumber
            lags = [lags] * len(values)
        else:
            lags = ut.as_list(lags)

        if len(values) != len(lags):
            msg = '{} len(values) is not len(lags), {}.kr returns None'
            warnings.warn(msg.format(cls.__name__, cls.__name__))
            return None

        n = 16
        values = [values[i:i + n] for i in range(0, len(values), n)] # values.clump(16)
        lags = [lags[i:i + n] for i in range(0, len(lags), n)] # lags.clump(16)
        outputs = []
        for i in range(len(values)):
            outputs.extend(cls.multi_new_list(['control'] + values[i] + lags[i]))
        return outputs

    @classmethod
    def ar(cls, values, lags):
        return AudioControl.ar(values).lag(lags) # TODO: lag es un operador definido en UGen.

    def init_ugen(self, *stuff):
        # declara la variable lags y no la usa.
        size = len(stuff)
        size2 = size >> 1 # size // 2
        self.values = list(stuff)[size2:size] # en Python es la cantidad de elementos desde, no el índice.
        if self.synthdef is not None:
            self.special_index = len(self.synthdef.controls) # TODO: VER, esto se relaciona con _Symbol_SpecialIndex como?
            self.synthdef.controls.extend(self.values)
            self.synthdef.control_index += len(self.values)
        return self.init_outputs(len(self.values), self.rate)


# Inputs

class AbstractIn(ug.MultiOutUGen):
    @classmethod
    def is_input_ugen(self):
        return True


class In(AbstractIn):
    @classmethod
    def ar(cls, bus=0, num_channels=1):
        return cls.multi_new('audio', num_channels, bus)

    @classmethod
    def kr(cls, bus=0, num_channels=1):
        return cls.multi_new('control', num_channels, bus)

    def init_ugen(self, num_channels, *arg_bus):
        self.inputs = arg_bus # TODO: es tupla, en sclang es nil si no hay inputs.
        return self.init_outputs(num_channels, self.rate)


class LocalIn(AbstractIn):
    @classmethod
    def ar(cls, num_channels=1, default=0.0):
        return cls.multi_new('audio', num_channels, *ut.as_list(default))

    @classmethod
    def kr(cls, num_channels=1, default=0.0):
        return cls.multi_new('control', num_channels, *ut.as_list(default))

    def init_ugen(self, num_channels, *default):
        self.inputs = tuple(ut.wrap_extend(list(default), num_channels)) # TODO: es tupla, en sclang es nil si no hay inputs.
        return self.init_outputs(num_channels, self.rate)


class LagIn(AbstractIn):
    @classmethod
    def kr(cls, bus=0, num_channels=1, lag=0.1):
        return cls.multi_new('control', num_channels, bus, lag)

    def init_ugen(self, num_channels, *inputs):
        self.inputs = inputs # TODO: es tupla, en sclang es nil si no hay inputs. Quité as list
        return self.init_outputs(num_channels, self.rate)


class InFeedback(AbstractIn):
    @classmethod
    def ar(cls, bus=0, num_channels=1):
        return cls.multi_new('audio', num_channels, bus)

    def init_ugen(self, num_channels, *arg_bus):
        self.inputs = arg_bus # TODO: es tupla, en sclang es nil si no hay inputs.
        return self.init_outputs(num_channels, self.rate)


class InTrig(AbstractIn):
    @classmethod
    def kr(cls, bus=0, num_channels=1):
        return cls.multi_new('control', num_channels, bus)

    def init_ugen(self, num_channels, *arg_bus):
        self.inputs = arg_bus # TODO: es tupla, en sclang es nil si no hay inputs.
        return self.init_outputs(num_channels, self.rate)


# Outputs

class AbstractOut(ug.UGen):
    def num_outputs(self):
        return 0

    def write_output_specs(self, file):
        pass # Se define como no hacer nada porque las ugens que escriben a buses no tienen señales de salida (cables internos). Es interfaz de polimorfismo desde UGen.

    def check_inputs(self):
        if self.rate == 'audio':
            for i in range(self.__class__.num_fixed_args(), len(self.inputs)): # TODO: es tupla, en sclang es nil si no hay inputs.
                if ug.as_ugen_rate(self.inputs[i]) != 'audio':
                    msg = '{}:'.format(self.__class__.__name__)
                    msg += ' input at index {} ({}) is not audio rate'
                    return msg.format(i, self.inputs[i].__class__.__name__) # TODO: Si es OutputProxy que imprima source_ugen
        elif len(self.inputs) <= self.__class_.num_fixed_args(): # TODO: es tupla, en sclang es nil si no hay inputs.
            return 'missing input at index 1'
        return self.check_valid_inputs()

    @classmethod
    def is_output_ugen(cls):
        return True

    @classmethod
    def num_fixed_args(cls):
        pass # TODO: VER: ^this.subclassResponsibility(thisMethod)

    def num_audio_channels(self):
        return len(self.inputs) - self.__class__.num_fixed_args() # TODO: es tupla, en sclang es nil si no hay inputs.

    def writes_to_bus(self):
        pass # BUG: VER: ^this.subclassResponsibility(thisMethod) se usa en SynthDesc:outputData se implementa en varias out ugens. Es método de interfaz/protocolo de UGen, creo.


class Out(AbstractOut):
    @classmethod
    def ar(cls, bus, channels_list):
        channels_list = cls.replace_zeroes_with_silence(
            ut.as_list(ug.as_ugen_input(channels_list, cls)))
        cls.multi_new_list(['audio', bus] + ut.as_list(channels_list))
        return 0.0

    @classmethod
    def kr(cls, bus, channels_list):
        cls.multi_new_list(['control', bus] + ut.as_list(channels_list))
        return 0.0

    @classmethod
    def num_fixed_args(cls):
        return 1

    def writes_to_bus(self):
        return True


class ReplaceOut(Out): pass # No hace nada espcial.


class OffsetOut(Out):
    @classmethod
    def kr(cls, bus, channels_list):
        msg = '{} should not implemet kr constructor' # TODO: ver en qué casos se puede llamar, porque acá le agregué los argumentos si no tira error.
        raise NotImplementedError(msg.format(cls.__name__))


class LocalOut(AbstractOut):
    @classmethod
    def ar(cls, channels_list):
        channels_list = ug.as_ugen_input(channels_list, cls)
        channels_list = ut.as_list(channels_list)
        channels_list = cls.replace_zeroes_with_silence(channels_list)
        cls.multi_new_list(['audio'] + channels_list)
        return 0.0 # OC: LocalOut has no output.

    @classmethod
    def kr(cls, channels_list):
        channels_list = ut.as_list(channels_list)
        cls.multi_new_list(['audio'] + channels_list)
        return 0.0 # OC: LocalOut has no output.

    @classmethod
    def num_fixed_args(cls):
        return 0

    def writes_to_bus(self):
        return False


class XOut(AbstractOut):
    @classmethod
    def ar(cls, bus, xfade, channels_list):
        channels_list = ug.as_ugen_input(channels_list, cls)
        channels_list = ut.as_list(channels_list)
        channels_list = cls.replace_zeroes_with_silence(channels_list)
        cls.multi_new_list(['audio', bus, xfade] + channels_list)
        return 0.0 # OC: Out has no output.

    @classmethod
    def kr(cls, bus, xfade, channels_list):
        channels_list = ut.as_list(channels_list)
        cls.multi_new_list(['control', bus, xfade] + channels_list)
        return 0.0 # OC: Out has no output.

    @classmethod
    def num_fixed_args(cls):
        return 2

    def writes_to_bus(self):
        return True
