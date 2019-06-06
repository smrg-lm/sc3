"""Stream.sc"""

import inspect
#from abc import ABC, abstractmethod # BUG: comentado por __new__, probablemente vuelva, pero en sclang no es clase abstracta?

import sc3.functions as fn
from . import thread as thr


class Stream(fn.AbstractFunction): #, ABC):
    ### iterator protocol ###

    def __iter__(self):
        return self

    def __stream__(self):
        return self

    def __embed__(self, inval=None):
        while True:
            yield self.next(inval)

    def __next__(self):
        return self.next() # TODO: en Python no son infinitos por defecto

    def __call__(self, inval=None):
        return self.next(inval)

    #@abstractmethod # NOTE: la clase que se usa como Stream por defecto es Routine (hay otras)
    def next(self, inval=None): # se define en Object y se sobreescribe con subclassResponsibility en Stream
        pass

    # @property # BUG: ver si es realmente necesario definir esta propiedad
    # def parent(self): # TODO: entiendo que esta propiedad, que no se puede declarar como atributo, es por parent de Thread
    #     return None

    # def stream_arg(self): # BUG: se usa para Pcollect, Pselect, Preject, el método lo definen Object y Pattern también.
    #     return self

    def all(self, inval=None):
        self.reset()
        item = None
        lst = []
        while True:
            try:
                item = self.next(inval)
                lst.append(item)
            except StopIteration:
                break
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
        return BinaryOpStream(selector, self, stream(other)) # BUG: BUG: en sclang usa el adverbio y si es nil la operación binaria retorna nil, tal vez porque sin él no hace la operación elemento a elemento de los streams.

    def compose_narop(self, selector, *args):
        args = [stream(x) for x in args]
        return NAryOpStream(selector, self, *args)

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
        a = self.a.next(inval) # NOTE: tira StopIteration
        if hasattr(self.selector, '__scbuiltin__'):
            return self.selector(a)
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
        a = self.a.next(inval) # NOTE: tira StopIteration
        b = self.b.next(inval)
        if hasattr(self.selector, '__scbuiltin__'):
            return self.selector(a, b)
        else:
            ret = getattr(a, self.selector)(b)
            if ret is NotImplemented and type(a) is int and type(b) is float: # BUG: ver cuál era el caso de este problema
                return getattr(float(a), self.selector)(b)
            return ret

    def reset(self):
        self.a.reset()
        self.b.reset()

    # storeOn # TODO


class NAryOpStream(Stream):
    def __init__(self, selector, a, *args):
        self.selector = selector
        self.a = a
        self.args = args # BUG: cambié el nombres arglist, no uso la optimización isNumeric, todos los args son stream (convertidos en la llamada)

    def next(self, inval=None):
        a = self.a.next(inval) # NOTE: tira StopIteration
        args = []
        res = None
        for item in self.args:
            res = item.next(inval) # NOTE: tira StopIteration
            args.append(res)
        if hasattr(self.selector, '__scbuiltin__'):
            return self.selector(a, *args)
        else:
            return getattr(a, self.selector)(*args)

    def reset(self):
        self.a.reset()
        for item in self.args:
            item.reset()

    # storeOn # TODO


### higher level abstractions ###


class FuncStream(Stream):
    pass


# TODO * TODO * TODO * TODO * TODO * TODO * TODO * TODO * TODO * TODO * TODO *
# Como maestro Zen, lo próximo que tengo que hacer es NotificationCenter
# con WEAKREFERECE, y TESTs. Ir haciendo los test y los casos de uso, prolijo,
# detallado por archivo y clase. Ver métodologías de UnitTest. Recién luego
# volver acá, porque aquello se necesita para Server también. Los casos de uso
# para las rutinas, streams y patterns, porque me olvido. Anotar el flujo del
# programa en los tests (luego y sobre todo en SystemClock y AppClock,
# embed(InStream) y (as)stream, cómo funciona el yield from, etc. Es volver a
# estudiar y retener. Comenzar con NotificationCenter (y reemplazar dependancy).


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


def stream(obj):
    if hasattr(obj, '__stream__'):
        return obj.__stream__()
    if hasattr(obj, '__iter__'):
        def _(inval=None):
            yield from obj
        return thr.Routine(_)

    def _(inval=None):
        while True: # BUG: los Object son streams infinitos el problema es que no se comportan lo mismo con embedInStream, ahí son finitos, valores únicos.
            yield obj
    return thr.Routine(_)


def embed(obj, inval=None):
    if hasattr(obj, '__embed__'):
        return obj.__embed__(inval)
    if hasattr(obj, '__stream__') or hasattr(obj, '__iter__'):
        return  stream(obj).__embed__(inval)

    def _(inval=None):
        yield obj
    return thr.Routine(_).__embed__()
