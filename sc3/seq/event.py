'''
Event.sc simplification attemp. No multichannel expasion.
'''

from ..base import main as _libsc3
from ..base import builtins as bi
from ..synth import node as nod
from ..synth import _graphparam as gpp
from ..synth import synthdesc as sdc
from ..synth import server as srv
from . import scale as scl
from .rest import Rest



class _EmptyKey():
    pass


### Event Keys ###


class EventKeys():
    name = None
    __slots__ = ()

    def __call__(self, dict):
        self.__init__(dict)


class PitchKeys(EventKeys):
    name = 'pitch'

    __slots__ = ('_freq', '_midinote', '_degree', 'mtranspose', 'gtranspose',
                 'ctranspose', 'octave', 'root', 'scale', 'detune', 'harmonic',
                 '_set_key')

    _special_keys = ('freq', 'midinote', 'degree')  # special keys, other keys in _keys.

    _keys = [('mtranspose', 0), ('gtranspose', 0.0),
             ('ctranspose', 0.0), ('octave', 5.0),
             ('root', 0.0), ('scale', scl.Scale([0, 2, 4, 5, 7, 9, 11])),  # BUG: Scale tiene que ser inmutable como tuple.
             ('detune', 0.0), ('harmonic', 1.0)]

    def __init__(self, dict):
        for key in self._special_keys:
            value = dict.pop(key, _EmptyKey)
            if value is not _EmptyKey:
                setattr(self, key, value)
                self._set_key = key
                break
        if not value:
            raise ValueError('no valid pitch key given')
        for key, value in self._keys:
            value = dict.pop(key, value)
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

    _special_keys = ('sustain')  # *** TODO

    _keys = [('tempo', None), ('dur', 1.0), ('stretch', 1.0), ('legato', 0.8),
             ('lag', 0.0), ('strum', 0.0), ('strum_ends_together', False)]

    def __init__(self, dict):
        self._sustain = dict.pop('sustain', _EmptyKey)  # NOTE: simplificar redundacia preparando super().__init__ para atributos internos.
        for key, value in self._keys:
            value = dict.pop(key, value)
            setattr(self, key, value)

    @property
    def sustain(self):
        if self._sustain is _EmptyKey:
            return self.dur * self.legato * self.stretch
        else:
            return self._sustain


    @sustain.setter
    def sustain(self, value):
        self._sustain = value


class AmplitudeKeys(EventKeys):
    name = 'amplitude'

    __slots__ = ('_amp', 'db', 'velocity', 'pan', 'trig')

    _special_keys = ('amp', 'db', 'velocity')  # *** TODO

    _keys = [('db', -20.0), ('velocity', 64), ('pan', 0.0), ('trig', 0.5)]

    def __init__(self, dict):
        self._amp = dict.pop('amp', _EmptyKey)
        for key, value in self._keys:
            value = dict.pop(key, value)
            setattr(self, key, value)

    @property
    def amp(self):
        if self._amp is _EmptyKey:
            return bi.dbamp(self.db)
        else:
            return self._amp

    @amp.setter
    def amp(self, value):
        self._amp = value


class ServerKeys(EventKeys):
    name = 'server'

    __slots__ = ('server', 'latency', 'synth_lib', '_group', 'out',
                 'add_action', 'msg_params', 'instrument', 'variant',
                 'has_gate', '_send_gate', 'args', 'lag', 'timing_offset')

    _special_keys = ('group', 'send_gate')  # *** TODO

    _keys = [('server', None), ('latency', None), ('synth_lib', None),
             ('out', 0), ('add_action', 'addToHead'), ('msg_params', None),
             ('instrument', 'default'), ('variant', None), ('has_gate', True),  # // assume SynthDef has gate
             ('args', ('freq', 'amp', 'pan', 'trig')), # // for \type \set
             ('lag', 0), ('timing_offset', 0)]

    def __init__(self, dict):
        self._group = dict.pop('group', _EmptyKey)  # NOTE: simplificar redundacia preparando super().__init__ para atributos internos.
        self._send_gate = dict.pop('send_gate', _EmptyKey)  # NOTE: simplificar redundacia preparando super().__init__ para atributos internos.
        for key, value in self._keys:
            value = dict.pop(key, value)
            setattr(self, key, value)

    @property
    def group(self):
        # BUG: *** en NodeEvents.sc está definido como:
        # BUG: *** this.parent = Event.parentEvents[\groupEvent] y retorna self.
        # BUG: *** PERO SÍ SE LLAMA LA LLAVE CON e[\group] O ~group en 'note'!
        if self._group is _EmptyKey:
            return self.server.default_group.node_id
        else:
            return self._group

    @group.setter
    def group(self, value):
        self._group = value

    @property
    def send_gate(self):
        # // sendGate == false turns off releases
        if self._send_gate is _EmptyKey:
            return self.has_gate
        else:
            return self._send_gate

    @send_gate.setter
    def send_gate(self, value):
        self._send_gate = value

    # Reemplazar (nombre) get_msg_func, msg_func, SynthDesc msg_func por una
    # función que devuelva simplemente una lista de los nombres de los
    # argumentos (menos gate?). El problema también es que las llaves están
    # repartidas.
    # msg_func = self.server.msg_func

    def _get_msg_params(self, event_type):  # Was get_msg_func
        if self.msg_params is None or event_type._done:  # *** NOTE: msg_params podría ser @property y llama a este método si _msg_params is None.
            if self.synth_lib is None:
                synth_lib = sdc.SynthDescLib.default  # BUG: global_ u otro término.
            else:
                synth_lib = self.synth_lib
            desc = synth_lib.at(self.instrument)
            if desc is None:
                self.msg_params = self._default_msg_params(event_type)
            else:
                self.has_gate = desc.has_gate
                if desc.has_gate and not desc.msg_func_keep_gate:
                    control_names = desc.control_names[:]  # *** BUG: No realiza los checkeos que hace SynthDesc.make_msg_func.
                    control_names.remove('gate')
                else:
                    control_names = desc.control_names  # *** BUG: No realiza los checkeos que hace SynthDesc.make_msg_func.
                self.msg_params = []
                for arg in control_names:  # No optimal.
                    for keys_class in type(event_type).event_keys:
                        keys_obj = getattr(event_type, keys_class.name)
                        if hasattr(keys_obj, arg):
                            self.msg_params.extend(
                                [arg, getattr(keys_obj, arg)])
                            break
                return self.msg_params
        else:
            return self.msg_params

    def _default_msg_params(self, event_type):  # Was default_msg_func. # NOTE: event_type es un objeto, se confunde.
        # No tiene setter, de ser cambiable tiene que ser a nivel global.
        return ['freq', event_type.pitch.freq, 'amp', event_type.amplitude.amp,
                'pan', event_type.amplitude.pan, 'out', event_type.server.out]

    def _synthdef_name(self):
        # # // allow `nil to cancel a variant in a pattern # BUG: no entiendo por qué no alcanza solamente con nil en sclang.
        # variant = variant.dereference;
        if self.variant is not None\
        and self.synth_desc is not None\
        and self.synth_desc.has_variants():
            return f'{self.instrument}.{self.variant}'
        else:
            return self.instrument

    # *** NOTE: Ver notas en event.py y pasar las necesarias.
    # BUG: lag y offset pierden el tiempo lógico del tt que llama, en esta implementación,
    # BUG: al hacer sched de una Function u otra Routine, ver para qué sirven.
    # def _sched_bundle(self, lag, offset, server, msg, latency=None):
    #     # // "lag" is a tempo independent absolute lag time (in seconds)
    #     # // "offset" is the delta time for the clock (usually in beats)


# TODO...


class CustomKeys(EventKeys):
    name = 'custom'

    def __init__(self, dict, **kwargs):
        for key in dict.copy().keys():
            setattr(self, key, dict.pop(key))


### Event Types ###

# PartialEvent es EventKeys.
# PlayerEvent es un event keys según sclang, que define el comportamiento de la llave 'play' según EventType, y esto sería DefaultEvent
# PlayerEvent puede evaluar distintos EventTypes, EventType define play.
# PlayerEvent además es un EventKeys que depende de otros EventKeys, necesita muchas llaves.
# PlayerEvent puede pasarse a la categoría de DefaultEvent (en vez de este).
# Sobre todo porque GroupEvent y SynthEvent definen play_func (en sclang todo es play), están al mismo nivel que playerevent con respecto a esto.

# EventTypes deberían agrupar solo las llaves que necesitan para play.

# Creo que lo correcto sería el EventType que es quién necesita las llaves para play.
# NOTE: Pensar más por el lado de lenguaje declarativo.


class EventType():  # ABC
    name = None
    event_keys = ()

    def __init__(self, dict, parent=None):
        if parent is None:
            dict = dict.copy()
        else:
            dict = {**parent, **dict}
        for keys_class in type(self).event_keys:
            setattr(self, keys_class.name, keys_class(dict))
        self._done = False

    @property
    def done(self):
        return self._done

    def play(self):
        pass


class NoteType(EventType):
    name = 'note'
    event_keys = (PitchKeys, DurationKeys, AmplitudeKeys, ServerKeys,
                  CustomKeys) # TODO: , ...)

    def play(self):  # NOTE: No server parameter.
        if self.server.server is None:
            self.server.server = srv.Server.default

        self.pitch.freq = self.pitch.detuned_freq

        param_list = self.server._get_msg_params(self)  # Populates synth_desc.
        instrument_name = self.server._synthdef_name()
        id = self.server.server.next_node_id()  # NOTE: debería quedar guardado.
        add_action = nod.Node.action_number_for(self.server.add_action)
        group = gpp.node_param(self.server.group)._as_control_input() # *** NOTE: y así la llave 'group' que por defecto es una funcion que retorna node_id no tendría tanto sentido? VER PERORATA ABAJO EN GRAIN

        bndl = ['/s_new', instrument_name, id, add_action, group]
        bndl.extend(param_list)
        bndl = gpp.node_param(bndl)._as_osc_arg_list()

        # *** BUG: socket.sendto and/or threading mixin use too much cpu.
        self.server.server.send_bundle(self.server.server.latency, bndl)
        if self.server.send_gate:
            self.server.server.send_bundle(
                self.server.server.latency + self.duration.sustain,
                ['/n_set', id, 'gate', 0])

        self._done = True  # NOTE: instead of is_playing.

# TODO...


#### Events ###


class Event():
    default_parent = {}

    event_types = {
        NoteType.name: NoteType
    }

    def __init__(self, dict, parent=None):
        if parent is None:
            self.parent = type(self).default_parent
        else:
            self.parent = parent
        self.dict = dict
        self.type = dict.get('type') or self.parent.get('type') or 'note'
        self.reset()

    def play(self):
        if self._event.done:
            self.reset()
        self._event.play()

    @property
    def done(self):
        return self._event.done

    def reset(self):
        self._event = type(self).event_types[self.type](self.dict, self.parent)
