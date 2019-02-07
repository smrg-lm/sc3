"""Stream.sc"""

import supercollie.functions as fn


class Stream(fn.AbstractFunction):
    # TODO: esta clase implementa:
    #     * el comportamiento de yield en las TimeThread y Routines (que está a bajo nivel)
    #     * la interfaz de los generadores de Python
    pass


class FuncStream(Stream):
    pass


# // PauseStream is a stream wrapper that can be started and stopped.
class PauseStream(Stream):
    pass

# // Task is a PauseStream for wrapping a Routine
class Task(PauseStream):
    pass


class EventStreamPlayer(PauseStream):
    pass


# class OneShotStream(Stream): pass # TODO: ver para qué sirve, la única referencia está en Object:iter, , no está documentada
# class EmbedOnce(Stream): pass # TODO, ver, solo se usa en JITLib, no está documentada
# class StreamClutch(Stream): pass # TODO: no se usa en la librería de clases, actúa como un filtro, sí está documentada.
# class CleanupStream(Stream): pass # TODO: no se usa en la librería de clases, no tiene documentación
