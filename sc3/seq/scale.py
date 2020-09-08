"""Scale.sc"""

import math

from ..base import builtins as bi


__all__ = ['Scale', 'Tuning']


class Scale(tuple):
    _ALL = dict()

    # __slots__ = ('_tuning', '_ppo', '_name')

    # Tuning is the set of possible pitch clases (len(tuning)) in a Scale,
    # expressed as factors/ratios. Degrees are a sub-set of tuning ratios
    # expressed as indexes of tuning, len(degrees) is pitches per octave (ppo).
    # There is also steps per octave (spo) that depends on the octave ratio,
    # spo may differ from len(tuning) if octave ratio is different than 2.
    # Note that the word 'degree' as event key refers to the actual positional
    # degree of a scale, the first, second, third, and so on. Scale and Tuning
    # objects are immutable by now. Although I can see use cases for mutability
    # these complicate the code. Structures can be made mutable later anyway.

    def __new__(cls, degrees, tuning=None, *, name=None):
        return super().__new__(cls, degrees)

    def __init__(self, degrees, tuning=None, *, name=None):
        if tuning is None:
            tuning = Tuning.et(12)
            name = tuning.name
        else:
            tuning = Tuning(tuning)
        if max(degrees) > len(tuning) - 1:
            raise ValueError(
                f'max scale degree {max(degrees)} exceeds '
                f'{tuning.name} tuning ppo range')
        self._ppo = len(degrees)
        self._tuning = tuning
        self._name = name

    @classmethod
    def from_name(cls, name, tuning=None):  # Was newFromKey.
        try:
            scale = cls(cls._ALL[name], tuning, name=name)
        except KeyError:
            raise ValueError(f"invalid scale name '{name}'") from None
        return scale

    @classmethod
    def chromatic(cls, tuning=None):
        if tuning is None:
            tuning = Tuning.from_name('et12')
        ppo = len(tuning)
        name = f'Chromatic {ppo} {tuning.name}'
        return cls(range(ppo), tuning, name=name)

    @property
    def ppo(self):
        return self._ppo

    @property
    def tuning(self):
        return self._tuning

    @property
    def name(self):
        return self._name

    def degree_to_key(self, degree, acc=0):
        # Accidentals only work for et scales? Why not a fraction?
        spo = self.tuning._spo
        l = len(self)
        base_key = (spo * (degree // l)) + self[int(degree) % l]
        if acc == 0:
            return base_key
        else:
            return base_key + acc * (spo / self._ppo)

    def key_to_degree(self, note):  # note in spo, midinote/note?
        spo = self.tuning._spo
        n = note // spo * self._ppo  # N octaves in ppo.
        key = note % spo
        return bi.index_in_between(self, key) + n

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return (
                super().__eq__(other)
                and self._tuning == other._tuning
                and self._name == other._name)
        else:
            return False

    def __hash__(self):
        return hash((super().__hash__(), self._tuning, self._name))

    def __repr__(self):
        return f'Scale({super().__repr__()}, {self._tuning}, name={self._name})'

    # @property
    # def degree_ratios(self):  # Was semitones.
    #     tuning = self._tuning
    #     return tuple(tuning[i] for i in self)
    #
    # @property
    # def midi_ratios(self):  # Was ratios.
    #     ...
    #
    # performNearestInList
    # performNearestInScale
    # degreeToRatio
    # degreeToFreq
    # *choose
    # *chooseFromSelected
    # *names
    # octaveRatio
    # stepsPerOctave


class Tuning(tuple):
    _ALL = dict()

    # __slots__ = ('_octave_ratio', '_name', '_spo')

    def __new__(cls, tuning, octave_ratio=2.0, *, name=None):
        return super().__new__(cls, tuning)

    def __init__(self, tuning, octave_ratio=2.0, *, name=None):
        self._octave_ratio = octave_ratio
        self._name = name
        self._spo = math.log2(octave_ratio) * len(tuning)

    @classmethod
    def from_name(cls, name):  # Was newFromKey.
        try:
            tuning = cls._ALL[name]
        except KeyError:
            raise ValueError(f"invalid tuning name '{name}'") from None
        return tuning

    @classmethod
    def et(cls, spo=12):
        ratio = 12 / spo
        tuning = tuple(i * ratio for i in range(spo))
        return cls(tuning, 2.0, name='et' + str(spo))

    @property
    def octave_ratio(self):
        return self._octave_ratio

    @property
    def name(self):
        return self._name

    @property
    def spo(self):  # Was stepsPerOctave.
        return self._spo

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return (
                super().__eq__(other)
                and self._octave_ratio == other._octave_ratio
                and self._name == other._name)
        else:
            return False

    def __hash__(self):
        return hash((super().__hash__(), self._octave_ratio, self._name))

    def __repr__(self):
        return (
            f'Tuning({super().__repr__()}, '
            f'{self._octave_ratio}, '
            f'name={self._name})')
