"""Kernel.sc & Main.sc"""

import threading
import atexit
import time
import random
import sys

from ..synth import server as srv
from ..seq import stream as stm
from ..seq import clock as clk
from . import _oscinterface as osci
from . import responsedefs as rdf
from . import utils as utl
from . import platform as plf


class TimeException(ValueError):
    pass


### Kernel.sc ###


class Process(type):
    # classVars, <interpreter, schedulerQueue, <>nowExecutingPath TODO: ver luego si alguna sirve para la interfaz de Python
    # current_tt = None; main_tt = None

    RT = 0
    NRT = 1

    def __init__(cls, name, bases, dict):
        cls._main_lock = threading.RLock()
        cls._switch_cond = threading.Condition(cls._main_lock)
        cls._mode = None
        cls._rgen = random.Random()
        cls._init_platform()
        atexit.register(cls.shutdown)

    def _init_platform(cls):
        if sys.platform.startswith('linux'):
            cls._platform = plf.LinuxPlatform()
        elif sys.platform.startswith('darwin'):
            cls._platform = plf.DarwinPlatform()
        elif sys.platform.startswith('win32'):
            cls._platform = plf.Win32Platform()
        elif sys.platform.startswith('cygwin'):
            cls._platform = plf.CygwinPlatform()
        else:
            raise RuntimeError('platform not defined')
        cls._platform._startup()

    def _init_rt(cls):
        # NOTE: In sclang these two are the same clock, it obtains
        # time_since_epoch for gHostStartNanos =
        # duration_cast<nanoseconds>(hrTimeOfInitialization.time_since_epoch()).count()
        # I think is not important for these reference points to be sampled at
        # the same time because main.elapsed_time() == 0 is in logic relation
        # to main._rt_time_of_initialization. Comment to be removed later if true.
        cls._rt_time_of_initialization = time.time()  # time_since_epoch
        cls._rt_perf_counter_time_of_initialization = time.perf_counter()  # monotonic clock.
        cls._create_main_thread('rt')
        cls.osc_server = osci.LOInterface()
        cls.osc_server.start()

    def _init_nrt(cls):
        cls._nrt_time_of_initialization = 0.0
        cls._create_main_thread('nrt')
        cls._clock_scheduler = clk.ClockScheduler()

    def _create_main_thread(cls, prefix):
        # init main time thread # NOTE: ver PyrInterpreter3 L157 newPyrProcess y PyrPrimitive initPyrThread
        main_tt = stm.TimeThread.__new__(stm.TimeThread)
        main_tt.parent = None
        main_tt.func = None
        main_tt.state = stm.TimeThread.State.Init
        main_tt._thread_player = None
        main_tt._beats = 0.0 # NOTE: se inicializan en la declaración de la clase en sclang, sirven solo para mainThread las rutinas llama a _InitThread.
        main_tt._seconds = 0.0
        main_tt._rgen = cls._rgen

        main_vname = '_' + prefix + '_main_tt'
        curr_vname = '_' + prefix + '_current_tt'
        setattr(cls, main_vname, main_tt)
        setattr(cls, curr_vname, getattr(cls, main_vname)) # NOTE: un solo lock, no pueden existir en paralelo en distintos hilos.

    def rt(cls):
        '''Sets the library in rt mode.'''
        if not hasattr(cls, '_rt_time_of_initialization'):
            cls._init_rt()
        with cls._switch_cond:
            cls._time_of_initialization = cls._rt_time_of_initialization
            cls.main_tt = cls._rt_main_tt
            cls.current_tt = cls.main_tt
            setattr(cls, 'elapsed_time', cls._rt_elapsed_time)
            setattr(cls, 'update_logical_time', cls._rt_update_logical_time)
            cls._mode = cls.RT

    def nrt(cls):
        '''Sets the library in nrt mode.'''
        print('*** bug: nrt no va a funcionar con las clases que llaman a SystemClock directamente, por ejemplo Event.')
        if not hasattr(cls, '_nrt_time_of_initialization'):
            cls._init_nrt()
        with cls._switch_cond:
            cls._time_of_initialization = cls._nrt_time_of_initialization
            cls.main_tt = cls._nrt_main_tt
            cls.current_tt = cls.main_tt # *** BUG: ver qué pasa si no se resetea.
            setattr(cls, 'elapsed_time', cls._nrt_elapsed_time)
            setattr(cls, 'update_logical_time', cls._nrt_update_logical_time)
            cls._mode = cls.NRT

    @property
    def mode(cls):
        return cls._mode

    @property
    def rgen(cls):
        return cls.current_tt.rgen

    @property
    def platform(cls):
        return cls._platform

    # TODO: ver y agregar los comentarios en el código original
    def startup(cls):
        pass

    def run(cls):
        pass

    def stop(cls):
        pass

    def shutdown(cls):
        cls.platform._shutdown()
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
    #     cls._osc_servers.append(osr.OSCServer(port, protocol))
    # def open_ports

    def add_osc_recv_func(cls, func):
        cls.osc_server.add_recv_func(func)

    def remove_osc_recv_func(cls, func):
        cls.osc_server.remove_recv_func(func)

    # por lo que hace es redundante
    # def replace_osc_recv_func(cls, func):
    #     cls.osc_server.replace_recv_func(func)

    # *elapsedTime _ElapsedTime
    def _rt_elapsed_time(cls) -> float: # devuelve el tiempo del reloj de mayor precisión menos _time_of_initialization
        '''Physical time since library initialization.'''
        return time.perf_counter() - cls._rt_perf_counter_time_of_initialization

    def _nrt_elapsed_time(cls) -> float:
        '''Physical time is main_Thread.seconds in nrt.'''
        return float(cls.main_tt.seconds)

    # *monotonicClockTime _monotonicClockTime
    def monotonic_clock_time(cls) -> float: # monotonic_clock::now().time_since_epoch(), no sé dónde usa esto
        return time.monotonic() # en linux es hdclock es time.perf_counter(), no se usa la variable que declara

    def _rt_update_logical_time(cls, seconds=None):
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
            #if cls.current_tt is cls.main_tt: # NOTE: Dejo el check en Clock. NOTE: Esto actualiza cada vez que SystemClock y AppClock se consultan desde main_tt. (BUG) La misma lógica también cuando se usa también cuando llegan mensajes OSC, MIDI o HID.
            cls.main_tt.seconds = now # *logical time* is set to *physical time*
        elif seconds > now:
            raise TimeException(
                "logical time can't be set in the future of physical time")
        else:
            #print('*** seconds, now & diff:', [seconds, now, now - seconds]) # NOTE: otra medida sería cuándo el tiempo de retraso es perceptible en tiempo real...
            cls.main_tt.seconds = seconds

    def _nrt_update_logical_time(cls, seconds=None):
        if seconds is None:
            return
        else:
            cls.main_tt.seconds = seconds


### Main.sc ###


class main(metaclass=Process):
    pass


main.rt()
utl.ClassLibrary.init()
