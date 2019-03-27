"""Event.sc"""


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
    # alguna diferencia realmente...
    def __setattr__(self, name, value):
        if hasattr(type(self), name):
            raise AttributeError(f"attribute '{name}' can't be used as key")
        self[name] = value

    # NOTE: ver por qué, y si es parte de la especificación, este método
    # igula llama siempre los atributos de la superclase.
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            msg = f"'{type(self).__name__}' has not known key '{name}'"
            raise AttributeError(msg) from e # NOTE: creo que está bien que tire ambas excepciones, por posibles capturas puede ser uno u otro.

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
