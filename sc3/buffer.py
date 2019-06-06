"""Buffer.sc"""

from sc3.graphparam import UGenParameter


class Buffer(UGenParameter):
    # TODO: todo.

    # UGen graph parameter interface #
    # TODO: ver el resto en UGenParameter

    def as_ugen_input(self, *_):
        return self.bufnum

    def as_control_input(self):
        return self.bufnum
