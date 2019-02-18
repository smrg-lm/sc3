"""Kernel.sc y Main.sc

En sclang existen LanguageConfig, w/r archivos yaml. Las opciones sclang -h.
Sclang Startup File. La clase Main que hereda de Process. Las clases que
heredan de AbstractSystemAction: StartUp, ShutDown, ServerBoot, ServerTree,
CmdPeriod y seguramente otras más.

Y MAIN, CLIENT PODDRÍA SER UN MIEMBRO DE MAIN QUE ADEMÁS TIENE PLATFORM!

VER DOCUMENTACIÓN: 'OSC COMMUNICATION'

pickle PUEDE SER ÚTIL para guardar la instancia de client y que se
puedan ejecutar distintas instancias de python con el mismo cliente
sin tener que tener las sesiones andando en paralelo, e.g. para ejecutar
scripst por separado desde la terminal.
"""

import threading
import atexit
import time

from . import server as srv
from . import clock as clk
from . import thread as thr
from . import oscserver as osr
from . import responsedefs as rdf


# Kernel.sc
class Process(type):
    # classVars, <interpreter, schedulerQueue, <>nowExecutingPath TODO: ver luego si alguna sirve para la interfaz de Python
    # current_TimeThread = None; main_TimeThread = None

    def __init__(cls, name, bases, dict):
        # clk.SystemClock() # BUG; PASADA ABAJO DEL MÓDULO PARA PROBAR. Main y Main._main_lock tiene que definirse antes
        cls._time_of_initialization = time.time()
        cls._main_lock = threading.Condition() # ver, pasada desde abajo

        cls.main_TimeThread = thr.TimeThread.singleton() # el reloj en el que corre Process sería AppClock es un threading.Thread con un modelo diferente de programación de eventos, pero la verdad es que no estoy seguro.
        cls.current_TimeThread = cls.main_TimeThread

        cls.osc_server = osr.OSCServer() # BUG: options, y ver si se pueden crear más servidores, ver abajo
        cls.osc_server.start()

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
    def tick(cls): # BUG: este tick?
        pass


    # BUG: en sclang hay un solo servidor osc que abre varios puertos
    # acá se puede hacer un servidor por puerto con distinto protocolo,
    # que es algo que sclang maneja desde NetAddr. Tengo que ver.
    # def open_osc_port(cls, port, protocol=osr.DEFAULT_CLIENT_PROTOCOL):
    #     self._osc_servers.append(osr.OSCServer(port, protocol))
    # def open_ports

    def add_osc_recv_func(cls, func):
        cls.osc_server.add_recv_func(func)

    def remove_osc_recv_func(cls, func):
        cls.osc_server.remove_recv_func(func)

    # por lo que hace es redundante
    # def replace_osc_recv_func(cls, func):
    #     cls.osc_server.replace_recv_func(func)


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
clk.AppClock()
