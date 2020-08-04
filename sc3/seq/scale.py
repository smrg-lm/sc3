"""Scale.sc"""

import math


__all__ = ['Scale', 'Tuning']


class Scale(list): # BUG: Tuning es como un array en sc y Scale implementa la intefaz llamando a Tuning, pero no sé si conviene heredar de tuple/list acá, esto es todo provisorio para seguir con Event
    # TODO

    def __init__(self, degrees='ionian', ppo=None, tuning=None, name='Unknown Scale'):
        # TODO
        self.tuning = Tuning([0, 2, 4, 5, 7, 9, 11]) # TODO: tuning or Tuning.default(ppo) # BUG: tiene setter especial
        super().__init__(self.tuning) # BUG: provisorio
        # TODO

    # NOTE: podría ser property como en Tuning y acá abajo en octave_ratio
    def spo(self):
        return self.tuning.spo()

    @property
    def octave_ratio(self):
        return self.tuning.octave_ratio

    def degree_to_key(self, degree, spo=None, acc=0): # NOTE: es performDegreeToKey, spo = steps per octave, acc = accidental
        if spo is None:
            spo = self.tuning.spo()
        l = len(self)
        base_key = spo * (degree // l) + self[degree % l]
        if acc == 0:
            return base_key
        else:
            return base_key + acc * (spo / 12)

    # TODO


class Tuning(list): # BUG: Ídem Scale
    # TODO

    def __init__(self, tuning, octave_ratio=2.0, name='Unknown Tuning'):
        # TODO
        super().__init__(tuning)
        self.octave_ratio = octave_ratio # BUG: es read only
        # TODO

    def spo(self):
        return math.log2(self.octave_ratio) * 12 # NOTE: por qué 12.0 siempre es constante en relación a distintas cantidades de pasos por octava.

    # TODO


# TODO: sigue...
