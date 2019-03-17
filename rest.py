"""Rest.sc"""

import supercollie.operand as opd
from supercollie.graphparam import ugen_param


class Rest(opd.Operand):
    # TODO: todo.

    # UGen graph parameter interface #
    # TODO: ver el resto en UGenParameter

    def as_control_input(self):
        return ugen_param(self.value).as_control_input()

    # TODO...
