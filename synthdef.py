"""
SynthDef...

Ver qué métdos se llaman desde las UGens y cómo se relacionan.
Buscar la manera de ir probando los resultados parciales y comprobando
junto con sclang. Prestar atención a los métodos que son de ancestros
y que actúan como protocolo incorporado en la librería de sclang incluso
desde Object.

Luego poner synthdef, ugen, binopugen y todas las ugens que actúan como
tipos básicos en un subpaquete que se llame synthgraph. Las ugens concretas
irían a parte en otro paquete llamado ugens... Pero después ver cómo se
pueden importar las cosas como conjuntos de paquetes tal vez compuestos
de subconjuntos de los elemnentos de los paquetes... suena complicado.
"""

import threading
import inspect
import warnings

from supercollie.utils import aslist, perform_in_shape


class SynthDef():
    _current_def = None #UGen.buildSynthDef // the synth currently under construction
    _build_lock = threading.Lock()

    synthdef_dir = None
    @classmethod
    def synthdef_dir(cls, dir): # es setter, usar @property, además se llama desde *initClass
        pass

    @classmethod
    def init_class(cls): # ver cuál es el equivalente en Python
        pass

    #*new L35
    #rates y prependeargs pueden ser anotaciones de tipo, ver variantes y metadata, le constructor hace demasiado...
    def __init__(self, name, graph_func, rates=[], # ALGO HABÍA LEIDO SOBRE NO PONER ALGO POR DEFECTO Y CHECKAR NONE
                prepend_args=[], variants={}, metadata={}): # rates y prepend args pueden ser anotaciones, prepargs puede ser un tipo especial en las anotaciones, o puede ser otro decorador?
        self.name = name
        #self.func = graph_func # la inicializa en build luego de finishBuild
        self.variants = variants # no sé por qué está agrupada como propiedad junto con las variables de topo sort
        self.metadata = metadata
        #self.desc # *** Aún no vi dónde inicializa

        #self.controls = [] # inicializa en initBuild, esta propiedad la setean las ugens mediante _current_def agregando controles
        self.control_names = [] # en sclang se inicializan desde nil en addControlNames, en Python tienen que estar acá porque se pueden llamar desde wrap
        self.all_control_names = [] # en sclang se inicializan desde nil en addControlNames
        self.control_index = 0 # lo inicializa cuando declara la propiedad y lo reinicializa al mismo valor en initBuild, no sé por qué porque wrap salta a después de initBuild, este valor lo incrementan las ugen, e.g. audiocontrol
        self.children = [] # Array.new(64) # esta probablemente sea privada? pero se usa para ping pong

        #self.constants = dict() # inicializa en initBuild
        #self.constant_set = set() # inicializa en initBuild
        #self.max_local_bufs = None # inicializa en initBuild, la usa LocalBus*new1 y checka por nil

        # topo sort
        self.available = [] # la inicializan las ugens con .makeAvailable() creando el array desde nil, initTopoSort la vuelve a nil.
        self._width_first_ugens = [] # se puebla desde nil con WidthFirstUGen.addToSynth (solo para IFFT)
        self._rewrite_in_progress = False # = None, la inicializa a True en optimizeGraph L472 y luego la vuelve a nil, debe ser privada, tal vez sea major False?

        self._build(graph_func, rates, prepend_args)

    # este es un método especial en varios tipos de clases tengo
    # que ver cuál es el alcance global dentro de la librería,
    # tal vez sea para serialización, no se usa en SynthDef/UGen.
    #def store_args(self):
    #    return (self.name, self.func) # una tupla en vez de una lista (array en sclang)

    # construye el grafo en varios pasos, init, build, finish y va
    # inicializando las restantes variables de instancia según el paso.
    # Tal vez debería ponerlas todas a None en __init__
    def _build(self, graph_func, rates, prepend_args):
        with SynthDef._build_lock:
            try:
                SynthDef._current_def = self
                self._init_build()
                self._build_ugen_graph(graph_func, rates, prepend_args)
                self._finish_build()
                self.func = graph_func # inicializa func que junto con name son las primeras propiedades.
                SynthDef._current_def = None
            except Exception as e:
                SynthDef._current_def = None
                raise e

    # L53
    #*wrap # Tal vez podría ser un decorador en Python, ver la documentación de SynthDef.

    # OC: Only write if no file exists
    #*writeOnce
    #writeOnce # ver por qué duplica la funcioanlidad entre clase e instancia

    # L69
    def _init_build(self):
        #UGen.buildSynthDef = this; Ahora se hace como SynthDef._current_def con un lock.
        self.constants = dict() # o {} crea un diccionario en Python
        self.constant_set = set() # será constantS_set?
        self.controls = []
        self.control_index = 0 # reset this might be not necessary
        self.max_local_bufs = None # la usa LocalBus*new1 y checka por nil.
        #inicializa todo en lugares separados cuando podría no hacerlo? VER.

    def _build_ugen_graph(self, graph_func, rates, prepend_args):
        # OC: save/restore controls in case of *wrap
        save_ctrl_names = self.control_names # aún no se inicializó self.control_names usando new, es para wrap que se llama desde dentro de otra SynthDef ya en construcción.
        self.control_names = [] # None # no puede ser None acá
        self.prepend_args = prepend_args # Acá es una lista, no hay asArray.
        self._args_to_controls( # add_controls_from_args_of_func_please(
            graph_func, rates, len(self.prepend_args)) # HAY QUE TOMAR DECISIONES.
        result = func(*(prepend_args + self._build_controls())) # usa func.valueArray(prepend_args ++ this.buildControls) buildControls tiene que devolver una lista.
        self.control_names = save_control_names
        return result

    #addControlsFromArgsOfFunc (llamada desde buildUGenGraph)
    def _args_to_controls(self, func, rates, skip_args=0):
        # var def, names, values,argNames, specs;
        if not inspect.isfunction(func) or inspect.isgeneratorfunction(func):
            raise TypeError('@synthdef only apply to function')

        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        arg_names = [x.name for x in params] # list(map(lambda x: x.name, params))
        if len(arg_names) < 1: return self # None

        # OC: OK what we do here is separate the ir, tr and kr rate arguments,
		# create one Control ugen for all of each rate,
		# and then construct the argument array from combining
		# the OutputProxies of these two Control ugens in the original order.
        names = arg_names[skip_args:]
        arg_values = [x.default for x in params] # list(map(lambda x: x.default, params))
        values = [x if x is not inspect._empty else None for x in arg_values] # any replace method?
        values = values[skip_args:] # **** VER, original tiene extend, no se si es necesario acá (o allá), len(names) debería ser siempre igual a len(values), se puede aplicar "extend" como abajo, pero VER!
                                    # **** VER, puede ser que hace extend por si el valor de alguno de los argumentos es un array no literal.
                                    # **** def.prototypeFrame DEVUELVE NIL EN VEZ DE LOS ARRAY NO LITERALES!
                                    # **** Además, ver cómo es en Python porque no tendría las mismas restricciones que sclang
        values = _apply_metadata_specs(names, values) # convierte Nones en ceros o valores por defecto
        rates += [0] * (len(names) - len(rates)) # VER: sclang extend, pero no trunca
        rates = [x if x else 0.0 for x in rates]

        for i, name in enumerate(names):
            prefix = name[:2]
            value = values[i]
            lag = rates[i]

            msg = 'Lag value {} for {} arg {} will be ignored'
            # pero realmente me gustaría sacar los nombres x_param y reemplazarlos por anotaciones, es lo mismo y mejor, aunque se usan las anotaciones para otra cosa.
            if (lag == 'ir') or (prefix == 'i_'):
                if isinstance(lag, (int, float)) and lag != 0:
                    warnings.warn(msg.format(lag, 'i-rate', name))
                self.add_ir(name, value)
            elif (lag == 'tr') or (prefix == 't_'):
                if isinstance(lag, (int, float)) and lag != 0:
                    warnings.warn(msg.format(lag, 'trigger', name))
                self.add_tr(name, value)
            elif (lag == 'ar') or (prefix == 'a_'):
                if isinstance(lag, (int, float)) and lag != 0:
                    warnings.warn(msg.format(lag, 'audio', name))
                self.add_ar(name, value)
            else:
                if lag == 'kr': lag = 0.0
                self.add_kr(name, value, lag)

    # método agregado
    def _apply_metadata_specs(self, names, values):
        # no veo una forma conscisa como en sclang
        new_values = []
        if self.metadata and 'specs' in self.metadata:
            specs = self.metadata['specs']
            for i, value in enumerate(values):
                if value:
                    new_values.append(value)
                else:
                    if names[i] in specs:
                        spec = as_spec(specs[names[i]]) # as_spec devuelve un objeto ControlSpec o None, implementan Array, Env, Nil, Spec y Symbol  **** FALTA no está hecha la clase Spec ni la función para los strings!
                    else:
                        spec = as_spec(names[i])
                    if spec:
                        new_values.append(spec.default()) # **** FALTA no está hecha la clase Spec/ControlSpec, no sé si default es un método
                    else:
                        new_values.append(0.0)
        else:
            new_values = [x if x else 0.0 for x in values]
        return new_values # values no la reescribo acá por ser mutable

    # OC: Allow incremental building of controls.
    # estos métodos los usa solamente NamedControls desde afuera y no es subclase de SynthDef ni de UGen
    def add_non_control(self, name, values): # lo cambio por _add_nc _add_non? este método no se usa en ninguna parte de la librería estandar
        self.add_control_name(ControlName(name, None, 'noncontrol', # IMPLEMENTAR CONTROLNAME
            values, len(self.control_names))) # values hace copy *** VER self.controls/control_names no pueden ser None

    def add_ir(self, name, values): # *** VER dice VALUES en plural, pero salvo que se pase un array como valor todos los que calcula son escalares u objetos no iterables.
        self.add_control_name(ControlName(name, len(self.controls), 'scalar', # *** VER self.controls/control_names no pueden ser None
            values, len(self.control_names))) # values *** VER el argumento de ControlName es defaultValue que puede ser un array para expansión multicanal de controles, pero eso puede pasar acá saliendo de los argumentos?

    def add_tr(self, name, values):
        self.add_control_name(ControlName(name, len(self.controls), 'trigger', # *** VER self.controls/control_names no pueden ser None
            values, len(self.control_names))) # values hace copy, *** VER ControlName hace expansión multicanal como dice la documentación???

    def add_ar(self, name, values):
        self.add_control_name(ControlName(name, len(self.controls), 'audio', # *** VER self.controls/control_names no pueden ser None
            values, len(self.control_names))) # values hace copy

    def add_kr(self, name, values, lags): # acá también dice lags en plural pero es un valor simple como string (symbol) o number según interpreto del código anterior.
        self.add_control_name(ControlName(name, len(self.controls), 'control', # *** VER self.controls/control_names no pueden ser None
            values, len(self.control_names), lags)) # *** VER values y lag hacen copy

    # este también está expuesto como variente de la interfaz, debe ser el original.
    # el problema es que son internos de la implementación de la librería, no deberían ser expuestos al usuario.
    def add_control_name(self, cn): # lo llama también desde las ugens mediante _current_def, e.g. audiocontrol
        self.control_names.append(cn)
        self.all_control_names.append(cn)

    # L178
    def _build_controls(self): # llama solo desde _build_ugen_graph, retorna una lista
        nn_cns = [x for x in self.control_names if x.rate is 'noncontrol']
		ir_cns = [x for x in self.control_names if x.rate is 'scalar']
		tr_cns = [x for x in self.control_names if x.rate is 'trigger']
		ar_cns = [x for x in self.control_names if x.rate is 'audio']
        kr_cns = [x for x in self.control_names if x.rate is 'control']

        arguments = [0] * len(self.control_names)
        values = []
        index = None
        ctrl_ugens = None
        lags = None
        val_size = None

        if nn_cns:
            for cn in nn_cns:
                arguments[cn.arg_num] = cn.default_value

        def build_ita_controls(ita_cns, ctrl_class, method):
            nonlocal arguments, values, index, ctrl_ugens
            if ita_cns:
                values = []
                for cn in ita_cns:
                    values.append(cn.default_value)
                index = self.control_index
                ctrl_ugens = perform_in_shape(values, ctrl_class, method) # Control.ir(values.flat).asArray.reshapeLike(values);
                for i, cn in enumerate(ita_cns):
                    cn.index = index
                    index += len(as_list(cn.default_value))
                    arguments[cn.arg_num] = ctrl_ugens[i]
                    self._set_control_names(ctrl_ugens[i], cn)
        build_ita_controls(ir_cns, Control, 'ir')
        build_ita_controls(tr_cns, TrigControl, 'kr')
        build_ita_controls(ar_cns, AudioControl, 'ar')

        if kr_cns:
            values = []
            lags = []
            for cn in kr_cns:
                values.append(cn.default_value)
                valsize = len(as_list(cn.default_value))
                if valsize > 1:
                    lags.append(wrap_extend(as_list(cn.lag), valsize))
                else:
                    lags.append(cn.lag)
            index = self.control_index
            if any(x != 0 for x in lags):
                # flop. Sub-levels se pueden producir por expansión multicanal
                # pero _set_control_names soporta solo un nivel porque
                # OutputProxy no tiene atributo name. # **** REVISAR todo esto, es posible que haya pasado algo por alto porque me mareé. Pero por _set_control_names me parece que me mareé al pedoó.
                values = [(values[i], lags[i]) for i in range(len(values))]
                ctrl_ugens = perform_in_shape(values, LagControl, 'kr') # LagControl.kr(values.flat, lags).asArray.reshapeLike(values);
            else:
                ctrl_ugens = perform_in_shape(values, Control, 'kr') # Control.ir(values.flat).asArray.reshapeLike(values);
            for i, cn in enumerate(kr_cns):
                cn.index = index
                index += len(as_list(cn.default_value))
                arguments[cn.arg_num] = ctrl_ugens[i]
                self._set_control_names(ctrl_ugens[i], cn)

        self.control_names = [x for x in self.control_names\
                              if x.rate is not 'noncontrol']
        return arguments

    # L263
    def _set_control_names(self, ctrl_ugens, cn):
        if isinstance(ctrl_ugens, list):
            for ctrl_ugen in ctrl_ugens: # este loop no me da la pauta de que no soporta más que un nivel de anidamiento? (!)
                ctrl_ugen.name = cn.name
        else:
            ctrl_ugens.name = cn.name

    # L273
    def _finish_build(self):
        # estos métodos delegan en el homónimo de UGen (el ping pong)
        self._add_copies_if_needed() # ping, solo se usa para PV_Chain ugens, es un caso muy particular.
        self._optimize_graph() # llama a _init_topo_sort, _topological_sort hace lo mismo acá abajo, hace todo dos veces, parece. Y llama a self._index_ugens()
        self._collect_constants() # este método está en L489 pegado a optimizeGraph dentro de la lógica de topo sort, cambiado a orden de lectura
        self._check_inputs() # OC: Will die on error.

        # OC: re-sort graph. reindex.
        self._topological_sort() # llama a _init_topo_sort()
        self._index_ugens()
        # UGen.buildSynthDef = nil; esto lo pasé a SynthDef, está en try/except de _build

    def _add_copies_if_needed(self):
        # OC: could also have PV_UGens store themselves in a separate collection
        for child in self._width_first_ugens: # _width_first_ugens aún no lo inicializó porque lo hace en WithFirstUGen.addToSynth (solo para IFFT) en este caso, es una lista que agrego en __init__.
            if isinstance(child, PV_ChainUGen):
                child._add_copies_if_needed() # pong

    # L468
    # OC: Multi channel expansion causes a non optimal breadth-wise
    # ordering of the graph. The topological sort below follows
    # branches in a depth first order, so that cache performance
    # of connection buffers is optimized.

    # L472
    def _optimize_graph(self): # ping pong privato
        self._init_topo_sort()

        self._rewrite_in_progress = True # Comprueba en SynthDef:add_ugen que se llama desde las ugen, la variable es privada de SynthDef. No me cierra en que caso se produce porque si ugen.optimize_graph quiere agregar una ugen no fallaría?
        for ugen in self.children[:]: # ***** Hace children.copy.do porque modifica los valores de la lista sobre la que itera. VER RECURSIVIDAD: SI MODIFICA UN VALOR ACCEDIDO POSTERIORMENTE None.optimize_graph FALLA??
            ugen.optimize_graph() # pong, las ugens optimizadas se deben convertir en None dentro de la lista self.children, pasa en UGen.performDeadCodeElimination y en las opugens.
        self._rewrite_in_progress = False

        # OC: Fixup removed ugens.
        old_size = len(self.children)
        self.children = [x for x in self.children if x] #children.removeEvery(#[nil]);  *** por qué no es un reject?
        if old_size != len(self.children):
            self._index_ugens()

    def _init_topo_sort(self): # ping # CAMBIADO A ORDEN DE LECTURA (sería orden de llamada?)
        self.available = []
        for ugen in self.children:
            ugen.antecedents = set()
            ugen.descendants = set()
        for ugen in self.children:
            # OC: This populates the descendants and antecedents.
            ugen.init_topo_sort() # pong
        for ugen in reversed(self.children):
            ugen.descendants = # ugen.descendants.asArray.sort({ arg a, b; a.synthIndex < b.synthIndex })
            # OC: All ugens with no antecedents are made available.
            ugen.make_available()

    def _index_ugens(self): # CAMBIADO A ORDEN DE LECTURA
        for i, ugen in enumerate(self.children):
            ugen.synth_index = i

    # L489
    def _collect_constants(self): # ping
        for ugen in self.children:
            ugen._collect_constants() # pong

    # L409
    def _check_inputs(self): # ping
        first_err = None
        for ugen in self.children: # *** Itera sobre self.children por enésima vez.
            err = ugen.check_inputs() # pong, en sclang devuelve nil o un string, creo que esos serían todos los casos según la lógica de este bloque.
            if err: # *** HACER *** EN SCLANG ES ASIGNA A err Y COMPRUEBA notNil, acá puede ser none, pero ver qué retornan de manera sistemática, ver return acá abajo.
                #err = ugen.class.asString + err;
                #err.postln;
				#ugen.dumpArgs; # *** OJO, no es dumpUGens
                if not first_err: first_err = err
        if first_err:
            #"SynthDef % build failed".format(this.name).postln;
            raise Exception(firstErr)
        return True # porque ugen.check_inputs() retorna nil y acá true

    def _topological_sort(self):
        self._init_topo_sort()
        ugen = None
        out_stack = []
        while len(self.available) > 0:
            ugen = self.available.pop()
            ugen.schedule(out_stack); # puebla out_stack. ugen.schedule() se remueve de los antecedentes, se agrega a out_stack y devuelve out_stack. Acá no es necesaria la reasignación.
        self.children = out_stack
        self._cleanup_topo_sort()

    def _cleanup_topo_sort(self):
        for ugen in self.children:
            ugen.antecedents = set()
            ugen.descendants = set()
            ugen.width_first_antecedents = [] # *** ÍDEM, OJO: no es SynthDef:_width_first_ugens, los nombres son confusos.

    # L428
    # OC: UGens do these.
    # Métodos para ping pong
    def add_ugen(self, ugen): # lo usan UGen y WithFirstUGen implementando el método de instancia addToSynth
        if not self._rewrite_in_progress:
            ugen.synth_index = len(self.children)
            ugen.width_first_antecedents = self._width_first_ugens[:] # with1sth antec/ugens refieren a lo mismo en distintos momentos, la lista es parcial para la ugen agregada.
            self.children.append(ugen)

    def remove_ugen(self, ugen): # # lo usan UGen y BinaryOpUGen para optimizaciones
		# OC: Lazy removal: clear entry and later remove all None entries # Tiene un typo, dice enties
		self.children[ugen.synth_index] = None;

    def replace_ugen(self, a, b): # lo usa BinaryOpUGen para optimizaciones
        if not isinstance(UGen, b):
            raise Exception('replace_ugen assumes a UGen')

        b.width_first_antecedents = a.width_first_antecedents
        b.descendants = a.descendants
        b.synth_index = a.synth_index
        self.children[a.synth_index] = b

        for item in self.children: # tampoco usa el contador, debe ser una desprolijidad después de una refacción, uso la i para el loop interno
            if item:
                for i, input in enumerate(item.inputs):
                    if input is a:
                        item.inputs[i] = b

    def add_constant(self, value): # lo usa UGen:collectConstants
        if value not in self.constant_set:
            self.constant_set.add(value) # es un set, como su nombre lo indica, veo que se usa por primera vez
            self.constants[value] = len(self.constants) # es un dict, ver qué valores puede asumir value y si puede fallar como llave del diccionario, e.g. si son float generados por operaciones matemáticas.
            # VER: cómo se usa self.constants y por qué guarda len, que, supongo, sería el índice de la constante en una lista pero es una llave de un diccionario.

    # L535
    # Método utilitario de SynthDef, debe ser original para debuguing.
    def dump_ugens(self): # no se usa, no está documentado, pero es ÚTIL! se puede hacer hasta acá y pasar a las ugens (pero hay que hacer addUGen, etc., acá)
        inputs = []
        #ugen_name = None # esta no la usa, es un descuido del programador
        print(self.name)
        for ugen in self.children: # tampoco terminó usando el índice
            if ugen.inputs:
                inputs = [x.dump_name() if isinstance(x, UGen)\
                          else x for x in ugen.inputs] # ugen.inputs.collect {|in| if (in.respondsTo(\dumpName)) { in.dumpName }{ in }; }; # Las únicas clases que implementan dumpName son UGen, BasicOpUGen y OutputProxy, sería interfaz de UGen, sería if is UGen
            print([ugen.dump_name(), ugen.rate, inputs])

    # L549
    # OC: make SynthDef available to all servers
    #add
    # L561
    #*removeAt *** ver dónde se usa, es de clase

    # L294 # PUESTA DESPUÉS DE ADD. estos métodos no deberían ir luego de add? están como puestos antes acá, ver si tienen alguna dependencia de los métodos alrededor.
    #asBytes
    #writeDefFile
    #writeDef
    #writeConstants

    # L570
    # OC: Methods for special optimizations.
    # OC: Only send to servers.
    #send
    #doSend
    # OC: Send to server and write file.
    #load
    # OC: Write to file and make synth description.
    #store
    #asSynthDesc

    # L653
    # OC: This method warns and does not halt because
    # loading existing def from disk is a viable
    # alternative to get the synthdef to the server.
    #loadReconstructed

    # OC: This method needs a reconsideration
    #storeOnce

    #play
