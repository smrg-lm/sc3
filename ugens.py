"""
UGens, acá se complica.

Ver la documentación de la clase UGen y otras relacionadas.
La expansión multicanal en parte está implementada en Array.
El método de instancia asUGenInput también lo implementan nodos
buses y buffers para ser pasados directamente a las ugens y
synth como ugens args. Estos métodos, tal vez, deberían estar
en otra clase que actúe como protocolo.
"""

from math import isnan
from functools import singledispatch

from supercollie.functions import AbstractFunction
from supercollie.synthdef import SynthDef
from supercollie.utils import as_list


class UGen(AbstractFunction):
    # classvar <>buildSynthDef; // the synth currently under construction,  PASADA A SynthDef._current_def y tiene un Lock

    @classmethod
    def new1(cls, rate, *args): # la verdad que see podría llamar single_new.
        '''OD: This method returns a single instance of the UGen,
        not multichannel expanded. It is called inside multi_new_list,
        whenever a new single instance is needed.

        Creo que esto era así, checkear y escribir bien:
        This method is the real 'instances' creator (aka constructor), however
        is not meant to be used but throught multi_new for the next reasons.
        In most cases it returns an ugen but may return a number instead for
        some special ugens (like controls or outpus) for different reasons.
        UGens add themselves to the SynthDef graph under constsruction later
        by calling addToSynth/SynthDef:addUgen (aka ping pong design).
        '''
        #if rate is not valid rate: # HACER LAS CONSTANTES
        #    raise TypeError('rate {} is invalid')
        obj = cls()
        obj.rate = rate
        obj.add_to_synth()
        return obj.init_ugen(*args) # debería llamarse init_ugen o algo así

    # @classmethod
    # def new_from_desc(cls, rate, numOutputs, inputs, specialIndex):
    #     pass

    @classmethod
    def multi_new(cls, *args):
        '''OD: These methods are responsible for multichannel expansion.
        They call UGen.new1(rate, *args) for each parallel combination.
        Most UGen.ar/kr methods delegate to UGen.multiNewList.

        The first argument is rate, then the rest of the arguments as
        in UGen.new1(rate, *args).
        '''
        # single channel, one ugen
        lenght = 0
        args = as_ugen_input(args, cls)
        for item in args:
            if type(item) is list:
                lenght = max(lenght, len(item))
        if lenght is 0:
            return cls.new1(*args)
        # multichannel expansion
        new_args = [None] * len(args)
        results = [None] * lenght
        for i in range(lenght): # tener en cuenta sclang #[] y `()
            for j, item in enumerate(args):
                new_args[j] = item[i % len(item)]\
                              if type(item) is list\
                              else item # hace la expansión multicanal
            results[i] = cls.multi_new(*new_args)
        return results

    # @classmethod
    # def multi_new_list(cls, args): # REMOVED
    #     '''OD: See UGen.multi_new. ESTE MÉTODO LO VOY A PASAR A MULTI_NEW Y YA.
    #     Este método debe ser privado y específico para las ugens que soportan
    #     expansión multicanal, y otras ugens pueden reimplementar multi_new,
    #     pero no sucede en la librería de clases, solo los veo en Rect,
    #     tal vez no sea la famosa dynamic geometry support.
    #     '''
    #     pass

    # Python __init__ no es sclang SynthDef init
    # acá solo puse los valores de instancia por defecto de la clase original.
    def __init__(self): # OJO: Las subclases de UGen no pueden implementar __init___ !!!
        # atributos de instancia públicos?
        self.inputs = () # en sc es un array, es una tupla acá, se inicializa en UGen.init
        self.rate = 'audio' # TODO: VER: No se puede pasar opcionalmente a new1  *** !!! hacer un enum de algún tipo !!!
        # atributos de instancia privados
        self.synthdef = None # es SynthDef._current_def luego de add_to_synth
        self.synth_index = -1
        self.opcode_id = 0 # self.specialIndex = 0; # special_index # ver nombre, esto sería opcode_id
        # topo sorting
        self.antecedents = None #set() # estos sets los inicializa SynthDef init_topo_sort, antecedents lo transforma en lista luego, por eso los dejo en none.
        self.descendants = None #set()
        self.width_first_antecedents = [] # se inicializa con SynthDef _width_first_ugens[:] que es un array

    # VER: mutabilidad. *** Este método lo sobreescriben las subclases y se llama en new1 que se llama desde multiNewList ***
    # simplemente hace lo que se ve, guarda las entradas como un Array. Se llama después de setear rate y synthDef (a través de addToSynth)
    # Pero en control names guarda otra cosa... creo que las salidas, o los índices de los controles, no sé.
    def init_ugen(self, *inputs):
        self.inputs = inputs # VER para todos los casos (otras ugens)
        return self # OJO: Tiene que retornarse sí o sí porque es el valor de retorno de new1

    # OC: You can't really copy a UGen without disturbing the Synth.
	# Usually you want the same object. This makes .dup work.
    # L45
    # def copy(self): # se usa con dup en sclang SinOsc.ar!2 opuesto a { SinOsc.ar }!2
    #     return self
    # def __copy__(self): # para Lib/copy.py module, ver si tiene utilidad
    #     return self
    def dup(self, n):
        return [self] * n

    # Desde L51 hasta L284 son, más que nada, métodos de operaciones
    # mátemáticas que aplican las ugens correspondientes, el mismo
    # principio de AbstractFunction aplicados a los ugengraphs.
    # Lueve vienen:

    # L284
    def signal_range(self):
        return 'bipolar'

    # @ { arg y; ^Point.new(this, y) } // dynamic geometry support # ??? no sé qué será ni por qué está acá en el medio...

    # L287
    def add_to_synth(self): # este método lo reimplementan OuputProxy y WidthFirstUGen
        self.synthdef = SynthDef._current_def
        if self.synthdef:
            self.synthdef.add_ugen(self)

    # L292
    def _collect_constants(self): # pong
        for input in self.inputs:
            if isinstance(input, (int, float)):
                self.synthdef.add_constant(float(input))

    # Estos métodos son de protocolo y están puestos juntitos en sc,
    # pero buscar otros que actúen de la misma manera.
    #def is_valid_ugen_input(self): # HECHO ARRIBA COMO SINGLE DISPATCH
    #def as_ugen_input(cls, *opt_arg): # HECHO ARRIBA COMO SINGLE DISPATCH
    #def as_control_input(self): # HECHO ARRIBA COMO SINGLE DISPATCH
    #def num_channels(self): # HECHO ARRIBA COMO SINGLE DISPATCH

    # L304
    # Estos métodos son interfaz pero creo que solo para las UGens, serían interfaz protejida
    def check_inputs(self): # pong, se llama desde SynthDef _check_inputs(), lo reimplementan muchas sub-clases, es interfaz de UGen
        '''Returns error msg or None.'''
        return self.check_valid_inputs()

    def check_valid_inputs(self):  # este método se usa acá y en otras ugens dentro de check_inputs, es interfaz de UGen se usa junto con check_inputs
        '''Returns error msg or None.'''
        for i, input in enumerate(self.inputs):
            if not is_valid_ugen_input(input):
                arg_name = self.arg_name_for_input_at(i)
                if not arg_name: arg_name = i
                return 'arg: {} has bad input: {}'.format(arg_name, input)
        return None

    def check_n_inputs(self, n): # ídem anterior, deben ser interfaz protejida. Este no sé si pueda ser check_inputs sobrecargado o con parámetro opcional, tal vez si...
        if self.rate is 'audio': # *** convertir audio en constante de enum
            if n > len(self.inputs): # en sclang no comprueba el rango de inputs porque arr[i] fuera de rango devuelve nil y nil.rate devuelve nil!
                n = len(self.inputs)
            for i in range(n):
                if as_ugen_rate(self.inputs[i]) != 'audio': # *** VER VALORES POSIBLES PARA self.inputs[i]:: IMPLEMENTADO ARRIBA COMO SINGLE DISPATCH
                    return 'input {} is not audio rate: {} {}'.format(
                        i, self.inputs[i], self.inputs[0].rate)
        return self.check_valid_inputs() # comprueba is_valid_ugen_input no el rate.

    def check_sr_as_first_input(self): # checkSameRateAsFirstInput ídem anterior, deben ser interfaz protejida
        if self.rate is not as_ugen_rate(self.inputs[0]): # *** VER VALORES POSIBLES PARA self.inputs[0]: IMPLEMENTADO ARRIBA COMO SINGLE DISPATCH
            return 'first input is not {} rate: {} {}'.format(
                self.rate, self.inputs[0], self.inputs[0].rate)
        return self.check_valid_inputs()

    def arg_name_for_input_at(self, i): # se usa acá y en basicopugen dentro de checkValidInputs, ambas clases lo implementan.
        try:
            selector = self.method_selector_for_rate()
            method = getattr(self.__class__, selector)
            sig = inspect.signature(method)
            params = list(sig.parameters.values())
            arg_names = [x.name for x in params]
            if not arg_names: return None
            if i < len(arg_names):
                # if selector is '__init__': # TODO, TODO, TODO: No se puede usar __init__ y haya que usar new o dr para demand rate!!!!!
                #     return arg_names[i + 1] # TODO, TODO, TODO: VER ABAJO: 1 es arg_names_inputs_offset
                # else:
                #     return arg_names[i]
                return arg_names[i]
            else:
                return None # sclang at(i) retorna nil en vez de una excepción. No sé si eso está bien acá, porque claramente puede ser un error de índice si se pide algo que no existe, self.inputs no puede ser distinto.
        except AttributeError:
            return None

    # VER: Si este método es necesario en Python.
    # a = SinOsc.ar; a.class.class.findMethod(\ar).argNames; -> SymbolArray[ this, freq, phase, mul, add ]
    # arg_names como se extrae arriba omite el primer argumento que es self/cls, salvo para los métodos mágicos.
    # TODO: Si se usa __init__ como new de sclang *sí* se necesita offset. Los métodos mágicos devuelven self/cls. VER los métodos de clase.
    # TODO: Además, lo implementan muchas UGens (devuelven 2). Se usa solo en arg_name_for_input_at, de UGen y BasicOpUGenself.
    # En todo caso sería una propiedad o un método?
    # def arg_names_inputs_offset(self): # lo implementan varias clases como intefaz, se usa solo acá y basicopugen en argNameForInputAt
    #     return 1

    def method_selector_for_rate(self): # SUBIDA de la sección write
        return UGen.method_selector_for_rate(self.rate) # VER: este no tendría try/except en getattr? VER: repite el código porque comprueba con self.rate que cambia si se inicializa con ar/kr/ir, pero no es lo mismo así?? No lo implementa ninguna sub-clase.

    @classmethod
    def method_selector_for_rate(cls, rate): # este tiene una variante de instancia, ahora acá arriba.
        if rate is 'audio': return 'ar'
        if rate is 'control': return 'kr'
        if rate is 'scalar':
            if 'ir' in dir(cls): # VER arriba: es try: getattr(cls, self.method_selector_for_rate()) except AttributeError: lala.
                return 'ir'
            else:
                return 'new' # TODO, OJO, VER, LAS SUBCLASES NO PUEDEN IMPLEMENTAR __init__ !!!
        if rate is 'demand': return 'dr' # DR SE USA PORQUE LAS SUBCLASES DE UGEN NO PUEDEN IMPLEMENTAR __init__, DE PASO QUEDA MÁS CONSISTENTE...
        return None

    def dump_args(self): # implementa acá y en basicopugen se usa en SynthDef checkInputs y en Mix*kr
        msg = 'ARGS:\n'
        tab = ' ' * 4
        arg_name = None
        for i, input in enumerate(self.inputs):
            arg_name = self.arg_name_for_input_at(i)
            if not arg_name: arg_name = str(i)
            msg += tab + arg_name + ' ' + str(input)
            msg += ' ' + self.__class__.__name__ + '\n'
        print(msg, end='')

    #degreeToKey VER: por qué está acá y pegada a las otras !!! Es interfaz pero de simple number o math opes, creo, no sé por qué no está arriba.

    def dump_name(self):
        return str(self.synth_index) + '_' + self.name()

    def output_index(self): # es una propiedad de OutputProxy, es método constante acá. No tiene otra implementación en la librería estandar. Se usa solo UGen.writeInputSpec y SynthDesc.readUGenSpec se obtiene de las inputs.
        return 0

    def writes_to_bus(self): # la implementan algunas out ugens, se usa en SynthDesc.outputData
        return False

    # def is_ugen(self): # Object devuelve false, UGen, true. No se usa en ninguna parte, y no tiene sentido (se hace isinstance(esto, UGen))
    #     return True

    # VER: por qué estas no están más arriba con las matemáticas y mezcladas
    # acá, porque de alguna manera se relacoinan porque crean ugens, aunque
    # son para debuguing de la definición de síntesis en el servidor.
    # Un buen comentario sería '''Debug methods for running synths'''
    #poll
    #dpoll
    #checkBadValues

    @classmethod # VER: la locación de este método, es una utilidad de clase.
    def replace_zeroes_with_silence(cls, values: list): # es recursiva y la usan Function-asBuffer, (AtkMatrixMix*ar), GraphBuilder-wrapOut, LocalOut*ar, Out*ar, XOut*ar.
        # OC: This replaces zeroes with audio rate silence.
        # Sub collections are deep replaced
        num_zeroes = values.count(0.0)
        if num_zeroes is 0: return values

        silent_channels = as_list(Silent.ar(num_zeroes)) # usa asCollection
        pos = 0
        for i, item in enumerate(values):
            if item == 0.0:
                values[i] = silent_channels[pos]
                pos += 1
            elif isinstance(item, list):
                res = cls.replace_zeroes_with_silence(item)
                values[i] = res
        return values

    # L407
    # OC: PRIVATE
    # OC: function composition
    # Son la interfaz de AbstractFunction
    def compose_unop(self, selector): # composeUnaryOp
        return UnaryOpUGen(selector, self)
    def compose_binop(self, selector, input): #composeBinaryOp
        if is_valid_ugen_input(input):
            return BinaryOpUGen(selector, self, input)
        else:
            # TODO: anInput.performBinaryOpOnUGen(aSelector, this);
            # Lo implementan Complex, Polar, MathLib:Spherical y Object.
            # Cada clase prepara los datos para que sean ugens (o válidos).
            # Object llama al método performBinaryOpOnSomething que prepara
            # los datos según las características del tipo según un subconjunto
            # de operaciones binarias (== y !=) o tira BinaryOpFailureError.
            # TODO: se podría poner la lógica como envío doble en BinaryOpUGen?
            # cómo afecta esto a la creación de extensiones? Los objetos complex
            # en Python tienen el método __complex__, ver cmath builtin lib.
            msg = 'operations between UGen and {} are not implemented (yet or never)'
            raise NotImplementedError(msg.format(type(input).__name__))
    # def compose_rbinop(self, selector, ugen): # puede que no sea necesario, salvo otras operaciones de sclang, pero BinaryOpFunction usa rmethod y habría que cambiarlo también
    #     return BinaryOpUGen(selector, ugen, self)
    def compose_narop(self, selector, *args): #composeNAryOp
        raise NotImplementedError('UGen compose_narop is not implemented.') # y probablemente nunca se haga?

    # L426
    # OC: Complex support
    #asComplex
    #performBinaryOpOnComplex

    # L431, el método if que no voy a poner...
    #if(self, trueugen, falseugen)

    # L470
    # Este método llama a los de abajo, reordené or orden de lectura.
    # Escribe a archivo, pero también generan el formato. VER con SynthDef
    #writeDef

    # L467
    def name(self): # es ugen name
        return self.__class__.__name__

    def rate_number(sefl): #rateNumber # se usa en writeDef/Old y writeOutputSpec
        if self.rate is 'control': return 1
        if self.rate is 'audio': return 2
        if self.rate is 'demand': return 3
        return 0 # 'scalar'

    def num_inputs(self): #numInputs
        return len(self.inputs)

    def num_outputs(self):
        return 1

    # L435 métodos write, escriben a archivo, pero también generan el formato.
    # VER junto con SynthDef, se llaman desde writeDef (ahora arriba por orden de lectura)
    #writeInputSpec
    #writeOutputSpec
    #writeOutputSpecs

    # Topo sort methods. # y dumpName (PASADO ARRIBA) que se usa en UGen dumpUGens y OutputProxy dumpName

    # L488
    def init_topo_sort(self):
        for input in self.inputs:
            if isinstance(input, UGen):
                if isinstance(input, OutputProxy):
                    ugen = input.source_ugen # VER: source acá es solo propiedad de OutputProxy(es), no se implementa en otras clases.
                else:                        # OJO: SynthDesc-readUGenSpec llama a source dos veces, la primera sin checar. VER: source es un método/propiedad de varias clases, Array (que returns the source UGen from an Array of OutputProxy(s)) y Nil
                    ugen = input             # VER: source, Object (devuelve this), Nil (método vacío), OutputProxy (es propiedad) y Array, VER otras clases
                self.antecedents.add(ugen)
                ugen.descendants.add(self)
        for ugen in self.width_first_antecedents:
            self.antecedents.add(ugen)
            ugen.descendants.add(self)

    def make_available(self):
        if len(self.antecedents) is 0:
            self.synthdef.available.append(self)

    def remove_antecedent(self, ugen):
        self.antecedents.remove(ugen)
        self.make_available()

    def schedule(self, out_stack): # el nombre de este método no me cierra, la ugen se agrega a la pila, no más...
        for ugen in self.descendants: # por qué hace descendants.reverseDo si descendants es un Set???
            ugen.remove_antecedent(self)
        out_stack.append(self)

    def optimize_graph(self):
        pass # pass? se usa para esto o es confuso?

    def perform_dead_code_elimination(self): # Se usa un optimize_graph de BinaryOpUGen, PureMultiOutUGen, PureUGen y UnaryOpUGen.
        if self.descendants is 0:
            for input in self.inputs:
                if isinstance(input, UGen):
                    input.descendants.remove(self)
                    input._optimize_graph()
            self.synthdef.remove_ugen(self)
            return True
        return False


# OC: ugen which has no side effect and can therefore be considered for a dead code elimination
# read access to buffers/busses are allowed
class PureUGen(UGen):
    def optimize_graph(self):
        self.perform_dead_code_elimination() # VER: creo que no es necesario llamar a super


class MultiOutUGen(UGen): # TODO
    pass


class PureMultiOutUGen(MultiOutUGen):
    def optimize_graph(self):
        self.perform_dead_code_elimination() # VER: creo que no es necesario llamar a super


class OutputProxy(UGen):
    # VER: en el original declara <>name, pero no veo que se use acá, y no tiene subclases, tal vez sobreescribe UGen-name()?
    @classmethod
    def new(cls, rate, source_ugen, index):
        return cls.new1(rate, source_ugen, index) # OJO: tiene que retornoarseeee lo mismo que init_ugen!

    def init_ugen(self, source_ugen, index): # init_ugen tiene que retornar self! en Python retorna None por defecto.
        self.source_ugen = source_ugen # OJO: source cambia a source_ugen
        self.output_index = index
        self.synth_index = source_ugen.synth_index
        return self

    def add_to_synth(self):
        self.synthdef = SynthDef._current_def

    def dump_name(self):
        return self.source_ugen.dump_name() + '[' + str(self.output_index) + ']'


# Estos métodos no sé cómo implementarlos. El problema es que serían un
# protocolo, pero todos los objetos tienen que responder a él. Y no quiero
# alterar la paz pytónica creando un objeto base. Tal vez luego encuentre
# una solución general alternativa, así debería funcionar, el problema es
# ver cómo se hace cuando se crean nuevas clases como extensiones. Tal vez
# así podría andar y simplemente hay que agregar el register en cada módulo
# y no acá.

class Buffer(): pass  # TODO DEFINICIONES SOLO PARA TEST!
class Bus(): pass     # TODO VER CÓMO HACER PARA NO IMPORTAR TODO LO INNECESARIO
class Dunique(): pass #
class Event(): pass   #
class Node(): pass    #

@singledispatch
def is_valid_ugen_input(obj):
    return False

@is_valid_ugen_input.register(AbstractFunction)
@is_valid_ugen_input.register(UGen)
@is_valid_ugen_input.register(list)
@is_valid_ugen_input.register(tuple)
@is_valid_ugen_input.register(bool)
def _(obj):
    return True

#@is_valid_ugen_input.register con numbers.py? Para casos especiales lo mejor sería que cada módulo agregue su propio dispatch
@is_valid_ugen_input.register(float)
@is_valid_ugen_input.register(int)
def _(obj):
    return not isnan(obj)


@singledispatch #Este método es implementado por varias clases y extensiones. Cada clase prepara los datos para que sea una entrada válida.
def as_ugen_input(obj): # ugen_cls (*** VER ABAJO ***) es opt_arg, solo AbstractFunction y Array lo usan, Array porque itera sobre. Si la llamada recibe una tupla estrella vacía '*()' no pasa nada.
    return obj

@as_ugen_input.register
def _(obj: AbstractFunction, *ugen_cls): # *** VER, creo que siempre es una clase UGen, puede que no sea así?
    return obj(*ugen_cls)

@as_ugen_input.register(tuple) # las tuplas se convierten en listas, no sé si podría ser al revés.
@as_ugen_input.register(list)
def _(obj, *ugen_cls):
    return list(map(lambda x: as_ugen_input(x, *ugen_cls), obj)) # de Array: ^this.collect(_.asUGenInput(for))

@as_ugen_input.register
def _(obj: Buffer): # si la llamada recibe una tupla estrella vacía '*()' no pasa nada.
    return obj.bufnum

@as_ugen_input.register
def _(obj: Bus):
    return obj.index

@as_ugen_input.register
def _(obj: Dunique):
    raise NotImplementedError('Dunique as ugen input is not implemente yet.') #TODO

@as_ugen_input.register
def _(obj: Event): # sc Event, VER
    return as_control_input(obj) # es otro método de interfaz

@as_ugen_input.register
def _(obj: Node): # sc Node
    raise NotImplementedError('Should not use a Node inside a SynthDef') # dice esto pero implmente as_control_input

#@as_ugen_input.register
# def _(obj: Point): # qué point?
#     pass # ^this.asArray } // dangerous?
# Ref y UGen devuelve this, el caso por defecto.


@singledispatch
def as_control_input(obj):
    return obj

@as_control_input.register
def _(obj: UGen):
    '''Otro método de interfaz para otras clases, muchas. Los
    valores válidos son los aceptados por las ugens, que tengo
    que ver cuales son, por lo pronto números y arrays.
    '''# TODO
    raise TypeError("Can't set a control to an UGen.")


@singledispatch
def num_channels(obj):
    '''Idem anteriores.'''# TODO
    return obj

@num_channels.register
def _(obj: UGen):
    return 1


# Agregado por la propiedad rate de las UGens que está implementada a nivel
# de la librería de clases. Nil retorna nil, SimpleNumber devuelve 'scalar'.
# SequenceableCollection devueve una colleción de valores sobre los cuales
# aplica rate, si no es nil sino aplica 'scalar'. BinaryOpUGen usa
# a.respondsTo(\rate)) en rate(). RawArray retorna 'scalar'. Stethoscope
# retorna el rate del bus o nil. SynthDef rate devuevle nil. UGen rate es
# 'audio' por defecto.
# El método UGen.methodSelectorForRate(rate) devuelve 'audio', 'control' o
# 'scalar', como símbolo en UGen.methodSelectorForRate(rate), pero no es
# el mismo método, los ControlName, además, tienen 'trigger' rate. También
# está 'demand'.
@singledispatch
def as_ugen_rate(obj):
    return None

@as_ugen_rate.register
def _(obj: str): # OJO, porque en sclang es tanto una función como una propiedad, RawArray retorna 'scalar' ("audio".rate -> 'scalar'), ver el caso list
    return obj

@as_ugen_rate.register(UGen)
@as_ugen_rate.register(Bus)
def _(obj):
    return obj.rate

@as_ugen_rate.register(float)
@as_ugen_rate.register(int)
def _(obj):
    return 'scalar'

@as_ugen_rate.register(list)
@as_ugen_rate.register(tuple)
def _(obj):
    if len(obj) is 1: return as_ugen_rate(obj[0]) # *** en SequenceableCollection si this.size es 1 devuelve this.first.rate

    obj = [as_ugen_rate(x) for x in obj]
    if any(x is None for x in obj): # *** demás, reduce con Collection minItem, los símbolos por orden lexicográfico, si algún elemento es nil devuelve nil !!!
        return None
    else:
        return min(obj) # VER pero falla si los objetos no son comparables (e.g. int y str),
                        # en sclang comparaciones entre tipos no compatibles retornan false...
                        # minItem también lo implementa SparseArray, pero es un array más eficiente y llama a super.
                        # *** el método de minItem puede recibir una función.
                        # Acá debería estar cubierto el caso porque primero se llama a as_ugen_rate y luego comprueba None.
                        # TODO: Si agrego una enum tengo que cuidar el orden. Y RawArray.rate retorna 'scalar' ("audio".rate -> 'scalar'),
                        # pero en la comparación original es una propiedad str (que puede ser un método por polimorfismo)

# @as_ugen_rate.register # pero asi también habría que hacerlo para set y dict, no tienen clase base con list y tuple?
# def _(obj: tuple):
#     return ...

# @as_ugen_rate.register
# def _(obj):
#     return
