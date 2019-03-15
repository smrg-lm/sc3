"""Stream.sc"""

import inspect
#from abc import ABC, abstractmethod # BUG: comentado por __new__, probablemente vuelva, pero en sclang no es clase abstracta?

import supercollie.functions as fn
from . import thread as thr


class Stream(fn.AbstractFunction): #, ABC):
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

    ### iterator protocol ###

    def __iter__(self):
        return self.iter()

    def __next__(self):
        return self.next() # TODO: en Python no son infinitos por defecto

    def __call__(self, inval=None):
        return self.next(inval)

    def iter(self, inval=None):
        return self # BUG: es self para Routine?

    #@abstractmethod # NOTE: la clase que se usa como Stream por defecto es Routine (hay otras)
    def next(self, inval=None): # se define en Object y se sobreescribe con subclassResponsibility en Stream
        pass

    def stream(self): # BUG: cambié el nombre de asString, en sclang se define en Object devolviendo this, es protocolo
        return self # BUG: es self para Routine?

    # @property # BUG: ver si es realmente necesario definir esta propiedad
    # def parent(self): # TODO: entiendo que esta propiedad, que no se puede declarar como atributo, es por parent de Thread
    #     return None

    # def stream_arg(self): # BUG: se usa para Pcollect, Pselect, Preject, el método lo definen Object y Pattern también.
    #     return self

    def all(inval=None):
        lst = []
        item = self.next(inval)
        while item is not None:
            lst.append(item)
        return lst

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
        return BinaryOpStream(selector, self, as_stream(other)) # BUG: en sclang usa el adverbio y si es nil la operación binaria retorna nil, no sé para qué se usa.

    def compose_narop(self, selector, *args):
        args = [as_stream(x) for x in args]
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
    def __init__(self, selector, a):
        self.selector = selector
        self.a = a

    def next(self, inval=None):
        a = self.a.next(inval)
        if a is None:
            return None
        else:
            return getattr(a, self.selector)()

    def reset(self):
        self.a.reset()

    # storeOn # TODO


class BinaryOpStream(Stream):
    def __init__(self, selector, a, b):
        self.selector = selector
        self.a = a
        self.b = b

    def next(self, inval=None):
        a = self.a.next(inval) # BUG: a o b pueden no ser streams, polimorfismo
        if a is None:          # BUG: con StopIteration no es necesaria la comprobación
            return None        # BUG: revisar todos los op.
        b = self.b.next(inval)
        if b is None:
            return None
        return getattr(a, self.selector)(b)

    def reset(self):
        self.a.reset()
        self.b.reset()

    # storeOn # TODO


class NAryOpStream(Stream):
    def __init__(self, selector, a, *args):
        self.selector = selector
        self.a = a
        self.args = args # BUG: cambié los nombres arglist, isNumeric

    @property
    def args(self):
        return self._args

    @args.setter
    def args(self, value):
        # // optimization
        self._numeric = all(isinstance(x, (int, float, str)) for x in value)
        self._args = list(value)

    def next(self, inval=None):
        a = self.a.next(inval)
        if a is None:
            return None
        if self._numeric:
            args = self._args
        else:
            args = []
            res = None
            for item in self._args:
                if isinstance(item, Stream):
                    res = item.next(inval)
                else:
                    res = item
                if res is None:
                    return None
                args.append(res)
        return getattr(a, self.selector)(*args)

    def reset(self):
        self.a.reset()
        for item in self._args:
            if isinstance(item, Stream):
                item.reset()

    # storeOn # TODO


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

def as_stream(obj): # BUG: es asStream, ver nombre
    # NOTE: Esto es nuevo, la clase la estoy usando como
    # función de interfaz para convertir otros tipos, como funcionan
    # list, int, etc. en Python, aunque en este caso puede devolver
    # el objeto entrante... no es lo mismo, tal vez mejor una función
    # y el método mágico __stream__.
    # BUG: Luego tengo que revisar si resulta coherente además de práctico.
    # NOTE: Así es como si cualquier objeto pudiera ser convertido
    # en un Stream, pero porque esta clase tiene una sola subclase,
    # o implementa el protocolo stream (que tendría que ser __stream__).
    # En este caso se puede porque los tipos básico retornan todos self.
    # Se usa en compose.
    # NOTE: La verdad que se podría usar un método de clase, pero para
    # sentir cómo queda, la otra es implementar una función 'stream(obj)'
    # a nivel de módulo.
    # *************************************************************************
    # NOTE: IMPORTANTE: En Python todos los iterables responden a yield from,
    # creo que con que los Patterns sean iterables alcanza y el equivalente a
    # embedInStream es devolver un iterador... pero está el problema de inval.
    # *************************************************************************
    if isinstance(obj, Stream):
        return obj # NOTE: no se define __init__, la única subclase es Routine que usa __init__ de TimeThread
    if hasattr(obj, 'stream'): # BUG: no sé si alcanza para definir una interfaz, cualquier clase puede tener este método, tal vez __stream__, pero tengo que revisar todas las otras interfaces también.
        return obj.stream() # NOTE: es asStream que es método de interfaz
    if hasattr(obj, '__iter__'): # BUG: alcanza con esto?
        def _(inval=None):
            yield from item # NOTE: funciona incluso para dict
        return thr.Routine(_)
    return obj
