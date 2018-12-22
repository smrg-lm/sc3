"""BasicOpUGens.sc"""

import supercollie.ugens as ug
import supercollie.utils as ut


class BasicOpUGen(ug.UGen):
    def __init__(self):
        super().__init__()
        self._operator = None

    @property
    def operator(self):
        return self._operator

    @operator.setter
    def operator(self, value):
        self._operator = value # op es un símbolo en sclang, el método op.specialIndex llama a _Symbol_SpecialIndex // used by BasicOpUGens to get an ID number for the operator
        self.special_index = special_index(value) # TODO: en inout.py hace: self.special_index = len(self.synthdef.controls) # TODO: VER, esto se relaciona con _Symbol_SpecialIndex como?
        if self.special_index < 0:
            msg = "Operator '{}' applied to a UGen is not supported by the server" # Cambié scsynth por server
            raise Exception(msg.format(value))

    @operator.deleter
    def operator(self):
        del self._operator

    #argNamesInputsOffset # VER: estos métodos no se cambian acá porque estoy usando *new* que no es __init__ en Python y no incluye this/self como primer argumento. sclang hace lo mismo que Python con new, argNames devuevle [this, ...] para Meta_Object*new
    #argNameForInputAt

    def dump_args(self):
        msg = 'ARGS:\n'
        tab = ' ' * 4
        msg += tab + 'operator: ' + self.operator + '\n'
        arg_name = None
        for i, input in enumerate(self.inputs):
            arg_name = self.arg_name_for_input_at(i)
            if not arg_name: arg_name = str(i)
            msg += tab + arg_name + ' ' + str(input)
            msg += ' ' + self.__class__.__name__ + '\n'
        print(msg, end='')

    def dump_name(self):
        return str(self.synth_index) + '_' + self.operator


class UnaryOpUGen(BasicOpUGen):
    @classmethod
    def new(cls, selector, a):
        return cls.multi_new('audio', selector, a)

    def init_ugen(self, operator, input):
        self.operator = operator
        self.rate = input.rate
        self.inputs = tuple(ut.as_array(input)) # TODO: ver, acá es una tupla como en ugens.py, complica las cosas?
        return self # TIENEN QUE DEVOLVER SELF

    def optimize_graph(self):
        self.perform_dead_code_elimination() # VER: creo que no es necesario llamar a super, lo mismo que en ugens.PureUGen.


class BinaryOpUGen(BasicOpUGen):
    @classmethod
    def new1(cls, rate, selector, a, b):
        # OC: eliminate degenerate cases
        if selector is '*':
            if a is 0.0: return 0.0
            if b is 0.0: return 0.0
            if a is 1.0: return b
            if a is -1.0: return -b #.neg() # TODO: esto sería neg(b) si los operatores unarios se convierten en funciones.
            if b is 1.0: return a
            if b is -1.0: return -a #.neg() # TODO: ídem. Además, justo este es neg. UGen usa AbstractFunction __neg__
        if selector is '+':
            if a is 0.0: return b
            if b is 0.0: return a
        if selector is '-':
            if a is 0.0: return b.neg()
            if b is 0.0: return a
        if selector is '/':
            if b is 1.0: return a
            if b is -1.0: return a.neg()
        return super().new1(rate, selector, a, b) # TODO: es así la llamada acá en clase?

    @classmethod
    def new(cls, selector, a, b):
        return cls.multi_new('audio', selector, a, b)

    def init_ugen(self, operator, a, b):
        self.operator = operator
        self.rate = self.determine_rate(a, b)
        self.inputs = (a, b) # TODO: ver, acá es una tupla como en ugens.py, complica las cosas?
        return self # TIENEN QUE DEVOLVER SELF

    def determine_rate(self, a, b):
        if a.rate is 'control': return 'control'
        if b.rate is 'control': return 'control'
        if a.rate is 'audio': return 'audio'
        if b.rate is 'audio': return 'audio'
        if a.rate is 'demand': return 'demand'
        if b.rate is 'demand': return 'demand'
        return 'scalar'

    # TODO: optimizaciones a partir de acá, usa las clases de abajo.


class MulAdd(ug.UGen):
    pass


class Sum3(ug.UGen):
    pass


class Sum4(ug.UGen):
    pass
