"""Kernel.sc y Main.sc"""

from . import clock as clk
from . import thread as thr


# Kernel.sc
class Process(type):
    # classVars, <interpreter, schedulerQueue, <>nowExecutingPath TODO: ver luego si alguna sirve para la interfaz de Python
    # current_TimeThread = None; main_TimeThread = None

    def __init__(cls, name, bases, dict):
        clk.SystemClock()
        cls.main_TimeThread = thr.TimeThread.singleton()
        cls.current_TimeThread = cls.main_TimeThread

# Main.sc
class Main(metaclass=Process):
    # TODO: REVISAR: Process (__init__) se instancia en Main cuando se compila la clase (en el primer import, supongo)
    # BUG: Al ser una librería esto es debatible...
    pass
