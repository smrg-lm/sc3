"""Thread.sc"""

# TODO: ver https://www.python.org/dev/peps/pep-0492/
# TODO: ver https://www.python.org/dev/peps/pep-0342/
# TODO: ver https://www.python.org/dev/peps/pep-0380/
# TODO: ver https://www.python.org/dev/peps/pep-0550/
# TODO: ver https://www.python.org/dev/peps/pep-0567/
# aunque son para Python 3.7 en relación a asyncio
# TODO: ver https://stackoverflow.com/questions/750702/retrieving-printing-execution-context
# ^ CREO QUE NINGUNO DE ESOS RECURSOS ME SIRVE ^

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

        self.beats = current_TimeThread.beats # BUG: no se de dónde sacar parent, si pasarlo como argumento o como una propiedad current_thread de la clase
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

        self.environment = current_Environment # BUG: acá llama al slot currentEnvironment de Object y lo setea al del hilo
        # BUG: acá setea nowExecutingPath de la instancia de Process (Main) si es que no la estamos creando con este hilo.
        # if(g->process) { // check we're not just starting up
    	# 	slotCopy(&thread->executingPath,&g->process->nowExecutingPath);

        #self.stack_size = stack_size # BUG: stack_size se lo guarda en la struct de C pero no en la clase de sclang, no existe en sclang

#
