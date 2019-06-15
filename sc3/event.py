"""Event.sc"""

import types
import math
import warnings
import functools as ft
import itertools as it
import operator as op

from .rest import Rest
from . import builtins as bi
from . import scale as scl
from . import synthdef as sdf
from . import synthdesc as sdc
from . import main as _main
from . import utils as utl
from .graphparam import node_param
from . import clock as clk
from . import server as srv
from . import node as nod


# NOTE: para putAll -> Event({**a, **b, **c, ...}) en vez de updates... (>= Python 3.5)

# NOTE: *** VER EventTypesWithCleanup.sc ***


class Event(dict):
    # NOTE: Son Event, se inicializan luego por fuera con _make_parent_events
    # _default_parent_event = {}
    # parent_events = {}
    # partial_events = {}

    # BUG: tengo que ver la documentación, en update los parámetros actúan igual
    def __init__(self, *args, **kwargs): # know = always True
        super().__init__(*args, **kwargs)
        super().__setattr__('proto', self.pop('proto', None))
        super().__setattr__('parent', self.pop('parent', None))

    # NOTE: set/get/del es simplemente para implementar y las llamadas a super
    # __setattr__ son solo por know = always True, no se si realmente hace
    # alguna diferencia. También sirve para que tire error si se quiere
    # asignar una llave heredada.
    def __setattr__(self, name, value):
        if hasattr(type(self), name): # NOTE: son los atributos heredados de dict
            raise AttributeError(f"attribute '{name}' can't be used as key")
        if name in ('proto', 'parent'):
            super().__setattr__(name, value)
        else:
            self[name] = value

    # NOTE: https://docs.python.org/3/howto/descriptor.html#invoking-descriptors
    # NOTE: "Called when the default attribute access fails with an AttributeError"
    # NOTE: object.__getattribute__(): data descriptors -> instance variables -> non-data descriptors -> __getattr__()
    # NOTE: https://docs.python.org/3/reference/datamodel.html#object.__getattribute__
    # NOTE: https://docs.python.org/3/reference/datamodel.html#special-lookup
    # NOTE: https://docs.python.org/3/library/types.html#types.FunctionType
    # NOTE: VER: módulo types, porque usa types.MethodType to a bound instance method object,
    # NOTE: y es una manera de pasar self: "Define names for built-in types that aren't directly accessible as a builtin."
    def __getattr__(self, name):
        try:
            if name in ('proto', 'parent'):
                attr = super().__getattr__(name)
            else:
                attr = self[name]
        except KeyError:
            attr = KeyError
        if attr is KeyError: # NOTE: así no tira excepción sobre excepción.
            msg = "'{}' has not attribute or key '{}'"
            raise AttributeError(msg.format(type(self).__name__, name))
        if isinstance(attr, types.FunctionType):
            # return attr(self) # NOTE: así no existen las llamadas, la llave siempre retorna valor, self contiene el 'entorno'
            # NOTE: si se decide hacer que las llaves evalúen las funciones hay que tener en cuenta que hay llaves que necesitan retornar funciones, y la función como elemnto de la llave obtiene una cualidad especial distinta al comportamiento estandar.
            return types.MethodType(attr, self) # NOTE: esta es la forma correcta para que pase self primero siempre (no se puede fácil con FunctionType), ahora, self siempre tiene que estar declarada también. Cuando se llama con at no se pasa self en SuperCollider.
        else:
            return attr

    def __delattr__(self, name):
        if hasattr(type(self), name) or name in ('proto', 'parent'): # NOTE: los atributos heredados de dict, proto y parent no se pueden borrar
            raise AttributeError(f"attribute '{name}' can't be deleted")
        del self[name]

    def __getitem__(self, key):
        try:
            value = super().__getitem__(key)
        except KeyError:
            if self.proto is not None:
                try:
                    value = super(type(self), self.proto).__getitem__(key)
                except KeyError:
                    if self.parent is not None: # proto and parent
                        try:
                            value = self.parent[key]
                        except KeyError:
                            value = KeyError
                    else: # proto and no parent
                        value = KeyError
            elif self.proto is None and self.parent is not None: # no proto and parent
                try:
                    value = self.parent[key]
                except KeyError:
                    value = KeyError
            else: # no proto and no parent
                value = KeyError
        if value is KeyError: # NOTE: así no tira excepción sobre excepción.
            raise KeyError(key)
        return value

    def __repr__(self):
        return f'{type(self).__name__}({super().__repr__()})'

    def copy(self):
        obj = type(self)(super().copy())
        super(type(obj), obj).__setattr__('proto', self.proto)
        super(type(obj), obj).__setattr__('parent', self.parent)
        return obj

    ### Event interface ###

    # NOTE: '''Para usar como decorador'''
    def add_function(self, func):
        self.__setattr__(func.__name__, func)

    # NOTE: value sirve porque las llaves se pueden llamar siendo funciones o valores según el dato de entrada/sobreescritura del usuario
    # BUG: en realidad esto es simplemente self.name() pero ignora la llamada y los argumentos si no es una función, distintas funciones pueden tener distintos nombres para los argumentos, eso no se ignora acá y tienen que tener valores por defecto.
    def value(self, name, *args, **kwargs):
        value = self[name]
        if isinstance(value, types.FunctionType):
            return value(self, *args, **kwargs)
        else:
            return value

    @classmethod
    def default(cls):
        return cls(parent=cls._default_parent_event)

    @classmethod
    def silent(cls, dur=1.0, in_event=None):
        if in_event is None:
            in_event = cls()
        else:
            in_event = in_event.copy()
        delta = dur * in_event.get('strech', 1) # BUG: *** y is dur no puede ser Rest y ya?! VER comentario en Rest.
        in_event.update({'dur': Rest(dur), 'delta': delta})
        in_event.parent = cls._default_parent_event # NOTE: sclang usa put(\parent, x), pero es que no me cierra porque acá esta categorizado como atributos lo mismo que en IdentityDictionary
        return in_event

    # // event types

    # TODO: falta...

    # // instance methods

    # def next(self, inval):
    #     pass

    # NOTE: Se llamaba delta y se usa como llave y método en sclang usando
    # NOTE: put(\delta, value) o e[\delta] en playAndDelta y algunos patterns.
    # NOTE: En esta implementación se se puede tener atributos y llaves
    # NOTE: con el mismo nombre, cambio el nombre. Ahora, esto hay que
    # NOTE: recordarlo y revisarlo al implementar los patterns. Posbles BUG(s).
    def calc_delta(self):
        delta = self.get('delta')
        if delta is not None:
            return delta # NOTE: considero que no puede ser Rest.
        dur = self.get('dur')
        if dur is None:
            return None
        if isinstance(dur, Rest):
            dur = dur.value
        stretch = self.get('stretch', 1)
        # NOTE: considero que strech no puede ser Rest tampoco.
        return dur * stretch

    def play(self):
        if self.parent is None:
            super().__setattr__('parent', type(self)._default_parent_event)
        self.play_func()

    def is_rest(self):
        return False # BUG: ************************ TODO: por qué está implementado a bajo nivel?

    # TODO: falta...

    # // this method is called by EventStreamPlayer so it can schedule Routines as well
    def play_and_delta(self, cleanup, mute):
        if mute:
            self.type = 'rest'
        cleanup.update(self)
        self.play()
        return self.calc_delta()

    # // A Quant specifies the quant and phase at which a TempoClock starts an EventStreamPlayer
    # // Its offset specifies how far ahead of time events are actually computed by the EventStream.
    # // offset allows ~strum to be negative, so strummed chords complete on the beat
    # // it also makes it possible for one pattern to run a little ahead of another to set values
    # // This method keeps ~timingOffset and Quant.offset the same.
    def sync_with_quant(self, quant):
        # quant = clk.Quant.as_quant(quant) # NOTE: aunque la implementación actual no crea otro objeto esta función DEBE recibir un objeto Quant.
        if quant.timing_offset is not None:
            e = self.copy()
            e.timing_offset = quant.timing_offset
            return e
        else:
            quant.timing_offset = self.get('timing_offset')
            return self

    # TODO: sigue...

    # NOTE: Esta función realiza operaciones matemáticas entre vectores, y
    # NOTE: escalares. Es a la manera de sclang pero no realiza las operaciones
    # NOTE: dentro de los anidamientos. En principio está hecha para las operaciones
    # NOTE: sobre las llaves que definen las alturas. Hay que restringir los datos
    # NOTE: de entrada haciendolos explícitos por llave y relación entre llaves.
    # NOTE: VER: archivo test_scarray_op.py.
    @staticmethod
    def _binop_map(op, a, b):
        if isinstance(a, (list, tuple)):
            if isinstance(b, (list, tuple)):
                lena = len(a)
                lenb = len(b)
            else:
                lena = len(a)
                lenb = 1
                b = [b]
        elif isinstance(b, (list, tuple)):
            lenb = len(b)
            lena = 1
            a = [a]
        else:
            return op(a, b)
        ret_t = type(a)
        if lena < lenb:
            a = it.cycle(a)
        elif lena > lenb:
            b = it.cycle(b)
        return ret_t(map(op, a, b))

    # TODO

    # UGen graph parameter interface #
    # TODO: ver el resto en UGenParameter

    def as_ugen_input(self, *_):
        return self.as_control_input()

    def as_control_input(self):
        pass # TODO ^this[ EventTypesWithCleanup.ugenInputTypes[this[\type] ] ];

    # TODO...


# #############################################################################
# NOTE: La esctructura de lo que sigue desde sclang.
# NOTE: Ver cómo solucionar initClass en general para todas la librería.
# NOTE: Acá la inicialización de la clase están en función aparte, pero
# NOTE: podría pasar estos método como estáticos o métodos de clase.
#
# *initClass {
#     Class.initClassTree(Server);
#     Class.initClassTree(TempoClock);
#
#     this.makeParentEvents;
#
#     StartUp.add {
#         Event.makeDefaultSynthDef;
#     };
# }
#
# *makeDefaultSynthDef { ... }
#
# NOTE: Son varibales de clase que contienen intancias de Event
# NOTE: y se llama en *initClass.
# *make_parent_events {
#     // define useful event subsets.
#     partialEvents = (
#         pitch_event: (),
#         dur_event: (),
#         amp_event: (),
#         server_event: (),
#         buffer_event: (),
#         midi_event: (),
#         node_event: (),
#         player_event: (
#             type: 'note',
#             play: #{},
#             free_server_node: #{},
#             release_server_node: #{},
#             parent_types: (), // vacío
#             event_types: (
#                 rest: #{},
#                 note: #{},
#                 grain: #{},
#                 on: #{},
#                 set: #{},
#                 off: #{},
#                 kill: #{},
#                 group: #{},
#                 par_group: #{},
#                 bus: #{},
#                 fade_bus: #{},
#                 gen: #{},
#                 load: #{},
#                 read: #{},
#                 alloc: #{},
#                 free: #{},
#                 midi: #{},
#                 set_properties: #{},
#                 mono_off: #{},
#                 mono_set: #{},
#                 mono_note: #{},
#                 Synth: #{},
#                 Group: #{},
#                 tree: #{},
#             )
#         ),
#     );
#     parentEvents = (
#         default_event: ().putAll( # NOTE: cambia el nombre por el método default de clase.
#             partialEvents.pitchEvent,
#             partialEvents.ampEvent,
#             partialEvents.durEvent,
#             partialEvents.bufferEvent,
#             partialEvents.serverEvent,
#             partialEvents.playerEvent,
#             partialEvents.midiEvent
#         ),
#         group_event: (
#             lag:
#             play:
#         ).putAll(partialEvents.nodeEvent),
#         synth_event: (
#             lag:
#             play:
#             default_msg_func:
#         ).putAll(partialEvents.nodeEvent)
#     );
#     defaultParentEvent = parentEvents.default_event; # NOTE: cambia el nombre por el método default de clase.
# }
#

def _make_default_synthdef():
    pass # TODO

def _make_parent_events():
    ### Partial Events ###

    Event.partial_events = Event()

    pitch_event = Event(
        # NOTE: De todas estas llaves tendría que revisar y escribir la
        # NOTE: especificación de las relaciones. Por ejemplo, 'harmonic' solo
        # NOTE: calcula la llave freq si la frecuencia se define desde midinote
        # NOTE: o más arriba en la cadena (puede estar definida desde note o degree).
        # NOTE: xtranspose, octave y root son escalares que tratan los posibles
        # NOTE: acordes como una unidad (todas las notas se alteran por igual como conjunto).
        # NOTE: Problema: hay semántica múltiple, con respecto a la afinación y
        # NOTE: la estructura de datos jerárquica (operaciones sobre listas).
        # NOTE: VER notas en test_scarray_op.py. Lo mismo pasa en _pe_dur.
        # NOTE: Ver el gráfico en la documentación de Event.
        mtranspose=0, # transposición modal, ESCALAR
        gtranspose=0.0, # transposición por gamut, ESCALAR
        ctranspose=0.0, # transposición cromática, ESCALAR
        octave=5.0, # transposición de octava, ESCALAR
        root=0.0, # transposición por nota base, ESCALAR
        degree=0, # grado de la escala, VECTOR/ESCALAR, actúa en conjunto: degree -> note -> midinote -> freq -> detuned_freq, ver abajo.
        scale=scl.Scale([0, 2, 4, 5, 7, 9, 11]), # BUG: Scale tiene que ser inmutable como una tupla.
        #spo=12.0, # BUG: obsoleta, siempre se usa Scale NOTE steps per octave, steps_per_octave, stepsPerOctave. No sé.
        detune=0.0, # desafinación, VECTOR/ESCALAR, se pueden necesitar las notas alteradas en afinación dentro de un acorde, esta sería la única llave que lo permite, tiene doble semántica, con respecto a la afinación y la estructura de datos jerárquica.
        harmonic=1.0, # se usa solo para calcular la llave 'freq' tal vez debería ser vector/escalar si un conjunto de armónicos es un *acorde*, PERO: puede estar pensado para una sola altura y lo mismo vale si se define que esta llave no se puede usar para polifonía, es arbitrario.
        #octave_ratio = 2.0 # BUG: obsoleta, siempre se usa Scale
    )

    # **************************************************************************
    # NOTE: para esto usar el método value(key) (singular) con kwargs **********
    # BUG IMPORTANTE: el problema es la llamada con value que hace de las ******
    # BUG IMPORTANTE: llaves que pueden ser una función o un valor escalar. ****
    # BUG IMPORTANTE: Ver sustain, abajo, como otro ejemplo claro. *************
    # BUG IMPORTANTE: Y EL USO DE valueEnvir. SE PUEDE SOLUCIONAR CON MÉTODOS **
    # BUG IMPORTANTE: value(key) y value_envir(key) en Event, value_envir: *****
    # BUG IMPORTANTE: "evaluates a function, looking up unspecified arguments **
    # BUG IMPORTANTE: in currentEnvironment", completa los argumentos como si **
    # BUG IMPORTANTE: fueran kwargs, por nombre en vez de orden, ***************
    # BUG IMPORTANTE: y automáticamente. ***************************************
    # BUG IMPORTANTE: VER valueEnvir.scd y getMsgFunc. *************************
    # **************************************************************************

    # BUG: Solucionado provisoriamente con _binop_map:
    # BUG: Todos estos métodos deberían soportar operadores aritméticos sobre
    # BUG: listas, e.g. freq = [440, 442] + detune. El problema es que
    # BUG: además estas operaciones tienen comportamiento wrapAt, para Python
    # BUG: esto es una implementación arbitraria propia de la clase Event.
    # BUG: Si se limita a un único valor por llave los eventos no pueden generar
    # BUG: varios mensajes osc (ej. acordes y strum) que es un comportamiento
    # BUG: que se usa a nivel de patrones también. Por ejemplo en Pbind no se
    # BUG: pueden anidar estructuras paralelas por evento si no es con arrays.
    # BUG: Algo que tal vez podría funcionar más claramente en Python es usar
    # BUG: tuple para los datos paralelos, en vez de sub-listas, pero
    # BUG: igualmente hay que implementar la lógica para todas las llaves posibles.
    @pitch_event.add_function
    def note(self):
        # NOTE: La documentación de Function:performDegreeToKey da un buen ejemplo de cuándo una llave de event puede actuar como una función personalizada con parámetros estándar.
        #return self.scale.degree_to_key(self.degree + self.mtranspose) # BUG, NOTE: si solo se puede usar Scale la llave spo de Event es obsoleta.
        ret = self._binop_map(op.add, self.degree, self.mtranspose) # NOTE: degree puede ser una lista, xtranspose es escalar.
        if isinstance(ret, (list, tuple)):
            return type(ret)(self.scale.degree_to_key(i) for i in ret)
        else:
            return self.scale.degree_to_key(ret)

    @pitch_event.add_function
    def midinote(self):
        # ret = self.value('note') + self.gtranspose + self.root
        # ret = ret / self.scale.spo() + self.octave - 5.0 # BUG, NOTE: si solo se puede usar Scale la llave spo de Event es obsoleta.
        # ret = ret * (12.0 * math.log2(self.scale.octave_ratio)) + 60
        # return ret
        ret = self.value('note')
        if isinstance(ret, (list, tuple)):
            # NOTE: este es un ejemplo de cómo se degrada la ejecución, arriba
            # NOTE: es solución Python, pero no implementa operaciones entre
            # NOTE: posibles vectores desde 'note'.
            ret = self._binop_map(op.add, ret, self.gtranspose)
            ret = self._binop_map(op.add, ret, self.root)
            ret = self._binop_map(op.truediv, ret, self.scale.spo())
            ret = self._binop_map(op.add, ret, self.octave)
            ret = self._binop_map(op.sub, ret, 5.0)
            ret = self._binop_map(op.mul, ret, 12 * math.log2(self.scale.octave_ratio))
            ret = self._binop_map(op.add, ret, 60)
            return ret
        else:
            ret = ret + self.gtranspose + self.root
            ret = ret / self.scale.spo() + self.octave - 5.0 # BUG, NOTE: si solo se puede usar Scale la llave spo de Event es obsoleta.
            ret = ret * (12.0 * math.log2(self.scale.octave_ratio)) + 60
            return ret

    # NOTE: Vuelto a esta posición de lectura porque las dependencias son:
    # NOTE: degree -> note -> midinote -> freq -> detuned_freq.
    # NOTE: De ser mplementadas como propiedades de objeto se podría definir
    # NOTE: una variable privada, en la representación más conveniente, es
    # NOTE: arbitraria, y que todas estas propiedades dependan de ella así
    # NOTE: se actualizan entre sí y las llaves del evento quedan siempre
    # NOTE: en estado consistente. En este caso degree actúa de esa manera,
    # NOTE: no tiene función, es solo un número de referencia, pero faltaría
    # NOTE: que todas las llaves devuelvan el valor actual consistentemente
    # NOTE: cuando se cambia el valor de a través de una llave intermedia.
    @pitch_event.add_function
    def freq(self):
        #return bi.midicps(self.value('midinote') + self.ctranspose) * self.harmonic
        ret = self.value('midinote')
        if isinstance(ret, (list, tuple)):
            ret = self._binop_map(op.add, ret, self.ctranspose)
            ret = type(ret)(bi.midicps(i) for i in ret)
            ret = self._binop_map(op.mul, ret, self.harmonic)
            return ret
        else:
            return bi.midicps(ret + self.ctranspose) * self.harmonic # NOTE: considero que 'harmonic' es ESCALAR.

    @pitch_event.add_function
    def detuned_freq(self):
        #return self.value('freq') + self.detune
        return self._binop_map(op.add, self.value('freq'), self.detune)

    @pitch_event.add_function
    def freq_to_note(self, freq): # BUG: no parece usarse en la librería de clases
        pass # BUG: TODO. # BUG: podría ser que se tome siempre ~freq y se quite el parámetro para que actúe como propiedad, ver test_event_value_midinote.py

    @pitch_event.add_function
    def freq_to_scale(self, freq): # BUG: no parece usarse en la librería de clases
        pass # BUG: TODO. # BUG: podría ser que se tome siempre ~freq y se quite el parámetro para que actúe como propiedad, ver test_event_value_midinote.py

    Event.partial_events.pitch_event = pitch_event

    dur_event = Event(
        tempo=None,
        dur=1.0,
        stretch=1.0,
        legato=0.8,
        #sustain: #{ ~dur * ~legato * ~stretch }, # BUG IMPORTANTE: aunque e.sustain evalúa la función, usa e.use{ ~sustain.value } y necesita evaluar explícitamente, pero el problema es que value anda para todo y la función se puede reemplazar por un escalar.
        lag=0.0,
        strum=0.0,
        strum_ends_together=False
        # NOTE: offset sale de timing_offset. timing_offset, según la nota en
        # NOTE: sync_with_quant, es para hacer anticipaciones temporales, y que
        # NOTE: por ejemplo un arpegio comience antes del beat.
        # BUG: La implementación actual de sclang solo invierte el orden y no usa
        # BUG: schedStrummedNote que supongo se encarga de eso?
    )

    @dur_event.add_function
    def sustain(self):
        return self.dur * self.legato * self.stretch

    Event.partial_events.dur_event = dur_event

    amp_event = Event(
        #'amp': #{ ~db.dbamp }, # BUG: es curioso que en sclang Event.parentEvents.default; e.amp tira error ~db es nil, hay que hacer e.use { e.amp.postln }, i.e. no se puede usar como llave común y corriente # BUG: es un tanto inconsistente, aunque no se use así, que db no se recalcule si se cambia amp por un escalar, lo mismo define velocity pero no la usa para calcular amp
                                # BUG: la otra opción es que las llaves se comporten como properties con getter/setter.
        db=-20.0,
        velocity=64,
        pan=0.0,
        trig=0.5
    )

    @amp_event.add_function
    def amp(self):
        return bi.dbamp(self.db)

    Event.partial_events.amp_event = amp_event

    server_event = Event(
        server=None,
        latency=None,
        synth_lib=None,
        #group: #{ ~server.defaultGroup.nodeID }
        out=0,
        add_action='addToHead',
        msg_func=None,
        instrument='default',
        variant=None,
        has_gate=True, # // assume SynthDef has gate
        send_gate=None, # // false => event does not specify note release
        args=('freq', 'amp', 'pan', 'trig'), # // for \type \set
        timing_offset=0
    )

    #########################################################################
    # ().play llama solamente a getMsgFunc y synthDefName, pero deben habero otras combinaciones.
    #########################################################################

    @server_event.add_function
    def group(self):
        # BUG: *** en NodeEvents.sc está definido como:
        # BUG: *** this.parent = Event.parentEvents[\groupEvent] y retorna self.
        # BUG: *** PERO SÍ SE LLAMA LA LLAVE CON e[\group] O ~group en 'note'!
        return self.server.default_group.node_id

    # // this function should return a msgFunc: a Function that
    # // assembles a synth control list from event values
    @server_event.add_function
    def get_msg_func(self):
        # // if user specifies a msgFunc, prefer user's choice
        if self.msg_func is None:
            #self.instrument = self.instrument.as_def_name() # BUG: asDefName es una extensión en Common/Control/asDefName, supongo que soporta cadenas/símbolos y definiciones.
            if isinstance(self.instrument, sdf.SynthDef): # BUG: el único soporte interesante es SynthDef, podría no estar y que tenga que se un str y ya.
                self.instrument = self.instrument.name # NOTE: IMPORTANTE: ESTO CREA UNA LLAVE EN EVENTOS HIJOS REEMPLAZANDO LA LLAVE DE PARENT/PROTO. ASÍ ES COMO SE PUEBLAN LOS EVENTOS EN SCLANG.
            else:
                self.instrument = self.instrument # NOTE: IMPORTANTE: ESTO CREA UNA LLAVE
            if self.synth_lib is None:
                synth_lib = sdc.SynthDescLib.default # BUG: lo cambié a default, pero está mal, tiene que ser global, pero global es una palabra reservada y tira error.
            else:
                synth_lib = self.synth_lib
            desc = synth_lib.at(self.instrument)
            if desc is not None:
                self.has_gate = desc.has_gate
                self.msg_func = desc.msg_func # BUG: SynthDesc devuelve una función creada al vuelo con make_msg_func según los parámetros de la SynthDef que se asignan con valueEnvir!!!
            else:
                self.msg_func = self.default_msg_func()
        return self.msg_func

    @server_event.add_function
    def synthdef_name(self):
        if isinstance(self.instrument, sdf.SynthDef): # BUG: el único soporte interesante es SynthDef, podría no estar y que tenga que se un str y ya.
            self.instrument = self.instrument.name
        # # // allow `nil to cancel a variant in a pattern # BUG: no entiendo por qué no alcanza solamente con nil en sclang.
        # variant = variant.dereference;
        if self.variant is not None\
        and self.synth_desc is not None\
        and self.synth_desc.has_variants():
            return '{}.{}'.format(self.instrument, self.variant)
        else:
            return self.instrument

    # BUG: esta función ni se usa ni parece funcionar para (instrument: #[a, b]),
    # BUG: no veo el sentido del flop, no parece que se pueda hacer expansión
    # BUG: multicanal en eventos. Ver function_flop.scd.
    # BUG: Y creo que en sclang las funciones generadas con SynthDesc:
    # BUG: `make`_msg_func no tienen parámetros por defecto, ver, podrían tener.
    # @server_event.add_function
    # def get_bundle_args(self):
    #     if isinstance(self.instrument, (list, tuple)):
    #         return [self.value('get_msg_func', i)() for i in self.instrument]
    #     return self.value('get_msg_func', self.instrument)() # NOTE: hace flop, EVALUA LA FUNCION POR CANTIDAD DE INSTRUMENT EN EL ARRAY (EL NOMBRE NO IMPORTA)

    @server_event.add_function
    def default_msg_func(self):
        def _(self):
            return [
                'freq', self.value('freq'), # NOTE: llave definida en _pe_pitch, tal vez debería comprobar y asignar valores por defecto como es la función en sclang, pero igual mezcla el contenido que distribuye en eventos parciales... !!!
                'amp', self.value('amp'), # NOTE: llave definida en _pe_amp
                'pan', self.value('pan'), # NOTE: llave definida en _pe_amp
                'out', self.value('out') # NOTE: llave definida acá
            ]
        return _

    # NOTE: Transcribo acá la lógica del método schedBundleArrayOnClock de
    # NOTE: SimpleNumber y SequenceableCollection por separado.
    # NOTE: schedStrumedNote no parece usarse. La última opción sería convertir
    # NOTE: esta función en método de la clase Event. Solo se usa acá y el
    # NOTE: reloj siempre es thisThread.clock.
    # NOTE: Ahora, schedStrumedNote, detectando los eventos que definen
    # NOTE: strum simplificaría la implementación factorizando los casos.
    # NOTE: Sobre todo si se considera que strum es menos habitual.
    @server_event.add_function
    def sched_bundle(self, lag, offset, server, bundle, latency=None):
        # // "lag" is a tempo independent absolute lag time (in seconds)
        # // "offset" is the delta time for the clock (usually in beats)
        if latency is None:
            latency = server.latency
        lmbd = lambda: server.send_bundle(latency, *bundle)
        if lag != 0:
            if offset != 0:
                # // schedule on both clocks
                _main.Main.current_TimeThread.clock.sched(
                    offset,
                    lambda: clk.SystemClock.sched(lag, lmbd)
                )
            else:
                # // only lag specified: schedule only on the system clock
                clk.SystemClock.sched(lag, lmbd)
        else:
            if offset != 0:
                # // only delta specified: schedule only on the clock passed in # NOTE: passed in siempre es thisThread.clock
                _main.Main.current_TimeThread.clock.sched(offset, lmbd)
            else:
                # // no delays: send directly
                lmbd()

    @server_event.add_function
    def sched_bundle_list(self, lag, offset, server, bundles, latency=None):
        # // "lag" is a tempo independent absolute lag time (in seconds)
        # // "offset" is the delta time for the clock (usually in beats)
        # NOTE: originalmente offset es this, es SequenceableCollection al usar ~schedBundleArray que usa schedBundleArrayOnClock
        if latency is None:
            latency = server.latency
        lmbd = lambda i: server.send_bundle(latency, bundles[i % len(bundles)])
        if lag != 0:
            lag = utl.as_list(lag)
            for i, delta in enumerate(offset):
                if delta != 0:
                    # // schedule on both clocks
                    _main.Main.current_TimeThread.clock.sched(
                        delta,
                        ft.partial(lambda i: clk.SystemClock.sched(
                            lag[i % len(lag)],
                            lambda: lmbd(i)
                        ), i) # NOTE: Esto es feo en Python. Se necesita la evaluación parcial para que la variable libre i quede fija en el contexto de la lambda exterior. En sclang cada iteración es una función e 'i' es un argumetno. Ver refactorizaciones posibles.
                    )
                else:
                    # // only lag specified: schedule only on the system clock
                    clk.SystemClock.sched(
                        lag[i % len(lag)],
                        ft.partial(lambda i: lmbd(i), i)
                    )
        else:
            for i, delta in enumerate(offset):
                if delta != 0:
                    # // only delta specified: schedule only on the clock passed in # NOTE: passed in siempre es thisThread.clock
                    _main.Main.current_TimeThread.clock.sched(
                        delta,
                        ft.partial(lambda i: lmbd(i), i)
                    )
                else:
                    # // send directly
                    lmbd(i)

    # @server_event.add_function
    # def sched_strummed_note():
    #     pass

    Event.partial_events.server_event = server_event

    # BUG: ESCRIBURA DE LAS LLAVES. POR QUÉ ES ESPECIAL? DEBERÍA AGREGAR _? LEAVEOPEN ESTABA EN NOTACIÓN CAMELLO.
    buffer_event = Event(
        bufnum=0,
        filename='',
        frame=0,
        numframes=0,
        numchannels=1,
        gencmd='sine1',
        genflags=7,
        genarray=[1],
        bufpos=0,
        leaveopen=0
    )

    Event.partial_events.buffer_event = buffer_event

    # BUG: este 'event' en realidad define la intefaz de las funciones MIDI
    # BUG: que luego se llaman como Event Types de EventPlayer MidiEvent...
    # BUG: Partial Events tal vez no sean realmente 'Events', sino parámetros
    # BUG: (parciales) aplicados a los PlayerEvent Event Types. Pero ver Node,
    # BUG: Server, Buffer, Amp, Dur, Pitch Events. Poruqe define componentes
    # BUG: estáticos del servidor.
    midi_event = Event(
        # TODO
    )

    Event.partial_events.midi_event = midi_event

    # BUG: Event:node_id es una interfaz hibrida entre evento y nodo, para los
    # BUG: nodeEvent, está implementada en NodeEvents.sc, ahí explica su posible uso
    # BUG: con \Synth y \Group
    node_event = Event(
        # TODO
    )

    Event.partial_events.node_event = node_event

    player_event = Event(
        type='note',
        parent_types=Event() # NOTE: está justo antes de event types
    )

    @player_event.add_function
    def play_func(self):
        # NOTE: Esto incluso podría no estar, es una customización de la
        # NOTE: customización, y bastante específica/confusa sobre cómo se
        # NOTE: puede usar, componer eventos es más fácil. Y esto borra las
        # NOTE: llaves de defaultParentEvent, eso no lo entiendo.
        parent_type = self.parent_types.get(self.type)
        if parent_type is not None:
            super(type(self), self).__setattr__('parent', parent_type) # NOTE: creo que es correcto así, el método puede no estar boundeado como en las clases.
        self.server = self.server or srv.Server.default

        # NOTE: buscar la documentación de esta llave.
        finish = self.get('finish')
        if finish is not None:
            finish(self)

        tempo = self.get('tempo')
        if tempo is not None:
            _main.Main.current_TimeThread.clock.tempo = tempo # BUG: ESTO ES ASÍ PERO NO ME GUSTA NADA¡

        if not self.is_rest(): # BUG: falta definir is_rest, tengo que ver la implementación a bajo nivel y la clase Rest, no puede ser propiedad, no puede llamarse rest porque confunde con el event_type 'rest'.
            type_func = self.event_types.get(self.type)\
                        or self.event_types['note']
            type_func(self, self.server) # BUG: OJO, OJO: event_types ES OTRO evento en el cual se definen funciones ('note', 'set', etc.), en esas funciones el primero argumentos no hay que llamarlo self porque recibe otro evento que es este self (quien llama)! Eso es porque evalua todo con event.use{} y el alcance dinámico.

        # NOTE: buscar la documentación de esta llave.
        callback = self.get('callback')
        if callback is not None:
            callback(self)

    # BUG: No entiendo por qué esta nota está en este lugar, parece que refiere al comportamiento general del evento, no sé qué son los cleanup events.
    # // synth / node interface
    # // this may be better moved into the cleanup events, but for now
    # // it avoids confusion.
    # // this is a preliminary implementation and does not recalculate dependent
    # // values like degree, octave etc.

    @player_event.add_function
    def free_server_node(self): # NOTE: No se usa dentro de Event.
        pass # TODO

    # // for some yet unknown reason, this function is uncommented,
    # // it breaks the play method for gatelesss synths

    @player_event.add_function
    def release_server_node(self): # BUG: arg releaseTime. # NOTE: No se usa dentro de Event.
        pass # TODO

    ### Event Types ###

    # NOTE: son tipos de player_event en realidad, no sé por qué está hecho como está hecho.
    event_types = Event()

    @event_types.add_function
    def rest(event, server):
        pass # really empty

    @event_types.add_function
    def note(event, server):
        freqs = event.detuned_freq()
        # // msgFunc gets the synth's control values from the Event
        msg_func = event.get_msg_func()
        instrument_name = event.synthdef_name()
        # // determine how to send those commands
        # // sendGate == false turns off releases
        send_gate = event.send_gate or event.has_gate
        # // update values in the Event that may be determined by functions
        event.freq = freqs
        event.amp = event.value('amp')
        sustain = event.sustain = event.value('sustain') # BUG: posiblemente en sclang, el problema es que asume que el evento se crea desde un stream y se descarta.
        lag = event.lag
        offset = event.timing_offset
        strum = event.strum
        event.server = server # BUG: esto es redundante en sclang porque se setea en 'play', pero tengo que ver si este event_type se llama desde otra parte.
        event.is_playing = True
        add_action = nod.Node.action_number_for(event.add_action)
        # // compute the control values and generate OSC commands
        ids = None # BUG: debería posponer su declaración al momento en que se usa abajo y acá usar None como literal. NOTE: Es None por defecto y modifica el mensaje después generando ids.
        group = node_param(event.value('group')).as_control_input() # BUG: y así la llave 'group' que por defecto es una funcion que retorna node_id no tendría tanto sentido? VER PERORATA ABAJO EN GRAIN
        bndl = ['/s_new', instrument_name, ids, add_action, group] # event.value('group')] # NOTE: ~group en realidad deja una función acá, no el valor de retorno, parece que se evalúa en _NetAddr_SendBundle.
        bndl.extend(msg_func()) # NOTE: si se obtiene como atributo es un bound method de self (msg_func necesita el evento argumento para comprobar las llaves).

        # NOTE: Esta condición define que sustain, offset (timing_offset) y lag
        # NOTE: pueden ser listas y que las llaves están todas relacionadas con strum.
        if strum == 0 and ( (send_gate and isinstance(sustain, list))\
        or isinstance(offset, list) or isinstance(lag, list) ):
            # NOTE: Creo que flopTogether se está usando para un caso borde.
            # NOTE: *** AUNQUE NO ESTOY SEGURO ***
            # NOTE: Como bndl es siempre un array de una dimensión, lo que
            # NOTE: hace es flop de sustain, lag y offset, que incluso pueden
            # NOTE: tener una sola dimensión, y luego multiplica bndl, pero
            # NOTE: se queda con uno solo, bndl[0] ... Tendría que ver todos
            # NOTE: los casos posibles que están restringidos a los parámetros
            # NOTE: usados dentro de esta función arriba: instrument_name (que
            # NOTE: en sclang tira error si instrument es un array), ids
            # NOTE: (que es siempre None acá), add_action, grupo y msg_func.
            bndl = utl.flop_together(bndl, [sustain, lag, offset])
            sustain, lag, offset = utl.flop(bndl[1])
            bndl = bndl[0]
        else:
            bndl = utl.flop(bndl) # NOTE: flop lo usa como bubble la mayoría de los casos pero es porque puede que sean varios mensajes si algún parámetro es array.
        # // produce a node id for each synth
        event.id = ids = [server.next_node_id() for _ in bndl]
        for i, b in enumerate(bndl):
            b[2] = ids[i]
            bndl[i] = node_param(b).as_osc_arg_list() # NOTE: modifico el item de la lista sobre el cuál itero al final del ciclo, pero no la lista en sí.
        # // schedule when the bundles are sent
        if strum == 0:
            event.sched_bundle(lag, offset, server, bndl, event.latency) # NOTE: puede ser cualquier cantidad de mensajes/notas, esto es algo que no está claro en la implementación de sclang, aquí offset es escalar, en strummed es una lista.
            if send_gate:
                event.sched_bundle(
                    lag,
                    sustain + offset,
                    server,
                    utl.flop(['/n_set', ids, 'gate', 0]),
                    event.latency
                )
        else:
            if strum < 0: # *** BUG *** ESTO ESTABA MAL EN SCLANG SEGÚN EL COMENTARIO DE sync_with_quant, timing_offset permite que los strum sean en levare (!) entonces no invierte el orden de las notas (!)
                bndl.reverse()
                ids.reverse() # NOTE: faltaba, eran un bug en sclang.
            strum = abs(strum) # NOTE: reuso la variable, no se necista más el valor anterior.
            #strum_offset = offset + [x * strum for x in range(0, len(bndl))] # BUG: offset puede ser un array y/o debe sumarse punto a punto.
            strum_offset = [offset + x * strum for x in range(0, len(bndl))] # BUG: el if anterior considera que offset puede ser una lista pero offset sale de timmming_offset que es un parámetro de server_event (ver nota arriba), tampoco vi dónde se explica ni por qué está, la latencia del servidor es latency. en sched_bundle(_list), implementado como schedBundleArrayOnClock dice: // "offset" is the delta time for the clock (usually in beats)
            event.sched_bundle_list(lag, strum_offset, server, bndl, event.latency)
            if send_gate:
                if event.strum_ends_together:
                    strum_offset = event._binop_map(op.add, sustain, offset) # NOTE: sustain puede ser lista definida por el usuario, offset creo que no, pero no estoy seguro, el código de arriba considera que sí, el problema es que nunca vi el uso de timingOffset en sclang.
                    if not isinstance(strum_offset, (list, tuple)):
                        strum_offset = [strum_offset] * len(bndl) # BUG: El problema es que sched_bundle_list solo acepta listas, por no usar as list y hacer esto allá, pero aún tengo que ver cómo se comportan todas las otras llamadas de ~schedBundleArrya en sclang.
                                                                  # BUG: Otra cosa, haciendo esta línea me doy cuenta que las operaciones vectoriales de sclang son semánticamente anti-pitónicas.
                else:
                    strum_offset = event._binop_map(op.add, sustain, strum_offset) # NOTE: tanto sustain como strum_offset pueden ser arrays.
                event.sched_bundle_list(
                    lag,
                    strum_offset,
                    server,
                    utl.flop(['/n_set', ids, 'gate', 0]),
                    event.latency
                )

    # // optimized version of type \note, about double as efficient.
    # // Synth must have no gate and free itself after sustain.
    # // Event supports no strum, no conversion of argument objects to controls
    @event_types.add_function
    def grain(event, server):
        freqs = event.detuned_freq()

        # // msgFunc gets the synth's control values from the Event
        try:
            if event.synth_lib is None:
                instrument_desc = sdc.SynthDescLib.default.at(event.instrument)
            else:
                instrument_desc = event.synth_lib.at(event.instrument)
        except KeyError: # ***** BUG: ver synthdesc.py L467 método match de SynthDescLib, es otro caso relacionado, no se si conviene agarrar el error o que SynthDescLib.at() devuelva None si no existe la llave.
            msg = "Event: instrument '{}' not found in SynthDescLib"
            warnings.warn(msg.format(event.instrument))
            return # BUG: en sclang retorno this, que es el intérprete, pero no tiene sentido porque se llama desde playerEvent['play'] y no hace nada con el valor de retorno, debería retornar nil?
        msg_func = instrument_desc.msg_func
        instrument_name = event.synthdef_name()

        # // update values in the Event that may be determined by functions
        event.freq = freqs
        event.amp = event.value('amp')
        event.sustain = event.value('sustain') # BUG: posiblemente en sclang, el problema es que asume que el evento se crea desde un stream y se descarta.
        add_action = nod.Node.action_number_for(event.add_action)

        # BUG IMPORTANTE: PARA TODO ESTO QUEDÓ IMPLEMENTANDO PROVISORIAMENTE NodeParameter.as_control_input como return ugen_param(self).as_control_input()
        # BUG IMPORTANTE: en sclang usa ~group.asControlInput que retorna nodeID (y debería hacer lo mismo para la función 'note' arriba aunque como anoté deja la función y se evalúa abajo nivel)
        # BUG IMPORTANTE: de un grupo o this de un entero, y la llave group acá se
        # BUG IMPORTANTE: define como node id. *********** PERO ***********
        # BUG IMPORTANTE: en graph_param.py as_control_input funciona para Group
        # BUG IMPORTANTE: si se llama a node_param: node_param(g).as_control_input()
        # BUG IMPORTANTE: pero no funciona para int: node_param(1000).as_control_input() -> AttributeError: 'NodeScalar' object has no attribute 'as_control_input'
        # BUG IMPORTANTE: y funciona para int si se llama a ugen_param: ugen_param(1000).as_control_input()
        # BUG IMPORTANTE: pero no funicona para Group:ugen_param(g).as_control_input() -> TypeError: UGenParameter: type 'Group' not supported
        # BUG IMPORTANTE: as_control_input, por más que sea interfaz de los Nodos
        # BUG IMPORTANTE: TIENE QUE FUNCIONAR TAMBIÉN PARA ENTEROS DESDE NODE_PARAM ¿Por qué no quedó así?
        # BUG IMPORTANTE: Y buscando, veo que la clase BusPlug tiene el método asControlInput que retorna u símbolo como si fuera asMap !!!!!!!!!!!!!!!
        # BUG IMPORTANTE: Y la documentacionde Event.asControlInput dice "Enables events to represent the server resources they created in an Event."
        # BUG IMPORTANTE: Y la documentacion de Ref.asControlInput dice "Returns the value - this is used when sending a Ref as a control value to a server Node."
        # BUG IMPORTANTE: Vamos ¿Quién miente? Por Ref, ahora creo que asControlInput es interface de Node y UGen.
        # BUG IMPORTANTE: El problema de pasar as_control_input a GraphParameter es que class UGenList(UGenParameter) lo redefine y se usa en NodeParameter a través de ugen_param.
        # BUG IMPORTANTE: Pero también es claro que el método tiene que actuar polimoficamente entre int y Group para esta llave.
        # BUG IMPORTANTE: Tal vez solo convenga definir GraphParameter en vez de dividir entre Node y UGen? Pero no es lo mismo, por UGen no usa as_target.
        # BUG IMPORTANTE: Otra opción es definir NodeParameter.as_control_input como return ugen_param(self).as_control_input().
        # BUG IMPORTANTE: Pienso que los as_control_inputs se pueden pasar a los nodos que se pasan a las ugens, que debería ser de ambas.
        # BUG IMPORTANTE: IMPLEMENTANDO NodeParameter.as_control_input como return ugen_param(self).as_control_input()
        # BUG IMPORTANTE: EL ÚNICO CASO QUE NO FUNCIONA ES ugen_param(g).as_control_input() -> TypeError: UGenParameter: type 'Group' not supported
        # BUG IMPORTANTE: PERO LA UGEN Free.kr USA NODE ID COMO PARÁMETRO ASÍ QUE NODE DEBERÍA IMPLEMENTAR LA INTERFAZ.
        # BUG IMPORTANTE: HAY QUE HACER UNA ESPECIFICACIÓN/MODELO DE LOS DATOS VÁLIDOS, SU SIGNIFICADO Y SUS RELACIONES POSIBLES COMO PARÁMETROS VÁLIDOS PARA DISTINTAS ESTRUCTURAS (E.G. NODOS Y UGENS)
        # BUG IMPORTANTE: El problema es que ugen_param es una interfaz de polimorfismo que de objetos UGen aplicada a datos integrados (int, str, list, etc.)
        # BUG IMPORTANTE: y que node_param es una interfaz de polimorfismo que de objetos de objetos Node aplicada a datos integrados (int, str, list, etc.)
        # BUG IMPORTANTE: y que as_control_input es un método de interfaz presente en ambas UGen y Node, y que en sclang cualquier objeto puede actuar as_control_input.
        # BUG IMPORTANTE: El problema son los datos de entrada válidos y el abuso de polimofismo en sclang, flata organizar y especificar como puse acá arriba.
        # BUG IMPORTANTE: VER Pattern Guide 08: Event Types and Parameters.
        # // compute the control values and generate OSC commands
        group = node_param(event.value('group')).as_control_input() # BUG: y así la llave 'group' que por defecto es una funcion que retorna node_id no tendría tanto sentido?
        bndl = ['/s_new', instrument_name, -1, add_action, group] # NOTE: ~group en realidad deja una función acá, no el valor de retorno, parece que se evalúa en _NetAddr_SendBundle.
        bndl.extend(msg_func(event)) # NOTE: como no se obtuvo como atributo de Event no es un bound method de self y hay que pasar event.
        event.sched_bundle( # NOTE: puede ser cualquier cantidad de mensajes/notas, esto es algo que no está claro en la implementación de sclang
            event.lag, # BUG: en sclang define la variable lag dentro de la funcion de la llave pero no la usa, usa ~lag de event.
            event.timing_offset,
            server,
            utl.flop(bndl),
            event.latency
        )

    @event_types.add_function
    def on(event, server):
        pass # TODO

    @event_types.add_function
    def set(event, server):
        pass # TODO

    @event_types.add_function
    def off(event, server):
        pass # TODO

    @event_types.add_function
    def kill(event, server):
        pass # TODO

    @event_types.add_function
    def group(event, server):
        pass # TODO

    @event_types.add_function
    def par_group(event, server):
        pass # TODO

    @event_types.add_function
    def bus(event, server):
        pass # TODO

    @event_types.add_function
    def fade_bus(event, server):
        pass # TODO

    @event_types.add_function
    def gen(event, server):
        pass # TODO

    @event_types.add_function
    def load(event, server):
        pass # TODO

    @event_types.add_function
    def read(event, server):
        pass # TODO

    @event_types.add_function
    def alloc(event, server):
        pass # TODO

    @event_types.add_function
    def free(event, server):
        pass # TODO

    @event_types.add_function
    def midi(event, server): ### **** BUG **** se repite con Partial Event ***
        pass # TODO

    @event_types.add_function
    def set_properties(event): #, server): # BUG: no tiene server como arg
        pass # TODO

    @event_types.add_function
    def mono_off(event, server):
        pass # TODO

    @event_types.add_function
    def mono_set(event, server):
        pass # TODO

    @event_types.add_function
    def mono_note(event, server):
        pass # TODO

    @event_types.add_function
    def Synth(event, server): # BUG: es con mayúsculas porque tiene significado especial, ### *** BUG *** por qué no sería NodeEvents que es un Partial Event
        pass # TODO

    @event_types.add_function
    def Group(event, server): # BUG: es con mayúsculas porque tiene significado especial, ### *** BUG *** por qué no sería NodeEvents que es un Partial Event
        pass # TODO

    @event_types.add_function
    def tree(event, server):
        pass # TODO

    player_event.event_types = event_types
    Event.partial_events.player_event = player_event

    ### Parent Events ###

    Event.parent_events = Event()

    default_event = Event(
        **Event.partial_events.pitch_event,
        **Event.partial_events.amp_event, # NOTE: el orden de las definiciones, que sigo, está mal en sclang
        **Event.partial_events.dur_event,
        **Event.partial_events.buffer_event,
        **Event.partial_events.server_event,
        **Event.partial_events.player_event,
        **Event.partial_events.midi_event
    )

    Event.parent_events.default_event = default_event

    # NOTE: estos definen play, los de arriba definen la función que llama dentro play definido en player_event
    group_event = Event( # *** BUG *** se repite con Partial Event, tal vez por eso allá estén en mayúscula.
        lag=0,
        **Event.partial_events.node_event
    )

    @group_event.add_function
    def play_func(self):
        pass # TODO

    Event.parent_events.group_event = group_event

    synth_event = Event( ### *** BUG *** se repite con Partial Event, tal vez por eso allá estén en mayúscula.
        lag=0,
        **Event.partial_events.node_event
    )

    @synth_event.add_function
    def play_func(self):
        pass # TODO

    Event.parent_events.synth_event = synth_event

    ### Default Parent Event ###

    Event._default_parent_event = Event.parent_events.default_event


# NOTE: se llaman desde init_class/initClass, BUG: ver organización.
_make_parent_events()
# StartUp.add { _make_default_synthdef() }
