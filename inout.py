"""InOut.sc"""

from supercollie.ugens import UGen, MultiOutUGen
from supercollie.synthdef import SynthDef
from supercollie.utils import as_list, unbubble


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
        return len(as_list(self.default_value))

    def print_on(self, stream):
        pass # TODO: VER, este método es de la librería de clases, define la representación para imprimir, acá puede que sea repr?

class Control(MultiOutUGen):
    def __init__(self):
        super().__init__()
        self.values = []

    @classmethod
    def names(cls, names):
        synthdef = SynthDef._current_def
        index = synthdef.control_index
        names = as_list(names)
        for i, name in enumerate(names):
            synthdef.add_control_name(
                ControlName(name, index + i, 'control',
                    None, synthdef.all_control_names))

    @classmethod
    def ir(cls, values):
        return cls.multi_new_list(['scalar'] + values)

    @classmethod
    def kr(cls):
        return cls.multi_new_list(['control'] + values)

    def init_ugen(self, *values):
        self.values = list(values)
        if self.synthdef:
            self.special_index = len(self.synthdef.controls)
            self.synthdef.controls.extend(self.values)

            ctl_names = self.synthdef.control_names
            if ctl_names:
                # OC: current control is always the last added, so:
                last_control = synthdef.control_names[len(synthdef.control_names) - 1] # VER: si no hay un método como last o algo así.
                if not last_control.default_value:
                    # OC: only write if not there yet:
                    last_control.default_value = unbubble(self.values)

            self.synthdef.control_index += len(self.values)
        return self.init_outputs(len(self.values), self.rate)

    @classmethod
    def is_control_ugen(cls):
        return True


class AudioControl(MultiOutUGen): pass
class TrigControl(Control): pass # No hace nada.
class LagControl(Control): pass


# Inputs

class AbstractIn(MultiOutUGen):
    @classmethod
    def is_input_ugen(self):
        return True

class In(AbstractIn): pass
class LocalIn(AbstractIn): pass
class LagIn(AbstractIn): pass
class InFeedback(AbstractIn): pass
class InTrig(AbstractIn): pass


# Outputs

class AbstractOut(UGen): pass
class Out(AbstractOut): pass
class ReplaceOut(Out): pass # No hace nada.
class OffsetOut(Out): pass
class LocalOut(AbstractOut): pass
class XOut(AbstractOut): pass
