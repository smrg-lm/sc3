"""Kernel.sc y Main.sc"""

import threading
import atexit
import time

from . import clock as clk
from . import thread as thr


# Kernel.sc
class Process(type):
    # classVars, <interpreter, schedulerQueue, <>nowExecutingPath TODO: ver luego si alguna sirve para la interfaz de Python
    # current_TimeThread = None; main_TimeThread = None

    def __init__(cls, name, bases, dict):
        # clk.SystemClock() # BUG; PASADA ABAJO DEL MÓDULO PARA PROBAR. Main y Main._main_lock tiene que definirse antes
        cls._time_of_initialization = time.time()
        cls.main_TimeThread = thr.TimeThread.singleton() # el reloj en el que corre Process sería AppClock es un threading.Thread con un modelo diferente de programación de eventos, pero la verdad es que no estoy seguro.
        cls.current_TimeThread = cls.main_TimeThread
        cls._main_lock = threading.Condition()
        atexit.register(cls.shutdown)

    # def _create_mtt_func(cls):
    #     def func():
    #         cls._run_thread = True
    #         while True:
    #             while cls._system_queue.empty():
    #                 with cls._main_lock:
    #                     cls._main_lock.wait()
    #                 if not cls._run_thread:
    #                     return
    #
    #             while not cls._system_queue.empty():
    #                 item = cls._system_queue.get()
    #     return func

    # TODO: ver y agregar los comentarios en el código original
    def startup(cls):
        pass
    def run(cls):
        pass
    def stop(cls):
        pass
    def shutdown(cls):
        pass
        # TODO: VER: PyrLexer shutdownLibrary, ahí llama sched_stop de SystemClock (acá) y TempoClock stop all entre otras cosas.
        # TODO: sched_stop tiene join, no se puede usasr con atexit?
        #cls._run_thread = False
        # BUG: no me acuerdo cuál era el problema con atexit y los locks, una solución es demonizarlas.
        # with cls._main_lock:
        #     cls._main_lock.notify_all()
        #cls._thread.join()
        # BUG: probablemente tenga que hacer lo mismo con todos los relojes.
    def tick(cls):
        pass

    # *elapsedTime _ElapsedTime
    def elapsed_time(cls) -> float: # devuelve el tiempo del reloj de mayor precisión menos _time_of_initialization
        return time.time() - cls._time_of_initialization

    # *monotonicClockTime _monotonicClockTime
    def monotonic_clock_time(cls) -> float: # monotonic_clock::now().time_since_epoch(), no sé dónde usa esto
        return time.monotonic() # en linux es hdclock es time.perf_counter(), no se usa la variable que declara

# Main.sc
class Main(metaclass=Process):
    # TODO: REVISAR: Process (__init__) se instancia en Main cuando se compila la clase (en el primer import, supongo)
    # BUG: Al ser una librería esto es debatible...
    pass

# BUG: TEST, luego va a ser necesario organizar todo
clk.SystemClock()
