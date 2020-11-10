"""BufIO.sc"""

from . import infougens as ifu
from .. import ugen as ugn
from .. import _graphparam as gpp
from ...base import main as _libsc3
from ...base import utils as utl


class PlayBuf(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, num_channels, bufnum=0, rate=1.0, trigger=1.0,
           start_pos=0.0, loop=0.0, done_action=0):
        return cls._multi_new(
            'audio', num_channels, bufnum, rate,
            trigger, start_pos, float(loop), done_action)

    @classmethod
    def kr(cls, num_channels, bufnum=0, rate=1.0, trigger=1.0,
           start_pos=0.0, loop=0.0, done_action=0):
        return cls._multi_new(
            'control', num_channels, bufnum, rate,
            trigger, start_pos, float(loop), done_action)

    def _init_ugen(self, num_channels, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(num_channels, self.rate)

    def _arg_names_inputs_offset(self):  # override
        return 1  # One less than sclang.


class TGrains(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, num_channels, trigger=0, bufnum=0, rate=1.0, center_pos=0,
           dur=0.1, pan=0, amp=0.1, interp=4):
        return cls._multi_new(
            'audio', num_channels, trigger, bufnum,
            rate, center_pos, dur, pan, amp, interp)

    def _init_ugen(self, num_channels, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(num_channels, self.rate)

    def _arg_names_inputs_offset(self):  # override
        return 1  # One less than sclang.


# SimpleLoopBuf, commented ugen.


class BufRd(ugn.MultiOutUGen):
    @classmethod
    def ar(cls, num_channels, bufnum=0, phase=0.0, loop=0.0, interpolation=2):
        return cls._multi_new(
            'audio', num_channels, bufnum, phase, float(loop), interpolation)

    @classmethod
    def kr(cls, num_channels, bufnum=0, phase=0.0, loop=0.0, interpolation=2):
        return cls._multi_new(
            'control', num_channels, bufnum, phase, float(loop), interpolation)

    def _init_ugen(self, num_channels, *inputs):  # override
        self._inputs = inputs
        return self._init_outputs(num_channels, self.rate)

    def _arg_names_inputs_offset(self):  # override
        return 1  # One less than sclang.

    def _check_inputs(self):  # override
        if self.rate == 'audio'\
        and gpp.ugen_param(self.inputs[1])._as_ugen_rate() != 'audio':
            return (f'phase input is not audio rate: {self.inputs[1]}'
                    f'{gpp.ugen_param(self.inputs[1])._as_ugen_rate()}')
        return self._check_valid_inputs()


class BufWr(ugn.UGen):
    @classmethod
    def ar(cls, input_list, bufnum=0, phase=0.0, loop=0.0):
        return cls._multi_new(
            'audio', bufnum, phase, float(loop), *utl.as_list(input_list))

    @classmethod
    def kr(cls, input_list, bufnum=0, phase=0.0, loop=0.0):
        return cls._multi_new(
            'control', bufnum, phase, float(loop), *utl.as_list(input_list))

    def _check_inputs(self):  # override
        if self.rate == 'audio':
            if gpp.ugen_param(self.inputs[1])._as_ugen_rate() != 'audio':
                return (f'phase input is not audio rate: {self.inputs[1]} '
                        f'{gpp.ugen_param(self.inputs[1])._as_ugen_rate()}')
            elif any(gpp.ugen_param(x)._as_ugen_rate() != 'audio'\
                     for x in self.inputs[3:]):
                return (f'input_list input is not audio rate: {self.inputs[3:]} '
                        f'{[gpp.ugen_param(x)._as_ugen_rate() for x in self.inputs[3:]]}')
        return self._check_valid_inputs()


class RecordBuf(ugn.UGen):
    @classmethod
    def ar(cls, input_list, bufnum=0, offset=0.0, rec_level=1.0, pre_level=0.0,
           run=1.0, loop=0.0, trigger=1.0, done_action=0):
        return cls._multi_new(
            'audio', bufnum, offset, rec_level, pre_level, run,
            float(loop), trigger, done_action, *utl.as_list(input_list))

    @classmethod
    def kr(cls, input_list, bufnum=0, offset=0.0, rec_level=1.0, pre_level=0.0,
           run=1.0, loop=0.0, trigger=1.0, done_action=0):
        return cls._multi_new(
            'control', bufnum, offset, rec_level, pre_level, run,
            float(loop), trigger, done_action, *utl.as_list(input_list))


class ScopeOut(ugn.UGen):
    @classmethod
    def ar(cls, input_list, bufnum=0):
        cls._multi_new('audio', bufnum, *utl.as_list(input_list))
        # return 0.0  # ScopeOut has no output.

    @classmethod
    def kr(cls, input_list, bufnum=0):
        cls._multi_new('control', bufnum, *utl.as_list(input_list))
        # return 0.0  # ScopeOut has no output.


class ScopeOut2(ugn.UGen):
    @classmethod
    def ar(cls, input_list, scope_num=0, max_frames=4096, scope_frames=None):
        if scope_frames is None:
            scope_frames = max_frames
        cls._multi_new(
            'audio', scope_num, max_frames,
            scope_frames, *utl.as_list(input_list))
        # return 0.0  # ScopeOut2 has no output.

    @classmethod
    def kr(cls, input_list, scope_num=0, max_frames=4096, scope_frames=None):
        if scope_frames is None:
            scope_frames = max_frames
        cls._multi_new(
            'control', scope_num, max_frames,
            scope_frames, *utl.as_list(input_list))
        # return 0.0  # ScopeOut2 has no output.


class Tap(ugn.UGen):
    @classmethod
    def ar(cls, bufnum=0, num_channels=1, delay_time=0.2):
        # // This depends on the session sample rate, not buffer.
        n = delay_time * ifu.SampleRate.ir().neg()
        return PlayBuf.ar(num_channels, bufnum, 1, 0, n, 1)


class LocalBuf(ugn.WidthFirstUGen):
    @classmethod
    def new(cls, num_frames=1, num_channels=1):
        return cls._multi_new('scalar', num_channels, num_frames)

    @classmethod
    def _new1(cls, rate, *args):  # override
        max_local_bufs = _libsc3.main._current_synthdef._max_local_bufs
        if max_local_bufs is None:
            max_local_bufs = MaxLocalBufs.new()
            _libsc3.main._current_synthdef._max_local_bufs = max_local_bufs
        max_local_bufs.increment()
        obj = cls._create_ugen_object(rate)
        obj._add_to_synth()
        return obj._init_ugen(*args, max_local_bufs)

    @classmethod
    def new_from(cls, lst):
        shape = utl.shape(lst)
        size = len(shape)
        if size == 0:
            raise TypeError(f'{cls.__name__} wrong type: {type(lst).__name__}')
        elif size == 1:
            shape = [1, len(lst)]
        elif size == 2:
            shape = list(shape)
        else:  # size > 2:
            raise ValueError(f'{cls.__name__} list has not the right shape')
        shape.reverse()
        buf = cls.new(*shape)
        buf.set(utl.flat(utl.flop(lst)))
        return buf

    @property
    def num_frames(self):
        return self.inputs[1]

    @property
    def num_channels(self):
        return self.inputs[0]

    def set(self, values, offset=0):
        SetBuf.new(self, utl.as_list(values), offset)

    def clear(self):
        ClearBuf.new(self)


class MaxLocalBufs(ugn.UGen):
    _default_rate = None

    @classmethod
    def new(cls):
        return cls._multi_new('scalar', 0)

    def increment(self):
        inputs = list(self._inputs)
        inputs[0] += 1
        self._inputs = tuple(inputs)


class SetBuf(ugn.WidthFirstUGen):
    @classmethod
    def new(cls, buf, values, offset=0):
        return cls._multi_new('scalar', buf, offset, len(values), *values)


class ClearBuf(ugn.WidthFirstUGen):
    @classmethod
    def new(cls, buf):
        return cls._multi_new('scalar', buf)
