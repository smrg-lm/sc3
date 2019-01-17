"""SystemActions.sc"""

# TODO: AbstractSystemAction -> AbstractServerAction -> ServerBoot


class AbstractSystemAction():
    pass


# // things to clear when hitting cmd-.
class CmdPeriod(AbstractSystemAction):
    pass


# // things to do after startup file executed
class StartUp(AbstractSystemAction):
    pass


# // things to do before system shuts down
class ShutDown(AbstractSystemAction):
    pass


# // things to do on a system reset
class OnError(AbstractSystemAction):
    pass


class AbstractServerAction(AbstractSystemAction):
    pass


# // things to do after server has booted
class ServerBoot(AbstractServerAction):
    @classmethod
    def add(cls, obj=None, server=None): # BUG: Ver por qué 'object', es una función en SynthDescLib
        pass # BUG: función vacía para TEST, no se define acá.


# // things to do after server has quit
class ServerQuit(AbstractServerAction):
    pass


# // things to do after server has booted and initialised
class ServerTree(AbstractServerAction):
    pass
