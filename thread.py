"""Thread.sc"""

# TODO: ver https://www.python.org/dev/peps/pep-0492/
# TODO: ver https://www.python.org/dev/peps/pep-0342/
# TODO: ver https://www.python.org/dev/peps/pep-0380/
# TODO: ver https://www.python.org/dev/peps/pep-0550/
# TODO: ver https://www.python.org/dev/peps/pep-0567/
# aunque son para Python 3.7 en relación a asyncio
# TODO: ver https://stackoverflow.com/questions/750702/retrieving-printing-execution-context
# ^ CREO QUE NINGUNO DE ESOS RECURSOS ME SIRVE ^

# TODO: Process y Main (juntas o por separado, o solo Process) serían
# TODO: el entorno de ejecusión de SuperCollider dentro de Python.
# TODO: Probablemente sea lo mejor usar Process/Main para el manejo
# TODO: de los Threads como controlador global. No sé si no lo mismo
# TODO: con las cosas de synthdef en _global.py. Process es un nombre
# TODO: acertado para esto, en vez de Client, que sería oscclient o
# TODO: parte de la implementación de Process. SCLang hace muchas cosas
# TODO: distintas específicas del lenguaje que acá no son necesarias.

import enum
import inspect


class TimeThread(): #(Stream): # BUG: hereda de Stream por Routine y no la usa, pero acá puede haber herencia múltiple. Además, me puse poético con el nombre.
    # ./lang/LangSource/PyrKernel.h: enum { tInit, tStart, tReady, tRunning, tSleeping, tSuspended, tDone };
    # ./lang/LangSource/PyrKernel.h: struct PyrThread : public PyrObjectHdr
    State = enum.Enum('State', [
        'Init', 'Start', 'Ready', 'Running',
        'Sleeping', 'Suspended', 'Done'
    ])
    #_EVAL_STACK_DEPTH = 512 # PyrKernel.h # BUG

    def __init__(self, func): #, stack_size=512): # BUG: no se si puedo manejar stack_size o si sea realmente conveniente
        # _Thread_Init -> prThreadInit -> initPyrThread
        if not inspect.isfunction(func):
            raise TypeError('Thread function arg is not a function')

        # BUG: ver test_clock_thread.scd, estos valores no tienen efecto porque
        # se sobreescribe el reloj por TempoClock.default en Stream:play
        # y Routine:run vuelve a escribir SystemClock (cuando ya lo hizo en
        # PyrPrimitive). La única manera de usar el reloj heredado es llamando a next.
        self.beats = current_TimeThread.beats # BUG: no se de dónde sacar parent, PyrPrimitive usa &g->thread->beats, BUG: PERO NUNCA SETEA ESA PROPIEDAD! si pasarlo como argumento o como una propiedad current_thread de la clase
        self.seconds = current_TimeThread.seconds # BUG: creo que tienen setters porque son dependientes...

        self.func = func
        #setl.stack = [0] * max(stack_size, self._EVAL_STACK_DEPTH) # BUG
        self.state = self.State.Init
        #ip y sp son stackpointers a cero # BUG
        self.rand_data = current_TimeThread.rand_data[:] # rgenArray -> PyrInt32Array

        if current_TimeThread.clock is None:
            self.clock = xxx.SystemClock
        else:
            self.clock = current_TimeThread.clock # hace slotCopy y lo registra en GC, puede que solo esté marcando una referencia más, más arriba a GCWriteNew con el array de la pila que es nuevo

        # NOTA: No guarda la propiedad <parent cuando crea el thread, es
        # &g->thread que la usa para setear beats y seconds pero no la guarda,
        # la setea luego en algún lugar, con el cambio de contexto, supongo,
        # y tiene valor solo mientras la rutina está en ejecusión. Ver test_clock_thread.scd
        self.environment = current_Environment # BUG: acá llama al slot currentEnvironment de Object y lo setea al del hilo
        # BUG: acá setea nowExecutingPath de la instancia de Process (Main) si es que no la estamos creando con este hilo.
        # if(g->process) { // check we're not just starting up
    	# 	slotCopy(&thread->executingPath,&g->process->nowExecutingPath);

        #self.stack_size = stack_size # BUG: stack_size se lo guarda en la struct de C pero no en la clase de sclang, no existe en sclang

#
