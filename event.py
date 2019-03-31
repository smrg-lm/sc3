"""Event.sc"""

import types


class Event(dict):
    default_parent_event = {}
    parent_events = {}
    partial_events = {}

    # BUG: tengo que ver la documentación, en update los parámetros actúan igual
    def __init__(self, *args, **kwargs): # know = always True
        super().__init__(*args, **kwargs)
        super().__setattr__('proto', self.pop('proto', None))
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
    # NOTE: https://docs.python.org/3/reference/datamodel.html#object.__getattribute__
    # NOTE: https://docs.python.org/3/reference/datamodel.html#special-lookup
    # NOTE: https://docs.python.org/3/library/types.html#types.FunctionType
    # NOTE: VER: módulo types, porque usa types.MethodType to a bound instance method object,
    # NOTE: y es una manera de pasar self: "Define names for built-in types that aren't directly accessible as a builtin."
    def __getattr__(self, name):
        try:
            attr = self[name]
        except KeyError:
            if self.proto is not None:
                try:
                    attr = self.proto[name]
                except KeyError:
                    if self.parent is not None:
                        try:
                            attr = self.parent[name]
                        except KeyError:
                            attr = KeyError
        if attr is KeyError:
            msg = "'{}' has not attribute or key '{}'"
            raise AttributeError(msg.format(type(self).__name__, name))
        else:
            if isinstance(attr, types.FunctionType):
                # BUG: el problema es que por más que llame a Event.use, las variables con tilde siempre leen del entorno actual y puede cambiar
                return types.MethodType(attr, self) # NOTE: esta es la forma correcta para que pase self primero siempre (no se puede fácil con FunctionType), ahora, self siempre tiene que estar declarada también. Cuando se llama con at no se pasa self en SuperCollider.
            else:
                return attr


    def __delattr__(self, name):
        if hasattr(type(self), name):
            raise AttributeError(f"attribute '{name}' can't be deleted")
        del self[name]

    def __repr__(self):
        return f'{type(self).__name__}({super().__repr__()})'

    # UGen graph parameter interface #
    # TODO: ver el resto en UGenParameter

    def as_ugen_input(self, *_):
        return self.as_control_input()

    def as_control_input(self):
        pass # TODO ^this[ EventTypesWithCleanup.ugenInputTypes[this[\type] ] ];

    # TODO...


### Partial Events ###


class PitchEvent(Event):
    def _init(self):
        self.mtranspose = 0
        self.gtranspose = 0.0
        self.ctranspose = 0.0
        self.octave = 5.0
        self.root = 0.0
        self.degree = 0
        self.scale = (0, 2, 4, 5, 7, 9, 11) # NOTE: ESTO SÍ ES UNA TUPLA EN VEZ DE UNA LISTA?
        self.spo = 12.0 # NOTE steps per octave, steps_per_octave, stepsPerOctave. No sé.
        self.detune = 0.0
        self.harmonic = 1.0
        self.octave_ratio = 2.0

    # BUG: son property en realidad, al setear las llaves sobreescribe la función por un valor.
    # BUG: ver si las pongo como llaves o como propiedades. El ejemplo clave es
    # BUG: freq, que por defecto depende de (~midinote.value + ~ctranspose).midicps * ~harmonic;
    # BUG: o midinote! y que se puedan llamar indistintamente como función o propiedad también es problema.
    # BUG: cuando se especifica midinote. Pero en el otro extremo hay funciones
    # BUG: como freqToNote y freqToScale, que actúan más como métodos.
    def note(self):
        # NOTE: usa degreeToKey, que es un método polimórfico y una UGen, por algo le dieron relevancia, pero ver la clase Scale porque me resulta redundante.
        pass

    def midinote(self):
        pass

    def detuned_freq(self):
        pass

    def freq(self):
        pass

    def freq2note(self, freq): # BUG: nombre. midicps, ampdb, freqnote/freqscale? freq_to_note?
        pass

    def freq2scale(self, freq):
        pass


class DurEvent(Event):
    pass


class AmpEvent(Event):
    pass


class ServerEvent(Event):
    pass


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


class NodeEvent(Event):
    pass


class PlayerEvent(Event):
    pass


### Event Types ###

# BUG: son tipos de PlayerEvent en realidad, no sé por qué está hecho como está hecho.

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
