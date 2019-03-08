"""Buffer.sc"""

class Buffer():
    # TODO: todo.

    # UGen graph parameter interface #
    # TODO: ver el resto en GraphParameter

    def as_ugen_input(self, *_):
        return self.bufnum

    def as_control_input(self):
        return self.bufnum
