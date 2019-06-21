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
import random

from . import server as srv
from . import stream as stm
from . import oscserver as osr
from . import responsedefs as rdf
from . import utils as utl


class TimeException(ValueError):
    pass


# Kernel.sc
class Process(type):
    # classVars, <interpreter, schedulerQueue, <>nowExecutingPath TODO: ver luego si alguna sirve para la interfaz de Python
    # current_TimeThread = None; main_TimeThread = None

    def __init__(cls, name, bases, dict):
        cls._time_of_initialization = time.time()
        cls._main_lock = threading.Condition() # ver, pasada desde abajo

        cls._create_main_thread()

        cls.osc_server = osr.OSCServer() # BUG: options, y ver si se pueden crear más servidores, ver abajo
        cls.osc_server.start()

        atexit.register(cls.shutdown)

    def _create_main_thread(cls):
        # init main time thread # NOTE: ver PyrInterpreter3 L157 newPyrProcess y PyrPrimitive initPyrThread
        cls.main_TimeThread = stm.TimeThread.__new__(stm.TimeThread)
        cls.main_TimeThread.parent = None
        cls.main_TimeThread.func = None
        cls.main_TimeThread.state = stm.TimeThread.State.Init
        cls.main_TimeThread._thread_player = None
        cls.main_TimeThread._beats = 0.0 # NOTE: se inicializan en la declaración de la clase en sclang, sirven solo para mainThread las rutinas llama a _InitThread.
        cls.main_TimeThread._seconds = 0.0
        cls.main_TimeThread._rand_state = random.getstate() # BUG: ver, inicializa el estado con ./lang/LangPrimSource/PyrUnixPrim.cpp:int32 timeseed() en newPyrProcess
        # NOTE: cls.main_TimeThread.clock siempre es SystemClock y no se puede setear (no tiene efecto).
        cls.current_TimeThread = cls.main_TimeThread

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
    def tick(cls): # BUG: este tick? Creo que es algo que no se usa más y quedó de la vieja implementación en sclang.
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
        '''Physical time since library initialization.'''
        return time.time() - cls._time_of_initialization

    # *monotonicClockTime _monotonicClockTime
    def monotonic_clock_time(cls) -> float: # monotonic_clock::now().time_since_epoch(), no sé dónde usa esto
        return time.monotonic() # en linux es hdclock es time.perf_counter(), no se usa la variable que declara

    def update_logical_time(cls, seconds=None):
        # NOTE: En la documentación de Thread dice:
        # // When code is run from the code editor, the command line, or in
        # // response to OSC and MIDI messages, the main Thread's logical
        # // time is set to the current physical time (see Process: *elapsedTime).
        # // When code scheduled on a Clock is run, the main Thread's
        # // logical time is set to the time the code was scheduled for.
        # // Child Threads inherit logical time from their parents
        # // - whenever a Thread (Routine) is started or resumed, its
        # // logical time is set to that of the parent Thread.
        # NOTE: Esta es una función de interfaz interna de la librería que
        # NOTE: intenta ser general aunque sería menos eficiente para los relojes.
        now = cls.elapsed_time()
        if seconds is None:
            #if cls.current_TimeThread is cls.main_TimeThread: # NOTE: Dejo el check en Clock. NOTE: Esto actualiza cada vez que SystemClock y AppClock se consultan desde main_TimeThread. (BUG) La misma lógica también cuando se usa también cuando llegan mensajes OSC, MIDI o HID.
            cls.main_TimeThread.seconds = now # *logical time* is set to *physical time*
        elif seconds > now:
            raise TimeException(
                "logical time can't be set in the future of physical time")
        else:
            #print('*** seconds, now & diff:', [seconds, now, now - seconds]) # NOTE: otra medida sería cuándo el tiempo de retraso es perceptible en tiempo real...
            cls.main_TimeThread.seconds = seconds


# Main.sc
class Main(metaclass=Process):
    # TODO: REVISAR: Process (__init__) se instancia en Main cuando se compila la clase (en el primer import, supongo)
    # BUG: Al ser una librería esto es debatible...
    pass


utl.ClassLibrary.init()
