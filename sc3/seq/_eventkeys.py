'''
Intención de generalización como objetos:

- La clase Event se encarga de definir un diccionario como parent y/o proto.
- Se mezcla el diccionario de creación del evento con parent y/o proto.
- Las clases que representan propiedades (EventKeys) quedan inalteradas.

No hay expansión multicanal, al menos por ahora.
'''

from ..base import builtins as bi
from ..synth import node as nod
from ..synth import _graphparam as gpp
from . import scale as scl


### Event Keys ###


class EventKeys():  # Hacer ABC o constructor por defecto, se puede necesitar para CustomKeys.
    name = None
    __slots__ = ()

    def __call__(self, dict=None, **kwargs):
        # *** NOTE: hace que el objeto sea reutilizable, se podría aplicar a la funcion/módulo graphparam?
        self.__init__(dict, **kwargs)  # *** NOTE: el último sobreescribe, sirve para parent en Event (que iría primero al mezclar)


class PitchKeys(EventKeys):
    name = 'pitch'

    __slots__ = ('_freq', '_midinote', '_degree', 'mtranspose', 'gtranspose',
                 'ctranspose', 'octave', 'root', 'scale', 'detune', 'harmonic',
                 '_set_key')

    _pitch_keys = ('freq', 'midinote', 'degree')  # special keys, other keys y all keys?

    _keys = [('mtranspose', 0), ('gtranspose', 0.0),
             ('ctranspose', 0.0), ('octave', 5.0),
             ('root', 0.0), ('scale', scl.Scale([0, 2, 4, 5, 7, 9, 11])),  # BUG: Scale tiene que ser inmutable como tuple.
             ('detune', 0.0), ('harmonic', 1.0)]

    def __init__(self, dict=None, **kwargs):
        dict = dict or {}
        dict = {**dict, **kwargs}
        for key in self._pitch_keys:
            value = dict.get(key)
            if value:
                setattr(self, key, value)
                self._set_key = key
                break
        if not value:
            raise ValueError('no valid pitch key given')
        for key, value in self._keys:
            value = dict.get(key, value)
            setattr(self, key, value)

    @property
    def freq(self):
        if self._set_key == 'freq':
            # Cuando se setea una llave ya no llama a la cadena de
            # transformaciones. Pero 'harmonic' podría funcionar (no lo hace
            # en sclang). Aunque si lo hace el valor de set != get.
            return self._freq  # * self.harmonic
        elif self._set_key == 'midinote':
            midinote = self._midinote  # midinote -> freq
        else:  # self._set_key == 'degree'
            midinote = self.midinote  # degree -> note -> midinote -> freq
        return bi.midicps(midinote + self.ctranspose) * self.harmonic

    @freq.setter
    def freq(self, value):
        self._freq = value
        self._set_key = 'freq'

    @property
    def midinote(self):
        if self._set_key == 'midinote':
            return self._midinote
        elif self._set_key == 'degree':
            ret = self.scale.degree_to_key(self._degree + self.mtranspose)  # degree -> note -> midinote
            ret = ret + self.gtranspose + self.root
            ret = ret / self.scale.spo() + self.octave - 5.0
            ret = ret * (12.0 * math.log2(self.scale.octave_ratio)) + 60
            return ret
        else:  # self._set_key == 'freq'
            return bi.cpsmidi(self._freq)  # no existe en sclang

    @midinote.setter
    def midinote(self, value):
        self._midinote = value
        self._set_key = 'midinote'

    @property
    def degree(self):
        if self._set_key == 'degree':
            return self._degree
        else:  # self._set_key == 'freq' or self._set_key == 'midinote'
            return None  # no existe en sclang
        # No se puede hacer el camino inverso si se piensa que:
        # El valor de freq es sin transformación ni detune.
        # El valor de midinote es sin ctranspose ni harmonic.
        # El valor de degree es sin escala ni transposiciones ni alteraciones.
        # Eso se define por la cadena degree -> note -> midinote -> freq -> detuned_freq

    @degree.setter
    def degree(self, value):
        self._degree = value
        self._set_key = 'degree'

    @property
    def detuned_freq(self):
        return self.freq + self.detune


class DurationKeys(EventKeys):
    name = 'duration'

    __slots__ = ('_sustain', 'tempo', 'dur', 'stretch', 'legato',
                 'lag', 'strum', 'strum_ends_together')

    _keys = [('tempo', None), ('dur', 1.0), ('stretch', 1.0), ('legato', 0.8),
             ('lag', 0.0), ('strum', 0.0), ('strum_ends_together', False)]

    def __init__(self, dict=None, **kwargs):
        dict = dict or {}
        dict = {**dict, **kwargs}
        self._sustain = dict.get('sustain')
        for key, value in self._keys:
            value = dict.get(key, value)
            setattr(self, key, value)

    @property
    def sustain(self):
        if self._sustain:
            return self._sustain
        else:
            return self.dur * self.legato * self.stretch

    @sustain.setter
    def sustain(self, value):
        self._sustain = value


class AmplitudeKeys(EventKeys):
    name = 'amplitude'

    ...


class ServerKeys(EventKeys):
    name = 'server'

    ...


    # Reemplazar get_msg_func, msg_func, SynthDesc msg_func por una
    # función que devuelva simplemente una lista de los nombres de los
    # argumentos (menos gate?). El problema también es que las llaves están
    # repartidas.
    # msg_func = self.server.msg_func
    # NOTE: De ser así tiene que haber una clase CustomKeys para EventType.event_keys.
    # NOTE: no puede ser una propiedad y rompo la regla que quería.
    def msg_parameters(self, event_type):  # event_type es un objeto, se confunde.
        param_list = []
        for arg in self.synthdef_args:  # No existe, son todos menos gate.
            for keys_class in type(event_type).event_keys:
                keys_obj = getattr(event_type, keys_class.name)
                if hasattr(keys_obj, arg):
                    param_list.extend([arg, getattr(keys_obj, arg)])
                    break
        return param_list


# TODO...


### Event Types ###

# PartialEvent es EventKeys.
# PlayerEvent es un event keys según sclang, que define el comportamiento de la llave 'play' según EventType, y esto sería DefaultEvent
# PlayerEvent puede evaluar distintos EventTypes, EventType define play.
# PlayerEvent además es un EventKeys que depende de otros EventKeys, necesita muchas llaves.
# PlayerEvent puede pasarse a la categoría de DefaultEvent (en vez de este).
# Sobre todo porque GroupEvent y SynthEvent definen play_func (en sclang todo es play), están al mismo nivel que playerevent con respecto a esto.

# EventTypes deberían agrupar solo las llaves que necesitan para play.

# El problema es que el diccionario que se le pasa a Event es filtrado
# por cada una de las EventKeys, quién hace el filtrado y en qué formato?
# Creo que lo correcto sería el EventType que es quién necesita las llaves para play.
# NOTE: Pensar más por el lado de lenguaje declarativo.


class EventType():  # ABC
    name = None
    event_keys = ()

    def __init__(self, dict, parent):  # Aunque tal vez parent debería ser un conjunto de event_keys? complica, que sea una especificación declarativa de los valores de los tipos por defecto. Y se pueden sacar los valres por defecto a _keys de arriba.
        dict = {**parent, **dict}
        for keys_class in type(self).event_keys:
            setattr(self, keys_class.name, keys_class(dict))  # Crea una instancia de cada una por evento, mal pero se necesita, simplifica mucho.

    def play(self):
        pass


class NoteType(EventType):
    name = 'note'
    event_keys = (PitchKeys, DurationKeys)  # AmplitudeKeys, ...)

    def play(self, server):
        # freq = self.pitch.detuned_freq

        # Reemplazar get_msg_func, msg_func, SynthDesc msg_func por una
        # función que devuelva simplemente una lista de los nombres de los
        # argumentos (menos gate?). El problema también es que las llaves están
        # repartidas.
        # msg_func = self.server.msg_func
        # NOTE: De ser así tiene que haber una clase CustomKeys...
        param_list = self.server.msg_parameters(self)

        # // sendGate == false turns off releases
        send_gate = self.server.send_gate or self.server.has_gate  # NOTE: puede ser la lógica de la propiedad send_gate acá.
        # Se podría hacer, mejor, que la lógica esté contenida en las llaves
        # salvo las que compartan parámetros entre llaves. getMsgFunc es el
        # caso principal, es la función devuelta por synthdesc a la que se
        # le pasa event como parámetro para que obtenga los valores de las llaves.

        instrument_name = self.server.synthdef_name
        id = server.next_node_id()  # NOTE: debería quedar guardado.
        add_action = nod.Node.action_number_for(self.server.add_action)
        group = gpp.node_param(  event.value('group')  )._as_control_input() # *** NOTE: y así la llave 'group' que por defecto es una funcion que retorna node_id no tendría tanto sentido? VER PERORATA ABAJO EN GRAIN

        bndl = ['/s_new', instrument_name, id, add_action, group]
        bndl.extend(param_list)
        bndl = gpp.node_param(bndl)._as_osc_arg_list()

        self.server.sched_bundle(
            self.server.lag, self.server.timing_offset,  # *** NOTE: lag no está definida en ningún partialEvent?
            server, bndl, self.server.latency) # NOTE: puede ser cualquier cantidad de mensajes/notas, esto es algo que no está claro en la implementación de sclang, aquí offset es escalar, en strummed es una lista.

        self.is_playing = True  # NOTE: no queda entre las llaves sino en eventype, creo que no está definida en partialEvents.

        if self.server.send_gate:  # NOTE: todavía no tiene definida la lógica de la asignación de arriba.
            self.server.sched_bundle(
                self.server.lag,  # *** NOTE: lag no está definida en ningún partialEvent?
                self.duration.sustan + self.server.timing_offset,
                server, ['/n_set', id, 'gate', 0], self.server.latency)

# TODO...


#### Events ###


class Event():
    ...


# LOS DEFAULT EVENTS SE PODRÍAN SACAR EN FAVOR DE EVENTTYPES (QUE TIENEN QUE
# TENER PLAY Y YA DEFINE LAS LLAVES QUE NECESITA), SIMPLIFICA.
class PlayerEvent(Event):  # es DefaultEvent/ParentEvent, ver arriba.
    ...
