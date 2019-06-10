"""Stream.sc"""

import inspect
#from abc import ABC, abstractmethod # BUG: comentado por __new__, probablemente vuelva, pero en sclang no es clase abstracta?

from . import main as _main
from . import thread as thr
from . import clock as clk
import sc3.functions as fn
import sc3.model as mdl


class StopStream(StopIteration):
    pass


# NOTE: para _RoutineYieldAndReset, ver método de Routine
class YieldAndReset(Exception):
    def __init__(self, value=None):
        super().__init__()
        self.value = value


# NOTE: para _RoutineAlwaysYield, ver método de Routine
class AlwaysYield(Exception):
    def __init__(self, terminal_value=None):
        super().__init__()
        self.terminal_value = terminal_value


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

    def yield_and_reset(self, value=None):
        if self is _main.Main.current_TimeThread:
            raise YieldAndReset(value)
        else:
            raise Exception('yield_and_reset only works if self is main.Main.current_TimeThread')

    def always_yield(self, value=None):
        if self is _main.Main.current_TimeThread:
            raise AlwaysYield(value) # BUG: ver como afecta a StopIteration
        else:
            raise Exception('always_yield only works if self is main.Main.current_TimeThread')

    #@abstractmethod # NOTE: la clase que se usa como Stream por defecto es Routine (hay otras)
    def next(self, inval=None): # se define en Object y se sobreescribe con subclassResponsibility en Stream
        raise NotImplementedError('Stream is an abstract class') # BUG: ver abc, ver que pasa lo mismo en Clock (__new__ o irá en __init__?)

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
    pass # TODO


# class OneShotStream(Stream): pass # TODO: ver para qué sirve, la única referencia está en Object:iter, no está documentada.
# class EmbedOnce(Stream): pass # TODO, ver, solo se usa en JITLib, no está documentada.
# class StreamClutch(Stream): pass # TODO: no se usa en la librería de clases, actúa como un filtro, sí está documentada.
# class CleanupStream(Stream): pass # TODO: no se usa en la librería de clases, creo, ver bien, no tiene documentación.


# // PauseStream is a stream wrapper that can be started and stopped.
class PauseStream(Stream):
    def __init__(self, stream, clock=None):
        self._stream = None
        self.original_stream = stream
        self.clock = clock or clk.TempoClock.default # BUG: implementar TempoClock
        self.next_beat = None
        self.stream_has_ended = False
        self.waiting = False # NOTE: era isWaiting, así es más pytónico.
        self.era = 0

    def playing(self): # NOTE: era isPlaying, así es más pytónico.
        return self._stream is not None

    def play(self, clock=None, reset=False, quant=None):
        if self._stream is not None:
            print('already playing')
            return # NOTE: sclang retorna self, esto es un comportamiento global de la librería que habría que ver, pero creo que no es muy Python.
        if reset:
            self.reset()
        self.clock = clock or self.clock or clk.TempoClock.default
        self.stream_has_ended = False
        self.refresh() # //_stream = originalStream;
        self._stream.clock = self.clock
        self.waiting = True # // make sure that accidental play/stop/play sequences don't cause memory leaks
        print('*** stream.py PauseStream.play: implementar CmdPeriod')
        self.era = 0 # xxx.CmdPeriod.era # BUG: implementar

        def pause_stream_play(*args): # BUG: DECIDIR checkeo de argumentos en wakeup: TypeError: pause_stream_play() takes 0 positional arguments but 3 were given
            if self.waiting and self.next_beat is None:
                self.clock.sched(0, self)
                self.waiting = False
                mdl.NotificationCenter.notify(self, 'playing')

        print('*** stream.py PauseStream.play: implementar Quant para TempoClock y que sea parámetro opcional acá o en Clock y Scheduler')
        self.clock.play(pause_stream_play) #, quant or xxx.Quant()) # NOTE: usa asQuant, nil.asQuant es Quant(0), no lo voy a implementar, pasar Quant o que la implementación se equivalente con tupla
        mdl.NotificationCenter.notify(self, 'user_played')

    def reset(self):
        self.original_stream.reset()

    def stop(self):
        save_stream = self.stream # NOTE: usa el getter
        self._stop()
        mdl.NotificationCenter.notify(self, 'user_stopped')
        if save_stream is _main.Main.current_TimeThread:
            self.always_yield()

    def _stop(self):
        self._stream = None
        self.waiting = False

    def removed_from_scheduler(self): # NOTE: removeD?
        self.next_beat = None
        self._stop()
        mdl.NotificationCenter.notify(self, 'stopped')

    def stream_error(self):
        self.removed_from_scheduler()
        self.stream_has_ended = True

    def was_stopped(self):
        return ((self.stream_has_ended and self._stream is None) # // stopped by clock or stop-message
               or xxx.CmdPeriod.era != self.era) # // stopped by cmd-period, after stream has ended

    def can_pause(self):
        return not self.stream_has_ended

    def pause(self):
        self.stop()

    def resume(self, clock=None, quant=None):
        self.play(clock or self.clock, False, quant) # BUG: en sclang está al revés el or y no tiene lógica porque puede pasar nil

    def refresh(self):
        self.original_stream.thread_player = self # NOTE: threadPlayer en sclang lo definen Object (siempre es this, no se puede setear, esta clase redunda en lo mismo) y Thread (que cambia), acá lo define TimeThread como property y agrego la propiedad acá, es problema esto.
        self._stream = self.original_stream # NOTE: va por separado porque en sclang method_(lala) devuelve this

    def start(self, clock=None, quant=None):
        self.play(clock, True, quant)

    def next(self, inval=None):
        try:
            if self._stream is None: # NOTE: self._stream puede ser nil por el check de abajo o tirar la excepción si finalizó, por eso se necesita esta comprobación, acá los stream no retornan None, tiran excepción.
                raise StopStream('_stream is None')
            next_time = self._stream.next(inval)
            self.next_beat = inval + next_time # // inval is current logical beat
            return next_time
        except StopStream as e:
            self.stream_has_ended = self._stream is not None
            self.removed_from_scheduler()
            raise StopStream('stream finished') from e # BUG: tal vez deba descartar e? (no hacer raise from o poner raise fuera de try/except)

    def awake(self, beats, seconds, clock): # *** NOTE: llama Scheduler wakeup, único caso acá, existe para esto y también se llama desde la implementación en C/C++.
        self._stream.beats = beats
        return self.next(beats)

    @property
    def stream(self):
        return self._stream

    @stream.setter
    def stream(self, value): # NOTE: OJO: No usa este setter en la implementación interna
        self.original_stream.thread_player = None # // not owned any more
        value.thread_player = self
        self.original_stream = value.thread_player
        if self._stream is not None:
            self._stream = value
            self.stream_has_ended = value is not None

    @property
    def thread_player(self):
        return self

    @thread_player.setter
    def thread_player(self, value):
        pass # NOTE: siempre es this para esta clase en sclang, el método se hereda de object y no se puede setear.


# // Task is a PauseStream for wrapping a Routine
class Task(PauseStream):
    def __init__(self, func, clock=None):
        super().__init__(thr.Routine(func), clock) # BUG: qué pasa si func llega a ser una rutina? qué error tira?

    # storeArgs # TODO: ver en general para la librería


# decorator syntax
def task(func, clock=None):
    return Task(func, clock)


class EventStreamPlayer(PauseStream):
    pass


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
