"""Stream.sc"""

import inspect
from abc import ABC, abstractmethod

import supercollie.functions as fn


class Stream(fn.AbstractFunction, ABC):
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

    def __init__(self, func):
        # NOTE: nope, en Routine puede que la función sea una función no generadora, ver.
        # if not inspect.isgeneratorfunction(func): # BUG: o tiene que ser un pattern (porque pattern envuelve una genfunc)
        #     raise TypeError('Stream func arg is not a generator function')
        self.func = func
        self._iterator = None

    ### iterator protocol ###

    def __iter__(self):
        return self.iter()

    def __next__(self):
        raise self.next() # TODO: en Python no son infinitos por defecto

    def __call__(self, inval=None):
        return self.next(inval)

    def iter(self):
        return self

    @abstractmethod # NOTE: la clase que se usa como Stream por defecto es Routine (hay otras)
    def next(self, inval=None):
        pass

    @property # BUG: ver si es realmente necesario definir esta propiedad
    def parent(self): # TODO: entiendo que esta propiedad, que no se puede declarar como atributo, es por parent de Thread
        return None

    # def stream_arg(self): # BUG: se usa para Pcollect, Pselect, Preject, el método lo definen Object y Pattern también.
    #     return self

    def all(inval=None):
        lalala

    # put
    # putN
    # putAll
    # do
    # subSample # es un tanto específico, evalúa a partir de offset una cantidad skipSize
    # generate # método interno para list comprehensions, documentado en Object

    # Estos métodos acá se podrían dejar para generator list comprehensions
    # collect
    # reject
    # select

    # dot # // combine item by item with another stream # NOTE: usa FuncStream
    # interlace # // interlace with another stream # NOTE: usa FuncStream
    # ++ (appendStream)
    # append_stream # NOTE: usa Routine con embedInStream
    # collate # // ascending order merge of two streams # NOTE: usa interlace
    # <> # Pchain

    def compose_unop(self, selector):
        return UnaryOpStream(selector, self)

    def compose_binop(self, selector, other):
        return BinaryOpStream(selector, self, other) # BUG: en sclang usa el adverbio y si es nil la operación binaria retorna nil, no sé para qué se usa.

    def compose_narop(self, selector, *args):
        return NAryOpStream(selector, self, *args)

    # TODO: ver embedInStream que se puede usar en las operaciones entre Streams
    # embedInStream # NOTE: es yield from en Python, creo que no se puede implementar como método

    # asEventStreamPlayer
    # play
    # trace
    # repeat

    # reset # NOTE: la docuemntación dice que está pero no todos los streams lo implementan.


### BasicOpStream.sc ###


class UnaryOpStream(Stream):
    pass


class BinaryOpStream(Stream):
    pass


class NAryOpStream(Stream):
    pass


### higher level abstractions ###


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


# class OneShotStream(Stream): pass # TODO: ver para qué sirve, la única referencia está en Object:iter, no está documentada.
# class EmbedOnce(Stream): pass # TODO, ver, solo se usa en JITLib, no está documentada.
# class StreamClutch(Stream): pass # TODO: no se usa en la librería de clases, actúa como un filtro, sí está documentada.
# class CleanupStream(Stream): pass # TODO: no se usa en la librería de clases, creo, ver bien, no tiene documentación.
