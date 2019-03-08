"""Rest.sc"""

import supercollie.operand as opd
import supercollie.ugens as ugn


class Rest(opd.Operand):
    # TODO: todo.

    # UGen graph parameter interface #
    # TODO: ver el resto en GraphParameter

    def as_control_input(self):
        return ugn.GraphParameter(self.value).as_control_input() # FIXME: creo que es así, y ahora veo que si querer hice una implementación de Operand.

    # TODO...
