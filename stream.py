"""Stream.sc"""

import supercollie.functions as fn


class Stream(fn.AbstractFunction):
    # TODO:
    #     * Stream actúa como conotenedor e iterador en sclang
    #     * los generadores implementan __iter__, los iteradores además implementan __next__
    #     * No me queda claro cómo deberían ser los equivalentes, Stream,
    #       al ser AbstractFunction implementa las operaciones matemáticas y eso
    #       iría sobre los iteradores o los generadores?
    #     * Por lo que veo no es necesario implementar Stream para que funcione
    #       lo básico de Routine.
    # TODO: OK, la cosa será así, al menos por ahora, Stream es un iterador
    # y Pattern es un generador, es lo que hace sclang en su explicación teórica.
    # La gracia de ambos es que son AbstractFunctions.
    # Tengo que ver, después, por qué Stream implementa la funcionalidad de los
    # contenedores, pero la idea es no agregar funcionalidad demás.
    # Tengo que ver cuándo sirve el método send de Python, tal vez para
    # embedInStream.

    # @property
    # def parent(self): return None # TODO: entiendo que esta propiedad, que no se puede declarar como atributo, es por parent de Thread
    # iter
    # next
    # reset
    # streamArg
    # value (llama a next(inval))
    # valueArray (llama a next sin inval)

    # iterator protocol
    def __iter__(self): # TODO: tal vez también convenga definir iter y next no mágicos
        return self
    def __next__(self): # TODO: tal vez sí convenga definir next no mágico, además, next en sclang es como send en Python
        raise self # TODO: en Python no son infinitos por defecto

    # TODO: todos los métodos el comportamiento de AbstractFunction
    # TODO: ver embedInStream que se puede usar en las operaciones entre Streams


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
