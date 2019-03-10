"""Event.sc"""


class Event():
    # TODO: todo

    # UGen graph parameter interface #
    # TODO: ver el resto en UGenParameter

    def as_ugen_input(self, *_):
        return self.as_control_input()

    def as_control_input(self):
        pass # TODO ^this[ EventTypesWithCleanup.ugenInputTypes[this[\type] ] ];

    # TODO...
