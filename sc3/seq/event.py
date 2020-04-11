'''
Event.sc attempt no. 3. No multichannel expasion.
'''

from ..base import builtins as bi
from ..base import operand as opd
from ..synth import server as srv
from ..synth import synthdesc as sdc
from ..synth import node as nod
from ..synth import _graphparam as gpp
from . import scale as scl


### Rest ###


class Rest(opd.Operand):
    def __init__(self, value=1.0):
        super().__init__(value)

    def __bool__(self):
        # unwrapBoolean
        return self.value

    # In sclang: \, \r, \rest, Rest and Rest() are rest values for any
    # key stream, also (type: \rest) and (isRest: true) at event level.
    # SEE: "event support" with asControlInput, playAndDelta & isRest.


def silent(dur=1.0, inevent=None):
    if inevent is None:
        inevent = dict()  # *** BUG: Event.new, parent: defaultParentEvent
    else:
        inevent = inevent.copy()
    inevent['delta'] = dur * inevent.get('stretch', 1.0)
    inevent['dur'] = dur if isinstance(dur, Rest) else Rest(dur)
    return inevent


def is_rest(inevent):
    return (inevent.get('type') == 'rest' or
            any(isinstance(value, Rest) for value in inevent.values()))


### Event Keys ###


class MetaEventKeys(type):
    def __init__(cls, name, bases, _):
        for base in reversed(bases):
            # To avoid defining _default_keys = {} but redundantly
            # copies and then overrides the first base _default_keys.
            # cls._default_keys = cls._default_keys.copy()
            if isinstance(base, MetaEventKeys):
                cls._default_keys.update(base._default_keys)


class EventKeys(dict, metaclass=MetaEventKeys):
    _default_keys = {}  # Definition is mandatory for each subclass.

    def __call__(self, key):
        try:
            return getattr(self, '_' + key)()
        except AttributeError:
            pass
        try:
            # Inline. Not using type(self) because takes even more time.
            return self.get(key, self._default_keys[key])
        except KeyError:
            pass
        raise ValueError(f"not evaluable key '{key}'")


class PitchKeys(EventKeys):
    _default_keys = {
        'freq': bi.midicps(60),
        'detune': 0.0,
        'harmonic': 1.0,

        'midinote': 60,
        'ctranspose': 0.0,

        'degree': 0,
        'mtranspose': 0,
        'gtranspose': 0.0,
        'octave': 5.0,
        'root': 0.0,
        'scale': scl.Scale([0, 2, 4, 5, 7, 9, 11])
    }

    def _detuned_freq(self):
        return self('freq') * self('harmonic') + self('detune')

    def _freq(self):
        if 'freq' in self:
            return self['freq']
        elif 'midinote' in self:
            return self._freq_from_midinote()
        elif 'degree' in self:
            return self._freq_from_degree()
        else:
            return self._default_keys['freq']

    def _freq_from_midinote(self):
        return bi.midicps(self._transposed_midinote())

    def _freq_from_degree(self):
        # No ctranspose. For every main key with it own modifiers (harmonic
        # and detune for freq) the other two can be calculate (without their
        # modifiers). Only one main key should be used at a time and 'freq'
        # overrides 'midinote' that overrides 'degree' for events.
        return bi.midicps(self._midinote_from_degree())

    def _transposed_midinote(self):
        return self('midinote') + self('ctranspose')

    def _midinote(self):
        if 'midinote' in self:
            return self['midinote']
        elif 'degree' in self:
            return self._midinote_from_degree()
        elif 'freq' in self:
            return self._midinote_from_freq()
        else:
            return self._default_keys['midinote']

    def _midinote_from_freq(self):
        return bi.cpsmidi(self._detuned_freq())

    def _midinote_from_degree(self):
        ret = self._transposed_degree()
        ret = ret * (12.0 * bi.log2(self('scale').octave_ratio)) + 60
        return ret

    def _transposed_degree(self):
        scale = self('scale')
        ret = scale.degree_to_key(self('degree') + self('mtranspose'))
        ret = ret + self('gtranspose') + self('root')
        ret = ret / scale.spo() + self('octave') - 5.0
        return ret

    def _degree(self):
        if 'degree' in self:
            return self['degree']
        elif 'freq' in self:
            return self._degree_from_freq()
        elif 'midinote' in self:
            return self._degree_from_midinote()
        else:
            return self._default_keys['degree']

    def _degree_from_freq(self):
        return self._midinote_to_degree(bi.cpsmidi(self._detuned_freq()))

    def _degree_from_midinote(self):
        return self._midinote_to_degree(self._transposed_midinote())

    def _midinote_to_degree(self, midinote):
        # From SequenceableCollection.performDegreeToKey
        scale = self('scale')
        degree_root = (midinote // 12 - 5) * len(scale.tuning)
        key = midinote % 12
        # From SequenceableCollection.indexInBetween modified.
        index = None
        for i, value in enumerate(scale.tuning):
            if value > key:
                index = i
                break
        if index == 0:
            return 0.0
        if index is None:
            index = i + 1
            a = scale.tuning[-1]
            b = scale.tuning[0] + scale.spo()
        else:
            a = scale.tuning[index - 1]
            b = scale.tuning[index]
        div = b - a
        if div == 0:
            return float(index)
        else:
            return (key - a) / div + index - 1 + degree_root


class DurationKeys(EventKeys):
    _default_keys = {
        'delta': None,
        'sustain': None,
        'dur': 1.0,
        'legato': 0.8,
        'stretch': 1.0,

        # 'tempo': None,
        # 'lag': 0.0,

        # 'strum': 0.0,
        # 'strum_ends_together': False
    }

    def _delta(self):
        # NOTE: Cast from Rest is done externally (explicit).
        if 'delta' in self:
            return self['delta']
        else:
            return self('dur') * self('stretch')

    def _sustain(self):
        if 'sustain' in self:
            return self['sustain']
        else:
            return self('dur') * self('legato') * self('stretch')

    # *** Behaviour is still missing for some keys.


class AmplitudeKeys(EventKeys):
    _default_keys = {
        'amp': 0.1,
        'db': -20,
        'velocity': 12,  # 0.1amp == -20dB == 12vel, linear mapping (-42.076dB range for velocity)

        'pan': 0.0,
        'trig': 0.5,  # Why was?
    }

    def _amp(self):
        if 'amp' in self:
            return self['amp']
        elif 'db' in self:
            return bi.dbamp(self['db'])
        elif 'velocity' in self:
            return self._amp_from_velocity()
        else:
            return self._default_keys['amp']

    def _amp_from_velocity(self):
        return self['velocity'] / 127

    def _db(self):
        if 'db' in self:
            return self['db']
        elif 'amp' in self:
            return bi.ampdb(self['amp'])
        elif 'velocity' in self:
            return self._db_from_velocity()
        else:
            return self._default_keys['db']

    def _db_from_velocity(self):
        return bi.ampdb(self._amp_from_velocity())

    def _velocity(self):
        if 'velocity' in self:
            return self['velocity']
        elif 'amp' in self:
            return self._velocity_from_amp()
        elif 'db' in self:
            return self._velocity_from_db()
        else:
            return self._default_keys['velocity']

    def _velocity_from_amp(self):
        return int(127 * self['amp'])

    def _velocity_from_db(self):
        return int(127 * bi.dbamp(self['db']))


class ServerKeys(EventKeys):
    _default_keys = {
        'server': srv.Server.default,
        'latency': None,
        'node_id': None,
        'group': None,
        'synth_lib': sdc.SynthDescLib.default, # None,  # BUG: Was global_.
        'synth_desc': None,
        'out': 0,
        'add_action': 'addToHead',
        'msg_params': None,
        'instrument': 'default',
        'variant': None,
        'has_gate': True,  # // assume SynthDef has gate
        'send_gate': None,  # // sendGate == false turns off releases
        'args': ('freq', 'amp', 'pan', 'trig'), # // for 'type' 'set'
        'lag': 0,
        'timing_offset': 0
    }

    def _group(self):
        # BUG: *** en NodeEvents.sc está definido como:
        # BUG: *** this.parent = Event.parentEvents[\groupEvent] y retorna self.
        # BUG: *** PERO SÍ SE LLAMA LA LLAVE CON e[\group] O ~group en 'note'!
        if 'group' in self:
            return self['group']
        else:
            return self('server').default_group.node_id

    def _send_gate(self):
        if 'send_gate' in self:
            return self['send_gate']
        else:
            return self('has_gate')

    # Reemplazar (nombre) get_msg_func, msg_func, SynthDesc msg_func por una
    # función que devuelva simplemente una lista de los nombres de los
    # argumentos (menos gate?). El problema también es que las llaves están
    # repartidas.
    # msg_func = self.server.msg_func

    def _get_msg_params(self):  # Was get_msg_func
        msg_params = self('msg_params')
        if msg_params is None or self('is_playing'):
            synth_lib = self('synth_lib')
            desc = synth_lib.at(self('instrument'))
            if desc is None:
                self['msg_params'] = self._default_msg_params()
                return self['msg_params']
            else:
                self['synth_desc'] = desc
                self['has_gate'] = desc.has_gate
                if desc.has_gate and not desc.msg_func_keep_gate:
                    control_names = desc.control_names[:]  # *** BUG: No realiza los checkeos que hace SynthDesc.make_msg_func.
                    control_names.remove('gate')
                else:
                    control_names = desc.control_names  # *** BUG: No realiza los checkeos que hace SynthDesc.make_msg_func.
                msg_params = []
                for arg in control_names:
                    if arg in self or arg in self._default_keys:
                        msg_params.extend([arg, self(arg)])
                self['msg_params'] = msg_params
                return msg_params
        else:
            return msg_params

    def _default_msg_params(self):  # Was default_msg_func.
        return ['freq', self('freq'), 'amp', self('amp'),
                'pan', self('pan'), 'out', self('out')]

    def _synthdef_name(self):
        # # // allow `nil to cancel a variant in a pattern # BUG: no entiendo por qué no alcanza solamente con nil en sclang.
        # variant = variant.dereference;
        if self('variant') is not None\
        and self('synth_desc') is not None\
        and self('synth_desc').has_variants():
            return f"{self('instrument')}.{self('variant')}"
        else:
            return self('instrument')

    # *** NOTE: Ver notas en event.py y pasar las necesarias.
    # BUG: lag y offset pierden el tiempo lógico del tt que llama, en esta implementación,
    # BUG: al hacer sched de una Function u otra Routine, ver para qué sirven.
    # def _sched_bundle(self, lag, offset, server, msg, latency=None):
    #     # // "lag" is a tempo independent absolute lag time (in seconds)
    #     # // "offset" is the delta time for the clock (usually in beats)


# TODO...


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


class NoteEvent(PitchKeys, AmplitudeKeys, DurationKeys, ServerKeys):  # TODO...
    _default_keys = {
        'is_playing': False
    }

    def play(self):  # NOTE: No server parameter.
        self['freq'] = self._detuned_freq()  # Before _get_msg_params.
        param_list = self._get_msg_params()  # Populates synth_desc.
        self['instrument'] = instrument_name = self._synthdef_name()
        self['server'] = server = self('server')

        self['node_id'] = id = server.next_node_id()
        add_action = nod.Node.action_number_for(self('add_action'))
        self['group'] = group = gpp.node_param(
            self._group())._as_control_input() # *** NOTE: y así la llave 'group' que por defecto es una funcion que retorna node_id no tendría tanto sentido? VER PERORATA ABAJO EN GRAIN

        bndl = ['/s_new', instrument_name, id, add_action, group]
        bndl.extend(param_list)
        bndl = gpp.node_param(bndl)._as_osc_arg_list()

        # *** BUG: socket.sendto and/or threading mixin use too much cpu.
        server.send_bundle(server.latency, bndl)  # *** NO USA LA LLAVE LATENCY, NO SÉ PARA QUÉ ESTARÁ.
        if self._send_gate():
            server.send_bundle(
                server.latency + self._sustain(), ['/n_set', id, 'gate', 0])

        self['is_playing'] = True
