"""InOut.sc"""

import warnings

import supercollie.ugens as ug
import supercollie._global as _gl
import supercollie.utils as ut


# Controls

class ControlName():
    def __init__(self, name, index, rate, default_value, arg_num, lag):
        self.name = name
        self.index = index
        self.rate = rate
        self.default_value = default_value
        self.arg_num = arg_num
        self.lag = lag or 0.0

    def num_channels(self):
        return len(ut.as_list(self.default_value))

    def print_on(self, stream):
        pass # TODO: VER, este método es de la librería de clases, define la representación para imprimir, acá puede que sea repr?


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
                ControlName(name, index + i, 'control',
                    None, synthdef.all_control_names))

    @classmethod
    def ir(cls, values):
        return cls.multi_new_list(['scalar'] + ut.as_list(values))

    @classmethod
    def kr(cls, values):
        return cls.multi_new_list(['control'] + ut.as_list(values))

    def init_ugen(self, *values):
        self.values = list(values)
        if self.synthdef:
            self.special_index = len(self.synthdef.controls) # TODO: VER, esto se relaciona con _Symbol_SpecialIndex como?
            self.synthdef.controls.extend(self.values)

            ctl_names = self.synthdef.control_names
            if ctl_names:
                # OC: current control is always the last added, so:
                last_control = ctl_names[len(ctl_names) - 1] # VER: si no hay un método como last o algo así.
                if not last_control.default_value:
                    # OC: only write if not there yet:
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
                ControlName(name, index + i, 'audio',
                    None, synthdef.all_control_names))

    @classmethod
    def ar(cls, values):
        return cls.multi_new_list(['audio'] + ut.as_list(values))

    def init_ugen(self, *values):
        self.values = list(values)
        if self.synthdef:
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
    def ir(cls):
        msg = '{} should not implemet ir constructor'
        raise NotImplementedError(msg.format(cls.__name__))

    @classmethod
    def kr(cls, values, lags):
        values = ut.as_list(values)
        if isinstance(lags, (int, float)): # isNumber
            lags = [lags] * len(values)
        else:
            lags = ut.as_list(lags)

        if len(values) is not len(lags):
            msg = '{} len(values) is not len(lags), {}.kr returns None'
            warning.warn(msg.format(cls.__name__, cls.__name__))
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
        if self.synthdef:
            self.special_index = len(self.synthdef.controls) # TODO: VER, esto se relaciona con _Symbol_SpecialIndex como?
            self.synthdef.controls.extend(self.values)
            self.synthdef.control_index += len(self.values)
        return self.init_outputs(len(self.values), self.rate)


# Inputs

class AbstractIn(ug.MultiOutUGen):
    @classmethod
    def is_input_ugen(self):
        return True


class In(AbstractIn): pass
class LocalIn(AbstractIn): pass
class LagIn(AbstractIn): pass
class InFeedback(AbstractIn): pass
class InTrig(AbstractIn): pass


# Outputs

class AbstractOut(ug.UGen):
    def num_outputs(self):
        return 0

    def write_output_specs(self):
        pass # No implementa, VER VALOR DE RETORNO en sclang es self.

    def check_inputs(self):
        if self.rate is 'audio':
            for i in range(self.__class__.num_fixed_args(), len(self.inputs)):
                if self.inputs[i].rate is not 'audio':
                    msg = 'input at index {} ({}) is not audio rate'
                    return msg.format(i, self.inputs[i])
        elif len(self.inputs) <= self.__class_.num_fixed_args():
            return 'missing input at index 1'
        return self.check_valid_inputs()

    @classmethod
    def is_output_ugen(cls):
        return True

    @classmethod
    def num_fixed_args(cls):
        pass # VER: ^this.subclassResponsibility(thisMethod)

    def num_audio_channels(self):
        return len(self.inputs) - self.__class__.num_fixed_args()

    def writes_to_bus(self):
        pass # VER: ^this.subclassResponsibility(thisMethod)


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


class ReplaceOut(Out): pass # No hace nada.
class OffsetOut(Out): pass
class LocalOut(AbstractOut): pass
class XOut(AbstractOut): pass
