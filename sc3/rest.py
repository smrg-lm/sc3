"""Rest.sc"""

from . import operand as opd
from . import graphparam as gpp


class Rest(opd.Operand):
    def __init__(self, value=1.0):
        super().__init__(value)

    @property
    def dur(self):
        return self.value

    @dur.setter
    def dur(self, value):
        self.value = value

    def __bool__(self):
        # unwrapBoolean
        return self.value

    # BUG: Aún no vi cómo se usa Rest en Pbind, EventStreamPlayer o similares.
    # Rest puede ser el valor de una llave en Pbind o similares, por eso actúa
    # como Stream. Rest debe poder ser el valor de retorno de un event pattter
    # en vez de un Evento, por eso actúá como tal (__embed__, __stream__). Rest
    # debe poder ser un parámetro de nodo en alguna parte, por eso
    # _as_control_input, pero pone el método junto a playAndDelta e isRest.

    # TODO... hereda la capacidad de ops de Operand, luego tiene "event support" con asControlInput, playAndDelta e isRest
