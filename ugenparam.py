"""Support for built in or extensions data types as UGen parameters."""

from math import isnan
import struct


def ugen_param(obj):
    import supercollie.ugens as ugn

    if isinstance(obj, (UGenParameter, ugn.UGen)):
        return obj
    new_cls = None
    for sub_class in UGenParameter.__subclasses__():
        if isinstance(obj, sub_class.param_type()):
            new_cls = sub_class
            break
    if new_cls is None:
        msg = "UGenParameter: type '{}' not supported"
        raise TypeError(msg.format(type(value).__name__))
    return new_cls(obj)


class UGenParameter():
    # def __new__(cls, value):
    #     if isinstance(value, (UGenParameter, UGen)):
    #         return value
    #     new_cls = None
    #     for sub_class in UGenParameter.__subclasses__():
    #         if isinstance(value, sub_class.type()):
    #             new_cls = sub_class
    #             break
    #     if new_cls is None:
    #         msg = "UGenParameter: type '{}' not supported"
    #         raise TypeError(msg.format(type(value).__name__))
    #     obj = super().__new__(new_cls)
    #     return obj

    def __init__(self, value):
        # if self is value: return
        self.__value = value

    # def __repr__(self):
    #     return "{}({})".format(type(self).__name__, repr(self.value))

    @property
    def value(self): # TODO: tal vez sería mejor que se llame param_value
        return self.__value

    ### Interface ###

    def param_type(cls):
        return (cls,)

    def madd(self, mul=1.0, add=0.0):
        msg = "madd can't be applied to '{}'"
        raise TypeError(msg.format(type(self.value).__name__))

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
            msg = "'{}' must implement rate attribute or as_ugen_rate method"
            raise AttributeError(msg.format(type(self).__name__)) from e

    def perform_binary_op_on_ugen(self, selector, thing):
        if selector == '==':
            return False
        if selector == '!=':
            return True
        msg = "operations between ugens and '{}' ('{}') are not implemented"
        raise NotImplementedError(msg.format(type(input).__name__, input))

    def write_input_spec(self, file, synthdef):
        msg = "'{}' does not implement write_input_spec"
        raise NotImplementedError(msg.format(type(self).__name__))


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

    def madd(self, mul=1.0, add=0.0):
        res = (self.value * mul) + add
        if isinstance(res, UGen):
            return res
        return self.value

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
            msg = 'write_input_spec constant not found: {}'
            raise Exception(msg.format(float(self.value))) from e


class UGenList(UGenParameter):
    @classmethod
    def param_type(cls):
        return (list, tuple)

    # BUG: array implementa num_channels?

    def madd(obj, mul=1.0, add=0.0):
        return MulAdd.new(obj, mul, add) # TODO: Tiene que hacer expansión multicanal, es igual a UGen. VER: qué pasa con MulAdd args = as_ugen_input([input, mul, add], cls)

    def is_valid_ugen_input(self):
        return True

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
        if any(x is None for x in lst): # TODO: reduce con Collection minItem, los símbolos por orden lexicográfico, si algún elemento es nil devuelve nil !!!
            return None
        return min(lst)

    def write_input_spec(self, file, synthdef):
        for item in self.value:
            ugen_param(item).write_input_spec(file, synthdef)
