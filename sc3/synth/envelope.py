"""Env.sc"""

import copy
import operator
import math

from ..base import main as _libsc3
from ..base import utils as utl
from ..base import builtins as bi
from . import _graphparam as gpp
from .ugens import trig as trg
from .ugens import oscillators as ocl


__all__ = ['Env']


class Env(gpp.UGenParameter, gpp.NodeParameter):
    '''Specification for a segmented envelope.

    Envelope specifications are used for server-side parameters'
    generation for ``EnvGen`` or ``IEnvGen``. They can be used
    client-side through the ``Pseq`` mostly equivalent time pattern.

    Envelopes can be of fixed duration or sustained, if a release node
    is defined. There is a number specialized constructor methods with
    the most common envelopes.

    This class supports multichannel expansion and ugens as inputs for
    the `levels` parameters (as supported by ``EnvGen``).

    Parameters
    ----------
    levels : list
        Amplitude levels of the envelope. The first value is the
        initial level of the envelope. When the envelope is used with
        an ``EnvGen``, levels can be any ugen (new level values are
        updated only when the envelope has reached that point). When
        the array of levels contains itself an array, the envelope
        returns a multichannel output (see multichannel expansion).
    times : list | float | int
        Transition times to the next level values. There should be one
        fewer duration than there are levels, but if shorter, the array
        is extended by wrapping around the given values. If a scalar
        value is supplied all durations will be equal.
    curves : list | str | float | int
        Determine the shape of the transition segments. Possible values
        are: 'linear' or 'lin', linear segments (default), 'step', flat
        segments (immediately jumps to final value), 'hold', flat
        segments (holds initial value, jump to final value at the end
        of the segment), 'exponential' or 'exp', natural exponential
        growth and decay (in this case, the levels must all be nonzero
        and have the same sign), 'sine' or 'sin', sinusoidal *S* shaped
        segments, 'welch' or 'wel', sinusoidal segments shaped like the
        sides of a Welch window, 'squared' or 'sqr', squared segment,
        'cubed' or 'cub', cubed segment, a float value, that determines
        the curvature value for all segments (0 means linear, positive
        and negative numbers curve the segment up and down) or a list
        of the above values determining the curvature for each segment.
    release_node : int
        If set, the envelope will sustain at the release node level
        until released.
    loop_node : int
        Define a node as the time point at which a loop is created
        between the next node and the release node levels. The level of
        the loop node is ignored, only the transition time to the next
        node is used in the loop as the time from the release node
        level to the next node level.
    offset : float | int
        An offset to all time values (only applies in ``IEnvGen``).

    Notes
    -----
    Internally, an envelope specification consist of an initial level
    value followed by time segments specified as target level value,
    duration to reach the target level, the shape of the segment and
    a cuve value (used only if the shape type if 5). These time
    segments are called evelope nodes.

    Constructors of this class group these parameters as separated
    lists of `levels`, `times` and `curves`. This representation is
    consistent with event patterns rather than server command.

    For example, a fixed time envelope is defined as follows.::

        # Fixed time triangular envelope of duration 2.
        levels = [0, 1, 0]  # An initial level, followed by 2 target levels.
        times = [1, 1]  # The duration to the target levels.
        curves = 'lin'  # The curve of the segments to reach next levels.
        env = Env(levels, times, curves)

    Fixed duration envelopes are triggered from the ``EnvGen`` `gate`
    parameter. The initial value of the envelope only acts as the start
    value and is never repeated. Thus, at the moment envelopes are
    re-triggered the first node becomes the target node and the
    transition starts from whatever the current level value of the
    envelope is at that moment.

    Sustained envelopes define a release node. The ``EnvGen`` `gate`
    parameter acts as a normal gate in this case. While the gate is
    open and the envelope reach the release node, it holds its level
    value until the gate is closed and then starts the transition to
    the next node through the end of the envelope.::

        # Sustained trapezoidal envelope
        levels = [0, 1, 0]  # An initial level, followed by 2 target levels.
        times = [0.1, 0.1]  # The duration to the target levels.
        curves = 'lin'  # The curve of the segments to reach next levels.
        release_node = 1  # Hold node at level 1 before the last target.
        env = Env(levels, times, curves, release_node)

    Sustained envelopes define can define a loop between nodes for the
    sustain part by defining both the release and loop nodes.::

        # Sustained ADSR envelope with loop node.
        levels = [0, 1, 0.25, 0.75, 0.5, 0]
        times = [0.02, 0.18, 0.2, 0.8, 0.02]
        release_node = 4
        loop_node = 2
        env = Env(levels, times, curves, release_node)

    Something that is sometimes confusing is that both the release node
    and the loop node are the nodes **prior** to the actual destination
    nodes (targets) for the loop and release phases of the envelope.
    This is just because the transition duration belongs to the target
    node and the loop/release node whould be the time point before that
    transition. In the example above, the release node (four) starts the
    loop between the node **after** the loop node and itself oscilating
    linearly between levels 0.5 and 0.75 at 1 Hertz, taking 0.2 seconds
    to reach the target level 0.75 and 0.8 to reach target level 0.5.
    As soon as the gate is closed by the ``EnvGen`` ugen, the envelope
    starts the transition from whatever the current value of the
    envelope is, in this case it will be between 0.5 and 0.75, taking
    0.02 seconds to reach level 0. Sigh.

    .. note:

        In some situations we deal with control points or breakpoints.
        If these control points have associated x positions they must
        be converted to time differences between points to be used as
        nodes in a ``Env`` object. The methods ``xyc`` and ``pairs``
        can be used to specify an envelope in terms of points.

    '''

    _SHAPE_NAMES = {
        'step': 0,
        'lin': 1,
        'linear': 1,
        'exp': 2,
        'exponential': 2,
        'sin': 3,
        'sine': 3,
        'wel': 4,
        'welch': 4,
        'sqrt': 6,
        'squared': 6,
        'cub': 7,
        'cubed': 7,
        'hold': 8
    }

    def __init__(self, levels=None, times=None, curves='lin',
                 release_node=None, loop_node=None, offset=0):
        super(gpp.UGenParameter, self).__init__(self)
        self.levels = levels or [0, 1, 0]  # Can't be empty or zero either.
        self.times = utl.wrap_extend(
            utl.as_list(times or [1, 1]), len(self.levels) - 1)
        self.curves = curves
        self.release_node = release_node
        self.loop_node = loop_node
        self.offset = offset
        self.__envgen_format = None
        self.__interpolation_format = None

    # no newClear
    # no kr
    # no ar
    # no setters


    ### Fixed duration common envelopes ###

    @classmethod
    def xyc(cls, xyc):
        '''Fixed duration envelope from control points with curvature.

        Parameters
        ----------
        xyc : list
            A list of lists of three elements `[time, level, curve]`.
            if possible, pairs are sorted regarding their point in time.
            Default curve value is 'lin'.

        '''

        if any(len(i) != 3 for i in xyc):
            raise ValueError(
                'xyc list must contain only sequences of length 3')
        xyc = xyc[:]  # Ensures internal state.
        xyc.sort(key=lambda x: x[0])
        times, levels, curves = utl.flop(xyc)
        offset = times[0]
        times = [b - a for a, b in utl.pairwise(times)]  # differentiate
        curves.pop(-1)  # Las point curvature is ignored.
        return cls(levels, times, curves, offset=offset)

    @classmethod
    def pairs(cls, pairs, curves=None):
        '''Fixed duration envelope from control points.

        Parameters
        ----------
        pairs : list
            A list of lists of two elements `[time, level]`.
            if possible, pairs are sorted regarding their point in time.
        curve : list | str | float | int
            Curvature of the segments. Default value is 'lin'.

        '''

        if any(len(i) != 2 for i in pairs):
            raise ValueError(
                'pairs list must contain only sequences of length 2')
        pairs = pairs[:]  # Ensures internal state.
        if curves is None:
            for i in range(len(pairs)):
                pairs[i].append('lin')
        elif isinstance(curves, (str, float, int)):
            for i in range(len(pairs)):
                pairs[i].append(curves)
        else:
            # NOTE: Last point curvature is ignored by xyc.
            if len(pairs) != len(curves):
                raise ValueError('pairs and curves must have the same length')
            for i in range(len(pairs)):
                pairs[i].append(curves[i])
        return cls.xyc(pairs)

    @classmethod
    def triangle(cls, dur=1.0, level=1.0):
        '''Fixed duration envelope specification with triangular shape.

        Parameters
        ----------
        dur : list | float | int
            Duration of the envelope.
        level : list | float | int
            Peak level of the envelope.

        '''

        dur = utl.list_binop(operator.mul, dur, 0.5)
        return cls([0, level, 0], [dur, dur])

    @classmethod
    def sine(cls, dur=1.0, level=1.0):
        '''Fixed duration envelope specification with hanning shape.

        Parameters
        ----------
        dur : list | float | int
            Duration of the envelope.
        level : list | float | int
            Peak level of the envelope.

        '''

        dur = utl.list_binop(operator.mul, dur, 0.5)
        return cls([0, level, 0], [dur, dur], 'sine')

    @classmethod
    def perc(cls, attack_time=0.01, release_time=1.0, level=1.0, curve=-4.0):
        '''Fixed duration evenlope which (usually) has a percussive shape.

        Parameters
        ----------
        attack_time : float | int | list
            Duration of the attack portion.
        release_time : float | int | list
            Duration of the release portion.
        level : float | int | list
            Peak level of the envelope.
        curve : str | float | int | list
            Curvature of the envelope.

        '''

        return cls([0, level, 0], [attack_time, release_time], curve)

    @classmethod
    def linen(cls, attack_time=0.01, sustain_time=1.0, release_time=1.0,
              level=1.0, curve='lin'):
        '''Fixed duration envelope specification with trapezoidal shape.

        Parameters
        ----------
        attack_time : list | float | int
            Duration of the attack portion.
        sustain_time : list | float | int
            Duration of the sustain portion.
        release_time : list | float | int
            Duration of the release portion.
        level : list | float | int
            Level of the sustain portion.
        curve : list | str | float | int
            Curvatuve of the envelope.

        '''

        return cls(
            [0, level, level, 0],
            [attack_time, sustain_time, release_time], curve)


    ### Sustained common envelopes ###

    @classmethod
    def step(cls, levels=None, times=None, release_level=None,
             loop_level=None, offset=0):
        '''Sustained envelope where all the segments are horizontal lines.

        Given n values of times only n levels need to be provided,
        corresponding to the fixed value of each segment.

        Parameters
        ----------
        levels : list
            Levels can be any ugen (new level values are updated only
            when the envelope has reached that point).
        times : list
            Durations of segments in seconds. It should be the same
            size as the levels array.
        release_level : int
            The index of the release level. The envelope will sustain
            at this level until released.
        loop_level : int
             Index of the loop level. If not ``None`` the envelop
             sustain will loop between this level and the release
             level.
        offset : float | int
            Offset to all time values (only applies in ``IEnvGen``).

        '''

        levels = levels or [0, 1]
        times = times or [1, 1]
        if len(levels) != len(times):
            raise ValueError('levels and times must have same length')
        levels = levels[:]  # Ensures internal state.
        levels.insert(0, levels[0])
        return Env(
            levels, times, 'step', release_level - 1, loop_level, offset)

    @classmethod
    def cutoff(cls, release_time=0.1, level=1.0, curve='lin'):
        '''Sustained envelope specification which has no attack segment.

        It simply sustains at the peak level until released. Useful if
        you only need a fadeout, and more versatile than ``Line``.

        Parameters
        ----------
        release_time : list | float | int
            Duration of the release portion.
        level : list | float | int
            Peak level of the envelope.
        curve : str
            Curvature of the envelope.

        '''

        curve_no = cls._shape_number(curve)
        release_level = bi.dbamp(-100) if curve_no == 2 else 0
        return cls([level, release_level], [release_time], curve, 0)

    @classmethod
    def dadsr(cls, delay_time=0.1, attack_time=0.01, decay_time=0.3,
              sustain_level=0.5, release_time=1.0, peak_level=1.0,
              curve=-4.0, bias=0.0):
        '''Sustained adsr envelope with onset delay.

        Parameters
        ----------
        delay_time : list | float | int
            Onset delay time.
        attack_time : list | float | int
            Duration of the attack portion.
        decay_time : list | float | int
            Duration of the decay portion.
        sustain_level : list | float | int
            Level of the sustain portion as a ratio of the peak level.
        release_time : list | float | int
            Duration of the release portion.
        peak_level : list | float | int
            Peak level of the envelope.
        curve : ist | str | float | int
            Curvature of the envelope.
        bias : list | float | int
            DC offset.

        '''

        return cls(
            utl.list_binop(
                operator.add,
                [0, 0, peak_level, peak_level * sustain_level, 0], bias),
            [delay_time, attack_time, decay_time, release_time], curve, 3)

    @classmethod
    def adsr(cls, attack_time=0.01, decay_time=0.3, sustain_level=0.5,
             release_time=1.0, peak_level=1.0, curve=-4.0, bias=0.0):
        '''Sustained envelope as traditional analog attack-decay-sustain-release.

        Parameters
        ----------
        attack_time : list | float | int
            Duration of the attack portion.
        decay_time : list | float | int
            Duration of the decay portion.
        sustain_level : list | float | int
            Level of the sustain portion as a ratio of the peak level.
        release_time : list | float | int
            Duration of the release portion.
        peak_level : list | float | int
            Peak level of the envelope.
        curve : ist | str | float | int
            Curvature of the envelope.
        bias : list | float | int
            DC offset.

        '''

        return cls(
            utl.list_binop(
                operator.add,
                [0, peak_level, peak_level * sustain_level, 0], bias),
            [attack_time, decay_time, release_time], curve, 2)

    @classmethod
    def asr(cls, attack_time=0.01, sustain_level=1.0,
            release_time=1.0, curve=-4.0):
        '''Sustained envelope as traditional analog attack-sustain-release.

        Parameters
        ----------
        attack_time : list | float | int
            Duration of the attack portion.
        sustain_level : list | float | int
            Level of the sustain portion as a ratio of the peak level.
        release_time : list | float | int
            Duration of the release portion.
        curve : ist | str | float | int
            Curvature of the envelope.

        '''

        return cls(
            [0, sustain_level, 0], [attack_time, release_time], curve, 1)

    @classmethod
    def cyclic(cls, levels, times, curves='lin'):  # was *circle
        '''Sustained envelope which cycles through its values.

        For making a given envelope cyclic, you can use the instance
        method ``circle``.

        Parameters
        ----------
        levels : list
            Values through which the envelope passes.
        times :  list | float | int
            Durations between subsequent levels in the envelope. If a
            list shorter than the levels list is passed it will be
            expanded. In difference to the default constructor method,
            the size of the times array is the same as that of the
            levels, because it includes the loop time.
        curves : list | str | float | int
            Curvature of the envelope. If a list shorter than the
            levels list is passed it will be expanded. In difference to
            the default constructor method, the size of the times array
            is the same as that of the levels, because it includes the
            loop time.

        Notes
        -----
        Cyclic envelopes use ugens internally thus they can only be
        used within a synthdef function.

        '''

        times = utl.wrap_extend(utl.as_list(times), len(levels))
        last_time = times.pop()
        curves = utl.wrap_extend(utl.as_list(curves), len(levels))
        last_curve = curves.pop()
        return cls(levels, times, curves).circle(last_time, last_curve)

    def circle(self, last_time=0.0, last_curve='lin'):
        '''Make the envelope cyclical.

        Parameters
        ----------
        last_time : float | int
            Transition time from the end to the beginning of the
            evenlope.
        last_curve : str
            Curvature of the transition from the end to the beginning
            of the evenlope.

        '''

        # // Connect releaseNode (or end) to first node of envelope.
        if _libsc3.main._current_synthdef is None:
            raise Exception('circle can only be used within graph functions')
        first_0_then_1 = trg.Latch.kr(1.0, ocl.Impulse.kr(0.0))
        if self.release_node is None:
            self.levels = [0.0, *self.levels, 0.0]
            self.curves = utl.wrap_extend(
                utl.as_list(self.curves), len(self.times))
            self.curves = [last_curve, *self.curves, 'lin']
            self.times = [
                first_0_then_1 * last_time, *self.times, float('inf')]
            self.release_node = len(self.levels) - 2
        else:
            self.levels = [0.0, *self.levels]
            self.curves = utl.wrap_extend(
                utl.as_list(self.curves), len(self.times))
            self.curves = [last_curve, *self.curves]
            self.times = [first_0_then_1 * last_time, *self.times]
            self.release_node += 1
        self.loop_node = 0
        return self

    @property
    def duration(self):
        '''Duration of the envelope as the sum of `times`.

        '''

        return utl.list_sum(self.times)

    @duration.setter
    def duration(self, value):
        res = utl.list_binop(
            operator.mul, self.times, 1 / self.total_duration())
        self.times = utl.list_binop(operator.mul, res, value)

    def total_duration(self):
        '''Duration of the longest envelop (multichannel case).

        '''

        duration = utl.list_sum(self.times)
        return utl.list_max(utl.as_list(duration))

    @property
    def release_time(self):
        '''Duration of the release portion of the envelope.

        '''

        if self.release_node is None:
            return 0.0
        else:
            return utl.list_sum(self.times[self.release_node:])

    @property
    def is_sustained(self):
        '''Return `True` if the envelope is sustained.

        '''

        return self.release_node is not None

    def range(self, lo=0.0, hi=1.0):
        '''Return a copy of the envelope with the levels mapped linearly.

        Parameters
        ----------
        lo : float | int
            Lower value of the new range.
        hi : float | int
            Maximum value of the new range.

        '''

        obj = copy.copy(self)
        min = utl.list_min(obj.levels)
        max = utl.list_max(obj.levels)
        obj.levels = utl.list_narop(bi.linlin, obj.levels, min, max, lo, hi)
        return obj

    def exprange(self, lo=0.01, hi=1.0):
        '''Return a copy of the envelope with the levels mapped exponentially.

        Parameters
        ----------
        lo : float | int
            Lower value of the new range. Must be greater than 0.
        hi : float | int
            Maximum value of the new range.

        '''

        obj = copy.copy(self)
        min = utl.list_min(obj.levels)
        max = utl.list_max(obj.levels)
        obj.levels = utl.list_narop(bi.linexp, obj.levels, min, max, lo, hi)
        return obj

    def curverange(self, lo=0.0, hi=1.0, curve=-4):
        '''Return a copy of the envelope with the levels mapped to a curvature.

        Parameters
        ----------
        lo : float | int
            Lower value of the new range.
        hi : float | int
            Maximum value of the new range.
        curve : float | int
            Curvature of the mapping.

        '''

        obj = copy.copy(self)
        min = utl.list_min(obj.levels)
        max = utl.list_max(obj.levels)
        obj.levels = utl.list_narop(
            bi.lincurve, obj.levels, min, max, lo, hi, curve)
        return obj

    # TODO
    # asMultichannelSignal
    # asSignal
    # discretize
    # storeArgs
    # ==
    # hash
    # at
    # embedInStream
    # asStream
    # asPseg
    # blend
    # delay
    # circle (moved up)
    # test

    @classmethod
    def _shape_number(cls, name):
        name = utl.as_list(name)
        ret = []
        for item in name:
            if gpp.ugen_param(item)._is_valid_ugen_input():
                ret.append(5)  # 'curvature value', items is not NaN SimpleNumber.
            else:
                try:
                    shape = cls._SHAPE_NAMES[item]
                    ret.append(shape)
                except KeyError as e:
                     raise ValueError(f"invalid Env shape '{item}'") from e
        return utl.unbubble(ret)

    @classmethod
    def _curve_value(cls, curve):
        if isinstance(curve, list):
            ret = []
            for item in curve:
                if gpp.ugen_param(item)._is_valid_ugen_input():
                    ret.append(item)
                else:
                    ret.append(0)
            return ret
        else:
            if gpp.ugen_param(curve)._is_valid_ugen_input():
                return curve
            else:
                return 0

    def _envgen_format(self):  # Was asMultichannelArray.
        if self.__envgen_format:  # this.array
            return self.__envgen_format

        # prAsArray
        levels = gpp.ugen_param(self.levels)._as_ugen_input()
        times = gpp.ugen_param(self.times)._as_ugen_input()
        curves = gpp.ugen_param(utl.as_list(self.curves))._as_ugen_input()
        size = len(self.times)
        contents = []

        contents.append(levels[0])
        contents.append(size)
        aux_input = gpp.ugen_param(self.release_node)._as_ugen_input()
        if aux_input is None:
            aux_input = -99
        contents.append(aux_input)
        aux_input = gpp.ugen_param(self.loop_node)._as_ugen_input()
        if aux_input is None:
            aux_input = -99
        contents.append(aux_input)

        for i in range(size):
            contents.append(levels[i + 1])
            contents.append(times[i])
            contents.append(type(self)._shape_number(curves[i % len(curves)]))
            contents.append(type(self)._curve_value(curves[i % len(curves)]))

        self.__envgen_format = [tuple(i) for i in utl.flop(contents)]
        return self.__envgen_format

    def _interpolation_format(self):  # Was asArrayForInterpolation.
        '''This version is for IEnvGen which has a special format.'''
        if self.__interpolation_format:
            return self.__interpolation_format

        levels = gpp.ugen_param(self.levels)._as_ugen_input()
        times = gpp.ugen_param(self.times)._as_ugen_input()
        curves = gpp.ugen_param(utl.as_list(self.curves))._as_ugen_input()
        size = len(self.times)
        contents = []

        aux_input = gpp.ugen_param(self.offset)._as_ugen_input()
        if aux_input is None:
            aux_input = 0
        contents.append(aux_input)
        contents.append(levels[0])
        contents.append(size)
        contents.append(utl.list_sum(times))

        for i in range(size):
            contents.append(times[i])
            contents.append(type(self)._shape_number(curves[i % len(curves)]))
            contents.append(type(self)._curve_value(curves[i % len(curves)]))
            contents.append(levels[i + 1])

        self.__interpolation_format = [tuple(i) for i in utl.flop(contents)]
        return self.__interpolation_format

    def _at(self, time):
        data = self._envgen_format()
        time = max(0, time - self.offset)
        return utl.unbubble([self._env_at(d, time) for d in data])

    def _env_at(self, data, time):
        # Values of data tuple:
        # (start_level, num_stages, release_node, loop_node, stage1 [, ...])
        # stage = *(target_level, target_dur, shape, curve)
        if len(data) < 8:
            raise ValueError('Env must have at least one stage')

        start_level = float(data[0])  # *** begLevel
        num_stages = data[1]
        begin_time = end_time = 0.0  # *** begTime, endTime
        shape_names = self._SHAPE_NAMES

        for i in range(4, num_stages * 4 + 1, 4):
            target_level = float(data[i])  # *** endLevel
            target_dur = data[i + 1]  # *** dur
            end_time += target_dur

            if time < end_time:
                shape = data[i + 2]
                pos = (time - begin_time) / target_dur

                if shape == shape_names['step']:
                    return target_level
                elif shape == shape_names['hold']:
                    return start_level
                elif shape == shape_names['linear']:
                    return pos * (target_level - start_level) + start_level
                elif shape == shape_names['exponential']:
                    if start_level == 0.0: return 0.0
                    return start_level * bi.pow(target_level / start_level, pos)
                elif shape == shape_names['sine']:
                    return (
                        start_level + (target_level - start_level) *
                        (-bi.cos(bi.pi * pos) * 0.5 + 0.5))
                elif shape == shape_names['welch']:
                    if start_level < target_level:
                        return (
                            start_level + (target_level - start_level) *
                            bi.sin(bi.pi2 * pos))
                    else:
                        return (
                            target_level - (target_level - start_level) *
                            bi.sin(bi.pi2 - bi.pi2 * pos))
                elif shape == 5:  # 'curvature value'
                    curve = data[i + 3]
                    if math.fabs(curve) < 0.0001:
                        return pos * (target_level - start_level) + start_level
                    else:
                        fac = (
                            (1.0 - bi.exp(pos * curve)) /
                            (1.0 - bi.exp(curve)))
                        return (
                            start_level + (target_level - start_level) * fac)
                elif shape == shape_names['squared']:
                    sqrt_sl = bi.sqrt(start_level)
                    sqrt_tl = bi.sqrt(target_level)
                    sqrt_level = pos * (sqrt_tl - sqrt_sl) + sqrt_sl
                    return sqrt_level * sqrt_level
                elif shape == shape_names['cubed']:
                    cbrt_sl = bi.pow(start_level, 0.3333333)
                    cbrt_tl = bi.pow(target_level, 0.3333333)
                    cbrt_level = pos * (cbrt_tl - cbrt_sl) + cbrt_sl
                    return cbrt_level * cbrt_level * cbrt_level
                else:
                    raise ValueError(f'invalid shape number: {shape}')
            else:
                start_level = target_level
                begin_time = end_time

        return start_level

    def __repr__(self):
        return (
            f'{type(self).__name__}({self.levels}, {self.times}, '
            f'{repr(self.curves)}, {self.release_node}, {self.loop_node}, '
            f'{self.offset})')


    ### Node parameter interface ###

    def _as_control_input(self):
        return utl.unbubble(self._envgen_format())

    def _embed_as_osc_arg(self, lst):
        gpp.node_param(self._as_control_input())._embed_as_osc_arg(lst)
