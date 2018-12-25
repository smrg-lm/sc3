"""BasicOpUGens.sc"""

import supercollie.ugens as ug
import supercollie.utils as ut
import supercollie._specialindex as si


class BasicOpUGen(ug.UGen):
    def __init__(self):
        super().__init__()
        self._operator = None

    # TODO: El método writeName está comentado en el original. Agregar comentado.

    @property
    def operator(self):
        return self._operator

    @operator.setter
    def operator(self, value):
        self._operator = value
        # TODO: línea de abajo comentada, ver cuáles y cómo son los operadores sportados por el servidor y cómo traducir desde Python __mul__, __rmul__, etc.
        #self.special_index = si.special_index(value) # TODO: en inout.py hace: self.special_index = len(self.synthdef.controls) # TODO: VER, esto se relaciona con _Symbol_SpecialIndex como?
        if self.special_index < 0:
            msg = "Operator '{}' applied to a UGen is not supported by the server" # TODO: ver cuáles son los soportados por el servidor porque Symbol responde a muchos más. # Cambié scsynth por server
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
            if a == 0.0: return 0.0
            if b == 0.0: return 0.0
            if a == 1.0: return b
            if a == -1.0: return -b #.neg() # TODO: esto sería neg(b) si los operatores unarios se convierten en funciones.
            if b == 1.0: return a
            if b == -1.0: return -a #.neg() # TODO: ídem. Además, justo este es neg. UGen usa AbstractFunction __neg__ para '-'
        if selector is '+':
            if a == 0.0: return b
            if b == 0.0: return a
        if selector is '-':
            if a == 0.0: return b.neg() # TODO: Ídem -a, -b, VER
            if b == 0.0: return a
        if selector is '/':
            if b == 1.0: return a
            if b == -1.0: return a.neg()
        return super().new1(rate, selector, a, b)

    @classmethod
    def new(cls, selector, a, b):
        return cls.multi_new('audio', selector, a, b)

    def init_ugen(self, operator, a, b):
        self.operator = operator
        self.rate = self.determine_rate(a, b)
        self.inputs = (a, b) # TODO: ver, acá es una tupla como en ugens.py, complica las cosas?
        return self # TIENEN QUE DEVOLVER SELF

    def determine_rate(self, a, b):
        # El orden es importante.
        if ug.as_ugen_rate(a) is 'demand': return 'demand'
        if ug.as_ugen_rate(b) is 'demand': return 'demand'
        if ug.as_ugen_rate(a) is 'audio': return 'audio'
        if ug.as_ugen_rate(b) is 'audio': return 'audio'
        if ug.as_ugen_rate(a) is 'control': return 'control'
        if ug.as_ugen_rate(b) is 'control': return 'control'
        return 'scalar'

    def optimize_graph(self):
        # OC: this.constantFolding;
        if self.perform_dead_code_elimination(): # llama a super, pero no sobreescribe, y en Python no es necesario tampoco práctico.
            return self
        if self.operator is '+':
            self.optimize_add()
            return self
        if self.operator is '-':
            self.optimize_sub()
            return self

    def optimize_add(self):
        # OC: create a Sum3 if possible
        optimized_ugen = self.optimize_to_sum3()
        # OC: create a Sum4 if possible
        if not optimized_ugen:
            optimized_ugen = self.optimize_to_sum4()
        # OC: create a MulAdd if possible.
        if not optimized_ugen:
            optimized_ugen = self.optimize_to_muladd()
        # OC: optimize negative additions
        if not optimized_ugen:
            optimized_ugen = self.optimize_addneg()

        if optimized_ugen:
            self.synthdef.replace_ugen(self, optimized_ugen)

    # L239
    def optimize_to_sum3(self):
        a, b = self.inputs
        if ug.as_ugen_rate(a) is 'demand' or ug.as_ugen_rate(b) is 'demand':
            return None

        if isinstance(a, BinaryOpUGen) and a.operator is '+'\
            and len(a.descendants) is 1:
            self.synthdef.remove_ugen(a)
            replacement = Sum3.new(a.inputs[0], a.inputs[1], b) # .descendants_(descendants);
            replacements.descendants = self.descendants
            self.optimize_update_descendants(replacement, a)
            return replacement

        # Ídem b... lo único que veo es que retornan y que la función debería devolver un valor comprobable para luego retornoar.
        if isinstance(b, BinaryOpUGen) and b.operator is '+'\
            and len(b.descendants) is 1:
            self.synthdef.remove_ugen(b)
            replacement = Sum3.new(b.inputs[0], b.inputs[1], a)
            replacement.descendants = self.descendants
            self.optimize_update_descendants(replacement, b)
            return replacement

        return None

    # L262
    def optimize_to_sum4(self):
        a, b = self.inputs
        if ug.as_ugen_rate(a) is 'demand' or ug.as_ugen_rate(b) is 'demand':
            return None

        if isinstance(a, Sum3) and len(a.descendants) is 1:
            self.synthdef.remove_ugen(a)
            replacement = Sum4.new(a.inputs[0], a.inputs[1], a.inputs[2], b)
            replacement.descendants = self.descendants
            self.optimize_update_descendants(replacement, a)
            return replacement

        if isinstance(b, Sum3) and len(b.descendants) is 1:
            self.synthdef.remove_ugen(b)
            replacement = Sum4.new(b.inputs[0], b.inputs[1], b.inputs[2], a)
            replacement.descendants = self.descendants
            self.optimize_update_descendants(replacement, b)
            return replacement

        return None

    # L197
    def optimize_to_muladd(self):
        a, b = self.inputs

        if isinstance(a, BinaryOpUGen) and a.operator is '*'\
            and len(a.descendants) is 1:

            if MulAdd.can_be_muladd(a.inputs[0], a.inputs[1], b):
                self.synthdef.remove_ugen(a)
                replacement = MulAdd.new(a.inputs[0], a.inputs[1], b)
                replacement.descendants = self.descendants
                self.optimize_update_descendants(replacement, a)
                return replacement

            if MulAdd.can_be_muladd(a.inputs[1], a.inputs[0], b):
                self.synthdef.remove_ugen(a)
                replacement = MulAdd.new(a.inputs[1], a.inputs[0], b)
                replacement.descendants = self.descendants
                self.optimize_update_descendants(replacement, a)
                return replacement

        # does optimization code need to be optimized?
        if isinstance(b, BinaryOpUGen) and b.operator is '*'\
            and len(b.descendants) is 1:

            if MulAdd.can_be_muladd(b.inputs[0], b.inputs[1], a):
                self.synthdef.remove_ugen(b)
                replacement = MulAdd.new(b.inputs[0], b.inputs[1], a)
                replacement.descendants = self.descendants
                self.optimize_update_descendants(replacement, b)
                return replacement

            if MulAdd.can_be_muladd(b.inputs[1], b.inputs[0], a):
                self.synthdef.remove_ugen(b)
                replacement = MulAdd.new(b.inputs[1], b.inputs[0], a)
                replacement.descendants = self.descendants
                self.optimize_update_descendants(replacement, b)
                return replacement

        return None

    # L168
    def optimize_addneg(self):
        a, b = self.inputs

        if isinstance(b, UnaryOpUGen) and b.operator is 'neg'\
            and len(b.descendants) is 1:
            # OC: a + b.neg -> a - b
            self.synthdef.remove_ugen(b)
            replacement = a - b.inputs[0]
            # OC: this is the first time the dependants logic appears. It's repeated below.
            # We will remove 'this' from the synthdef, and replace it with 'replacement'.
            # 'replacement' should then have all the same descendants as 'this'.
            replacement.descendants = self.descendants
            # OC: drop 'this' and 'b' from all of replacement's inputs' descendant lists
            # so that future optimizations decide correctly
            self.optimize_update_descendants(replacement, b)
            return replacement

        if isinstance(a, UnaryOpUGen) and a.operator is 'neg'\
            and len(a.descendants) is 1:
            # OC: a.neg + b -> b - a
            self.synthdef.remove_ugen(a)
            replacement = b - a.inputs[0]
            replacement.descendants = self.descendants
            self.optimize_update_descendants(replacement, a)
            return replacement

        return None

    # L283
    def optimize_sub(self):
        a, b = self.inputs

        if isinstance(b, UnaryOpUGen) and b.operator is 'neg'\
            and len(b.descendants) is 1:
            # OC: a - b.neg -> a + b
            self.synthdef.remove_ugen(b)
            replacement = BinaryOpUGen.new('+', a, b.inputs[0])
            replacement.descendants = self.descendants
            self.optimize_update_descendants(replacement, b)
            self.synthdef.replace_ugen(self, replacement)
            replacement.optimize_graph() # OC: not called from optimizeAdd; no need to return ugen here

        return None

    # L151
    # OC: 'this' = old ugen being replaced
    # replacement = this's replacement
    # deletedUnit = auxiliary unit being removed, not replaced
    def optimize_update_descendants(self, replacement, deleted_unit):
        def replace_func(ugen):
            if isinstance(ugen, UGen):
                desc = ugen.descendants
                desc.add(replacement)
                desc.remove(self)
                desc.remove(deleted_unit)

        for input in replacement.inputs:
            replace_func(input)
            if isinstance(input, OutputProxy):
                replace_func(input.source_ugen)

    # L301
    def constant_folding(self): # No sé si se usa este método, tal vez fue reemplazado porque está comentada la llamada arriba, pero no está comentado.
        pass # TODO, boring to copy


class MulAdd(ug.UGen):
    @classmethod
    def new(cls, input, mul=1.0, add=0.0):
        args = ug.as_ugen_input([input, mul, add], cls)
        rate = ug.as_ugen_rate(args)
        return cls.multi_new_list([rate] + args)

    @classmethod
    def new1(cls, rate, input, mul, add):
        # OC: eliminate degenerate cases
        if mul == 0.0: return add
        minus = mul == -1.0
        nomul = mul == 1.0
        noadd = add == 0.0
        if nomul and noadd: return input
        if minus and noadd: return input.neg() # TODO: ES POSIBLE QUE PUEDA NO SER UNA UGEN?
        if noadd: return input * mul
        if minus: return add - input
        if nomul: return input + add

        if cls.can_be_muladd(input, mul, add):
            return super().new1(rate, input, mul, add)
        if cls.can_be_muladd(mul, input, add):
            return super().new1(rate, mul, input, add)
        return (input * mul) + add

    def init_ugen(self, input, mul, add):
        self.inputs = [input, mul, add]
        self.rate = ug.as_ugen_rate(self.inputs)
        return self

    @classmethod
    def can_be_muladd(cls, input, mul, add):
        # OC: see if these inputs satisfy the constraints of a MulAdd ugen.
        if input.rate is 'audio': # TODO: ES POSIBLE QUE PUEDA NO SER UNA UGEN? ug.as_ugen_rate?
            return True
        mul_rate = ug.as_ugen_rate(mul)
        add_rate = ug.as_ugen_rate(add)
        if input.rate is 'control'\
            and (mul_rate is 'control' or mul_rate is 'scalar')\
            and (add_rate is 'control' or add_rate is 'scalar'):
            return True
        return False


class Sum3(ug.UGen):
    @classmethod
    def new(cls, in0, in1, in2):
        return cls.multi_new(None, in0, in1, in2)

    @classmethod
    def new1(cls, dummy_rate, in0, in1, in2):
        if in2 == 0.0: return in0 + in1
        if in1 == 0.0: return in0 + in2
        if in0 == 0.0: return in1 + in2

        arg_array = [in0, in1, in2]
        rate = ug.as_ugen_rate(arg_array)
        sorted_args = arg_array.sort(key=lambda x: x.rate) # Esto depende de la comparación entre strings, es así en sclang pero no es UGen.rate_number, no sé para qué ordena.

        return super().new1(rate, *sorted_args)


class Sum4(ug.UGen):
    @classmethod
    def new(cls, in0, in1, in2, in3):
        return cls.multi_new(None, in0, in1, in2, in3)

    @classmethod
    def new1(cls, in0, in1, in2, in3):
        if in0 == 0.0: return Sum3.new1(nil, in1, in2, in3)
        if in1 == 0.0: return Sum3.new1(nil, in0, in2, in3)
        if in2 == 0.0: return Sum3.new1(nil, in0, in1, in3)
        if in3 == 0.0: return Sum3.new1(nil, in0, in1, in2)

        arg_array = [in0, in1, in2, in3]
        rate = ug.as_ugen_rate(arg_array)
        sorted_args = arg_array.sort(key=lambda x: x.rate) # Esto depende de la comparación entre strings, es así en sclang pero no es UGen.rate_number, no sé para qué ordena.

        return super().new1(rate, *sorted_args)
