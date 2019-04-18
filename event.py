"""Event.sc"""

import types
import math

import supercollie.builtins as bi
import supercollie.scale as scl
import supercollie.synthdef as sdf
import supercollie.synthdesc as sdc
import supercollie.main as _main
import supercollie.utils as utl
from supercollie.graphparam import node_param
import supercollie.clock as clk
import supercollie.server as srv
import supercollie.node as nod


# NOTE: para putAll -> Event({**a, **b, **c, ...}) en vez de updates... (>= Python 3.5)


class Event(dict):
    default_parent_event = {}
    parent_events = {}
    partial_events = {}

    # BUG: tengo que ver la documentación, en update los parámetros actúan igual
    def __init__(self, *args, **kwargs): # know = always True
        super().__init__(*args, **kwargs)
        super().__setattr__('proto', self.pop('proto', None)) # BUG: se puede escribir la llave proto/parent luego pero siempre llama al atributo.
        super().__setattr__('parent', self.pop('parent', None))

    # NOTE: set/get/del es simplemente para implementar y las llamadas a super
    # __setattr__ son solo por know = always True, no se si realmente hace
    # alguna diferencia...
    def __setattr__(self, name, value):
        if hasattr(type(self), name):
            raise AttributeError(f"attribute '{name}' can't be used as key")
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
        if hasattr(type(self), name):
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

    def is_rest(self):
        return False # BUG: ************************ TODO: por qué está implementado a bajo nivel?

    # TODO

    # UGen graph parameter interface #
    # TODO: ver el resto en UGenParameter

    def as_ugen_input(self, *_):
        return self.as_control_input()

    def as_control_input(self):
        pass # TODO ^this[ EventTypesWithCleanup.ugenInputTypes[this[\type] ] ];

    # TODO...


### Partial Events ###


def _pe_pitch():
    pitch_event = Event(
        mtranspose = 0,
        gtranspose = 0.0,
        ctranspose = 0.0,
        octave = 5.0,
        root = 0.0,
        degree = 0,
        scale = scl.Scale([0, 2, 4, 5, 7, 9, 11]), # BUG: Scale tiene que ser inmutable como una tupla.
        #spo = 12.0, # BUG: obsoleta, siempre se usa Scale NOTE steps per octave, steps_per_octave, stepsPerOctave. No sé.
        detune = 0.0,
        harmonic = 1.0,
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

    @pitch_event.add_function
    def note(self):
        # NOTE: La documentación de Function:performDegreeToKey da un buen ejemplo de cuándo una llave de event puede actuar como una función personalizada con parámetros estándar.
        return self.scale.degree_to_key(self.degree + self.mtranspose) # BUG, NOTE: si solo se puede usar Scale la llave spo de Event es obsoleta.

    @pitch_event.add_function
    def midinote(self):
        ret = self.value('note') + self.gtranspose + self.root
        ret = ret / self.scale.spo() + self.octave - 5.0
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
        return bi.midicps(self.value('midinote') + self.ctranspose) * self.harmonic

    @pitch_event.add_function
    def detuned_freq(self):
        self.value('freq') + self.detune

    @pitch_event.add_function
    def freq_to_note(self, freq): # BUG: no parece usarse en la librería de clases
        pass # BUG: TODO. # BUG: podría ser que se tome siempre ~freq y se quite el parámetro para que actúe como propiedad, ver test_event_value_midinote.py

    @pitch_event.add_function
    def freq_to_scale(self, freq): # BUG: no parece usarse en la librería de clases
        pass # BUG: TODO. # BUG: podría ser que se tome siempre ~freq y se quite el parámetro para que actúe como propiedad, ver test_event_value_midinote.py

    return pitch_event


def _pe_dur():
    dur_event = Event(
        tempo = None,
        dur = 1.0,
        stretch = 1.0,
        legato = 0.8,
        #sustain: #{ ~dur * ~legato * ~stretch }, # BUG IMPORTANTE: aunque e.sustain evalúa la función, usa e.use{ ~sustain.value } y necesita evaluar explícitamente, pero el problema es que value anda para todo y la función se puede reemplazar por un escalar.
        lag = 0.0,
        strum = 0.0,
        strum_ends_together = False
    )

    @dur_event.add_function
    def sustain(self):
        return self.dur * self.legato * self.stretch

    return dur_event


def _pe_amp():
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

    return amp_event


def _pe_server():
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
    # BUG: make_msg_func no tienen parámetros por defecto, ver, podrían tener.
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

    # NOTE: transcribo acá la lógica del método schedBundleArrayOnClock de
    # NOTE: SimpleNumber (método que también define SequenceableCollection).
    # NOTE: No estoy teniendo en cuenta la nota de eficiencia en sclang.
    # NOTE: Estoy utilizando el nombre más simple, sched_bundle, porque
    # NOTE: ~schedBundleArray hace exactamente lo mismo pero sin latency.
    # NOTE: schedStrumedNote no parece usarse. La última opción sería
    # NOTE: convertir esta función en método de la clase Event.
    @server_event.add_function
    def sched_bundle(self, lag, offset, server, bundle, latency=None):
        print('*** Event.sched_bundle bundle = ', bundle)
        lmbd = lambda: server.send_bundle(latency or server.latency, *bundle)
        # // "offset" is the delta time for the clock (usually in beats)
        # // "lag" is a tempo independent absolute lag time (in seconds)
        if lag != 0:
            if offset != 0:
                # // schedule on both clocks
                _main.Main.current_TimeThread.clock(
                    offset,
                    lambda: clk.SystemClock.sched(lag, lmbd)
                )
            else:
                # // only lag specified: schedule only on the system clock
                clk.SystemClock.sched(lag, lmbd)
        else:
            if offset != 0:
                # // only delta specified: schedule only on the clock passed in
                _main.Main.current_TimeThread.clock(offset, lmbd)
            else:
                # // no delays: send directly
                lmbd()


    # // it is more efficient to directly use schedBundleArrayOnClock
    # // we keep these for compatibility.
    # @server_event.add_function
    # def sched_bundle_list():
    #     pass
    # @server_event.add_function
    # def sched_strummed_note():
    #     pass

    return server_event


class BufferEvent(Event):
    pass


### BUG: este 'event' en realidad define la intefaz de las funciones MIDI
### BUG: que luego se llaman como Event Types de EventPlayer MidiEvent...
### BUG: Partial Events tal vez no sean realmente 'Events', sino parámetros
### BUG: (parciales) aplicados a los PlayerEvent Event Types. Pero ver Node,
### BUG: Server, Buffer, Amp, Dur, Pitch Events. Poruqe define componentes
### BUG: estáticos del servidor.
class MidiEvent(Event): # BUG: todo en mayúsculas no me convence...
    pass


# BUG: Event:node_id es una interfaz hibrida entre evento y nodo, para los
# BUG: nodeEvent, está implementada en NodeEvents.sc, ahí explica su posible uso
# BUG: con \Synth y \Group
class NodeEvent(Event):
    pass


def _pe_player():
    player_event = Event(
        type='note',
        parent_types=Event() # NOTE: está justo antes de event types
    )

    @player_event.add_function
    def play(self): # BUG: esto podría ser un método?
        parent_type = self.parent_types.get(self.type)
        if parent_type is not None:
            self.parent = parent_type # BUG: esto escribe parent como una llave y se pierde la propiedad parent, creo que conviene definir parent y proto como @property
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
    def free_server_node(self):
        pass

    # // for some yet unknown reason, this function is uncommented,
    # // it breaks the play method for gatelesss synths

    @player_event.add_function
    def release_server_node(self): # BUG: arg releaseTime
        pass

    ### Event Types ###

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
        sustain = event.sustain = event.value('sustain')
        lag = event.lag
        offset = event.timing_offset
        strum = event.strum
        event.server = server # BUG: esto es redundante en sclang porque se setea en 'play', pero tengo que ver si este event_type se llama desde otra parte.
        event.is_playing = True
        add_action = nod.Node.action_number_for(event.add_action)
        # // compute the control values and generate OSC commands
        ids = None # NOTE: Es None por defecto y modifica el mensaje después generando ids.
        bndl = ['/s_new', instrument_name, ids, add_action, event.value('group')]
        bndl.extend(msg_func()) # NOTE: si se obtiene como atributo es un bound method de self.

        if strum == 0 and ( (send_gate and isinstance(sustain, list))\
        or isinstance(offset, list) or isinstance(lag, list) ):
            pass # BUG: TODO: flopTogether
        else:
            bndl = utl.flop(bndl)
        # // produce a node id for each synth
        event.id = ids = [server.next_node_id() for _ in bndl]
        for i, b in enumerate(bndl):
            b[2] = ids[i]
            bndl[i] = node_param(b).as_osc_arg_list()
        # // schedule when the bundles are sent
        if strum == 0:
            event.sched_bundle(lag, offset, server, bndl, event.latency)
            if send_gate:
                event.sched_bundle(
                    lag,
                    sustain + offset,
                    server,
                    utl.flop(['/n_set', ids, 'gate', 0]),
                    event.latency
                )
        else:
            pass # BUG: TODO: strum

    # TODO: sigue...

    player_event.event_types = event_types
    return player_event


### TEST ###
### BUG: ir pasando para abajo ###
### NOTE: ver test_event_value_midinote.py
### NOTE: hacer serverEvent y playerEvent ahora
Event.default_parent_event = Event(
    **_pe_pitch(),
    **_pe_amp(), # NOTE: el orden de las definiciones, que sigo, está mal en sclang
    **_pe_dur(),
    **_pe_server(),
    **_pe_player()
    # ...
)


### Event Types ###

# BUG: son tipos de PlayerEvent en realidad, no sé por qué está hecho como está hecho.

class PlayerEvent: pass # BORRAR

class RestEvent(PlayerEvent):
    pass


class NoteEvent(PlayerEvent):
    pass


# // optimized version of type \note, about double as efficient.
# // Synth must have no gate and free itself after sustain.
# // Event supports no strum, no conversion of argument objects to controls
class GrainEvent(PlayerEvent):
    pass


class OnEvent(PlayerEvent):
    pass


class SetEvent(PlayerEvent):
    pass


class OffEvent(PlayerEvent):
    pass


class KillEvent(PlayerEvent):
    pass


class GroupEvent(PlayerEvent):
    pass


class ParGroupEvent(PlayerEvent):
    pass


class BusEvent(PlayerEvent):
    pass


class FadeBusEvent(PlayerEvent):
    pass


class GenEvent(PlayerEvent):
    pass


class LoadEvent(PlayerEvent):
    pass


class ReadEvent(PlayerEvent):
    pass


class AllocEvent(PlayerEvent):
    pass


class FreeEvent(PlayerEvent):
    pass


# class MidiEvent(PlayerEvent): ### **** BUG **** se repite con Partial Event ***
#     pass


class SetPropertiesEvent(PlayerEvent):
    pass


class MonoOffEvent(PlayerEvent):
    pass


class MonoSetEvent(PlayerEvent):
    pass


class MonoNoteEvent(PlayerEvent):
    pass


class SynthEvent(PlayerEvent): ### *** BUG *** por qué no sería NodeEvents que es un Partial Event
    pass


class GroupEvent(PlayerEvent): ### *** BUG *** por qué no sería NodeEvents que es un Partial Event
    pass


class TreeEvent(PlayerEvent):
    pass


### Parent Events ###


class DefaultEvent(Event):
    pass


### BUG: estos definen play, los de arriba definen la función que llama dentro
### BUG: play definido en PlayerEVent
class GroupEvent(Event): ### *** BUG *** se repite con Partial Event, tal vez por eso allá estén en mayúscula.
    pass


class SynthEvent(Event): ### *** BUG *** se repite con Partial Event, tal vez por eso allá estén en mayúscula.
    pass


# BUG: defaultParentEvent = parentEvents.default;
