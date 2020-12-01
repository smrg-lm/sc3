'''
Event.sc attempt 3.2. No multichannel expasion.
'''

import types
import sys

from ..base import builtins as bi
from ..base import operand as opd
from ..synth import server as srv
from ..synth import synthdesc as sdc
from ..synth import node as nod
from ..synth import _graphparam as gpp
from . import scale as scl


__all__ = ['event', 'new_event', 'Rest', 'silent', 'is_rest']


### Rest ###


class Rest(opd.Operand):
    def __init__(self, value=1.0):
        super().__init__(value)

    def __bool__(self):
        # unwrapBoolean
        return self.value


def silent(dur=1.0, inevent=None):
    if inevent is None:
        inevent = event()
    else:
        inevent = inevent.copy()
    inevent['delta'] = dur * inevent.get('stretch', 1.0)
    inevent['dur'] = dur if isinstance(dur, Rest) else Rest(dur)
    return inevent


def is_rest(inevent):
    return (inevent.get('type') == 'rest' or
            any(isinstance(value, Rest) for value in inevent.values()))


### Event Keys ###


class keyfunction():
    '''Decorator class as mark for instance methods that become keys.'''

    def __init__(self, func):
        self.func = func


class _PrepareDict(dict):
    '''
    Especial dictionary to collect attributes and methods. It allows
    to repeat names but classes can't have public value-attributes.
    '''

    def __init__(self):
        super().__setitem__('default_values', dict())
        super().__setitem__('default_functions', dict())

    def __setitem__(self, key, value):
        if key.startswith('_') or isinstance(value, types.FunctionType):
            super().__setitem__(key, value)
        elif isinstance(value, keyfunction):
            self['default_functions'][key] = value.func
        else:
            self['default_values'][key] = value


class MetaEventDict(type):
    _event_types = dict()

    @classmethod
    def __prepare__(meta_cls, cls_name, args, **kwargs):
        pd = _PrepareDict()
        if 'partial_events' in kwargs:
            # Inherit non-key object attributes.
            dk = ('default_values', 'default_functions')
            for pe in kwargs['partial_events']:
                ed = vars(pe)
                keys = ed.keys() - dk
                for k in keys:
                    if k.startswith('__'):
                        pass
                    else:
                        pd[k] = ed[k]
        return pd

    def __init__(cls, name, bases, cls_dict, partial_events=None):
        default_values = dict()
        default_functions = dict()
        if name == 'EventDict':
            return
        if partial_events is not None:
            for pe in partial_events:  # reversed?
                default_values.update(pe.default_values)
                default_functions.update(pe.default_functions)
        for base in reversed(bases):
            if base is EventDict:
                break
            if isinstance(base, MetaEventDict):
                default_values.update(base.default_values)
                default_functions.update(base.default_functions)
        for key, value in cls.default_values.items():
            default_values[sys.intern(key)] = value
        for key, value in cls.default_functions.items():
            default_functions[sys.intern(key)] = value
        cls.default_values = default_values
        cls.default_functions = default_functions
        if 'type' in cls.default_values\
        and cls.default_values['type'] is not None:
            cls._event_types[cls.default_values['type']] = cls

    @property
    def types(cls):
        return tuple(cls._event_types.keys())


class EventDict(dict, metaclass=MetaEventDict):
    def __init_subclass__(cls, partial_events=None, **kwargs):
        super().__init_subclass__(**kwargs)

    def __call__(self, key, *args):
        if key in self.default_functions:
            return self.default_functions[key](self, *args)
        if not key in self:
            return self.default_values[key]
        if callable(self[key]):
            return self[key](self, *args)
        else:
            return self[key]

    def __copy__(self):
        return self.copy()

    def copy(self):
        return type(self)(self)

    def __repr__(self):
        return f'{type(self).__name__}({super().__repr__()})'


def new_event(name, values=None, functions=None,
              bases=None, partial_events=None):
    def init_defaults(ns):
        if values is not None:
            for k, v in values.items():
                ns[k] = v
        if functions is not None:
            for k, v in functions.items():
                if not isinstance(v, types.FunctionType):
                    raise ValueError(f'{v} is not FunctionType')
                ns[k] = keyfunction(v)

    if bases is None:
        bases = (EventDict,)
    if partial_events is None:
        partial_events = {'partial_events': ()}
    else:
        partial_events = {'partial_events': partial_events}
    return types.new_class(name, bases, partial_events, init_defaults)


class event(EventDict):
    _default_type = 'note'

    def __new__(cls, *args, **kwargs):
        d = {**dict(*args), **kwargs}  # Override duplicated 'type' keys.
        type = d.pop('type', None)  # Remove 'type' from actual keys.
        if type:
            try:
                return cls._event_types[type](d)
            except KeyError:
                raise ValueError(f"no event type '{type}'") from None
        else:
            return cls._event_types[cls._default_type](d)


### Partial Events ###


class PartialEvent(EventDict):
    pass


class PitchKeys(PartialEvent):
    freq = bi.midicps(60)
    detune = 0.0
    harmonic = 1.0

    midinote = 60
    ctranspose = 0.0

    # note = 0  # Desn't need a default, see comment in keyfunction.
    degree = 0
    mtranspose = 0
    gtranspose = 0.0
    octave = 5.0
    root = 0.0
    scale = scl.Scale([0, 2, 4, 5, 7, 9, 11])

    def _detuned_freq(self):
        return self('freq') * self('harmonic') + self('detune')

    @keyfunction
    def freq(self):
        if 'freq' in self:
            return self['freq']
        elif 'midinote' in self or 'note' in self:
            return self._freq_from_midinote()
        elif 'degree' in self:
            return self._freq_from_degree()
        else:
            return self.default_values['freq']

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

    @keyfunction
    def midinote(self):
        if 'midinote' in self:
            return self['midinote']
        elif 'note' in self:
            return self._midi_from_note()
        elif 'degree' in self:
            return self._midinote_from_degree()
        elif 'freq' in self:
            return self._midinote_from_freq()
        else:
            return self.default_values['midinote']

    def _midi_from_note(self):
        # See comment in keyfunction.
        ret = self['note'] + self('gtranspose') + self('root')
        ret = ret / self('scale').tuning.spo + self('octave') - 5.0
        ret = ret * (12.0 * bi.log2(self('scale').tuning.octave_ratio)) + 60
        return ret

    def _midinote_from_degree(self):
        scale = self('scale')
        ret = scale.degree_to_key(self('degree') + self('mtranspose'))
        ret = ret + self('gtranspose') + self('root')
        ret = ret / scale.tuning.spo + self('octave') - 5.0
        ret = ret * (12.0 * bi.log2(scale.tuning.octave_ratio)) + 60
        return ret

    def _midinote_from_freq(self):
        return bi.cpsmidi(self._detuned_freq())

    @keyfunction
    def note(self):
        # When set, this key doesn't call degree_to_key when converting to
        # midinote so it can be done externally, yet this is not the best
        # path for combinations and naming/meaning gets confusing.
        return self('scale').degree_to_key(self('degree') + self('mtranspose'))

    @keyfunction
    def degree(self):
        if 'degree' in self:
            return self['degree']
        elif 'freq' in self:
            return self._degree_from_freq()
        elif 'midinote' in self:
            return self._degree_from_midinote()
        else:
            return self.default_values['degree']

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
            b = scale.tuning[0] + scale.tuning.spo
        else:
            a = scale.tuning[index - 1]
            b = scale.tuning[index]
        div = b - a
        if div == 0:
            return float(index)
        else:
            return (key - a) / div + index - 1 + degree_root


class DurationKeys(PartialEvent):
    delta = None  # Used in EventStreamPlayer._play_and_delta.
    sustain = None
    dur = 1.0
    legato = 0.8
    stretch = 1.0

    # tempo = None
    # lag = 0.0

    # strum = 0.0
    # strum_ends_together = False

    @keyfunction
    def delta(self):
        # NOTE: Cast from Rest is done externally (explicit).
        if 'delta' in self:
            return self['delta']
        else:
            return self('dur') * self('stretch')

    @keyfunction
    def sustain(self):
        if 'sustain' in self:
            return self['sustain']
        else:
            return self('dur') * self('legato') * self('stretch')

    # *** Behaviour is still missing for some keys.


class AmplitudeKeys(PartialEvent):
    amp = 0.1
    db = -20
    velocity = 12  # 0.1amp == -20dB == 12vel, linear mapping (-42.076dB range for velocity)

    pan = 0.0
    trig = 0.5   # Why was?

    @keyfunction
    def amp(self):
        if 'amp' in self:
            return self['amp']
        elif 'db' in self:
            return bi.dbamp(self['db'])
        elif 'velocity' in self:
            return self._amp_from_velocity()
        else:
            return self.default_values['amp']

    def _amp_from_velocity(self):
        return self['velocity'] / 127

    @keyfunction
    def db(self):
        if 'db' in self:
            return self['db']
        elif 'amp' in self:
            return bi.ampdb(self['amp'])
        elif 'velocity' in self:
            return self._db_from_velocity()
        else:
            return self.default_values['db']

    def _db_from_velocity(self):
        return bi.ampdb(self._amp_from_velocity())

    @keyfunction
    def velocity(self):
        if 'velocity' in self:
            return self['velocity']
        elif 'amp' in self:
            return self._velocity_from_amp()
        elif 'db' in self:
            return self._velocity_from_db()
        else:
            return self.default_values['velocity']

    def _velocity_from_amp(self):
        return int(127 * self['amp'])

    def _velocity_from_db(self):
        return int(127 * bi.dbamp(self['db']))


class ServerKeys(PartialEvent):
    server = None
    latency = None
    node_id = None
    group = None
    synth_lib = None
    synth_desc = None
    out = 0
    add_action = 'addToHead'
    msg_params = []
    instrument = 'default'
    variant = None
    has_gate = True  # // assume SynthDef has gate
    send_gate = None  # // sendGate == false turns off releases
    args = ('freq', 'amp', 'pan', 'trig')  # // for 'type' 'set'
    # lag = 0
    timing_offset = 0  # Used in EventStreamPlayer._synch_with_quant

    @keyfunction
    def server(self):
        return srv.Server.default

    @keyfunction
    def group(self):
        if 'group' in self:
            return self['group']
        else:
            return self('server').default_group.node_id

    @keyfunction
    def synth_lib(self):
        return sdc.SynthDescLib.default  # BUG: Was global_.

    @keyfunction
    def send_gate(self):
        if 'send_gate' in self:
            return self['send_gate']
        else:
            return self('has_gate')

    def _get_msg_params(self):  # Was get_msg_func
        msg_params = self('msg_params')
        if not msg_params or self('is_playing'):
            synth_lib = self('synth_lib')
            desc = synth_lib.at(self('instrument'))
            if desc is None:
                self['msg_params'] = self._default_msg_params()
                return self['msg_params']
            else:
                self['synth_desc'] = desc
                self['has_gate'] = desc.has_gate
                if desc.has_gate and not desc.keep_gate:
                    control_names = desc.control_names[:]
                    control_names.remove('gate')
                else:
                    control_names = desc.control_names
                msg_params = []
                for arg in control_names:
                    if arg in self:
                        msg_params.extend([arg, self(arg)])
                self['msg_params'] = msg_params
                return msg_params
        else:
            return msg_params

    def _default_msg_params(self):  # Was default_msg_func.
        return ['freq', self('freq'), 'amp', self('amp'),
                'pan', self('pan'), 'out', self('out')]

    def _synthdef_name(self):
        if self('variant') is not None\
        and self('synth_desc') is not None\
        and self('synth_desc').has_variants():
            return f"{self('instrument')}.{self('variant')}"
        else:
            return self('instrument')

    # def _sched_bundle(self, lag, offset, server, msg, latency=None):
    #     # // "lag" is a tempo independent absolute lag time (in seconds)
    #     # // "offset" is the delta time for the clock (usually in beats)


# TODO...


### Event Types ###


class EventType(EventDict):
    # type = None
    # is_playing = False

    def play(self):
        pass

    # def __eq__(self, other):
    #     return super().__eq__(other)

    def __hash__(self):
        return id(self)


class NoteEvent(EventType, partial_events=(
        PitchKeys, AmplitudeKeys, DurationKeys, ServerKeys)):  # TODO...
    type = 'note'
    is_playing = False

    def play(self):  # NOTE: No server parameter.
        self['freq'] = self._detuned_freq()  # Before _get_msg_params.
        param_list = self._get_msg_params()  # Populates synth_desc.
        self['instrument'] = instrument = self._synthdef_name()
        self['server'] = server = self('server')

        self['node_id'] = node_id = server.next_node_id()
        add_action = nod.Node.action_number_for(self('add_action'))
        self['group'] = group = gpp.node_param(
            self('group'))._as_control_input()

        bndl = ['/s_new', instrument, node_id, add_action, group]
        bndl.extend(param_list)
        bndl = gpp.node_param(bndl)._as_osc_arg_list()

        # *** BUG: socket.sendto and/or threading mixin use too much cpu.
        server.send_bundle(server.latency, bndl)  # Missing ~latency, ~lag and ~timmingOffset.
        if self('send_gate'):
            server.send_bundle(
                server.latency + self('sustain'),
                ['/n_set', node_id, 'gate', 0])

        self['is_playing'] = True


class _MonoOnEvent(EventType, partial_events=(
        PitchKeys, AmplitudeKeys, DurationKeys, ServerKeys)):
    type = '_mono_on'
    is_playing = False

    def play(self):
        self['add_action'] = nod.Node.action_number_for(self('add_action'))
        self['group'] = gpp.node_param(self('group'))._as_control_input()
        bndl = [
            '/s_new', self['instrument'], self['node_id'],
            self['add_action'], self['group'], *self['msg_params']]
        bndl = gpp.node_param(bndl)._as_osc_arg_list()
        self['server'].send_bundle(self['server'].latency, bndl)  # Missing ~latency, ~lag and ~timmingOffset.
        self['is_playing'] = True

    def _prepare_event(self, instrument):
        self['instrument'] = instrument
        self['freq'] = self._detuned_freq()  # Before _get_msg_params.
        self['msg_params'] = self._get_msg_params()  # Populates synth_desc.
        self['has_gate'] = self('has_gate')
        self['server'] = self('server')
        self['node_id'] = self['server'].next_node_id()


class _MonoSetEvent(EventType, partial_events=(
        PitchKeys, AmplitudeKeys, DurationKeys, ServerKeys)):
    type = '_mono_set'
    is_playing = True
    mono_params = None

    def play(self):
        self['freq'] = self._detuned_freq()
        self['server'] = self('server')
        bndl = ['/n_set', self['node_id'], *self._update_msg_params()]
        bndl = gpp.node_param(bndl)._as_osc_arg_list()
        self['server'].send_bundle(self['server'].latency, bndl)

    def _update_msg_params(self):
        msg_params = []
        for arg in self['mono_params']:
            msg_params.extend([arg, self(arg)])
        self['msg_params'] = msg_params
        return msg_params


class _MonoOffEvent(EventType, partial_events=(ServerKeys,)):
    type = '_mono_off'
    is_playing = True
    has_gate = False
    gate = 0
    delay = 0

    def play(self):
        if self('has_gate'):
            bndl = ['/n_set', self['node_id'], 'gate', self('gate')]
        else:
            bndl = ['/n_free', self['node_id']]
        bndl = gpp.node_param(bndl)._as_osc_arg_list()
        server = self('server')
        server.send_bundle(server.latency + self('delay'), bndl)
        self['is_playing'] = False
