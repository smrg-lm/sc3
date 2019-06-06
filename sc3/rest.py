"""Rest.sc"""

import sc3.operand as opd
from sc3.graphparam import ugen_param


class Rest(opd.Operand):
    def __init__(self, value=1.0):
        super().__init__(value)

    @property
    def dur(self):
        return self.value

    @dur.setter
    def dur(self, value):
        self.value = value

    # BUG: Aún no vi cómo se usa Rest en Pbind, EventStreamPlayer o similares.
    # BUG: el método unwrapBoolean es un bug, la clase devuelve objeto de sí misma, no se usa, ver problemas, anuncia que "comparisons just works" si devuelve Boolean.

    # TODO... hereda la capacidad de ops de Operand, luego tiene "event support" con asControlInput, playAndDelta e isRest
