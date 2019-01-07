"""SynthDesc.sc"""

import io


class IODesc():
    def __init__(self, rate, num_channels, starting_channel, type):
        self.rate = rate
        self.num_channels = num_channels
        self.starting_channel = starting_channel or '?'
        self.type = type

    def print_on(self, stream: io.StringIO):
        txt = str(self.rate) + ' ' + self.type.name + ' '\
              + self.starting_channel + ' ' + self.num_channels
        stream.write(txt)


class SynthDesc():
    md_plugin = TextArchiveMDPlugin # // override in your startup file
    populate_metadata_func = None

    def __init__(self):
        self.name = None
        self.control_names = None
        self.control_dict = None
        self.controls = None
        self.inputs = None
        self.outputs = None
        self.metadata = None

        self.constants = None
        self.def = None
        self.msg_func = None
        self.has_gate = False
        self.has_array_args = None
        self.has_variants = None
        self.can_free_synth = False
        self.msg_func_keep_gate = False # TODO: solo tiene getter.

    @classmethod
    def new_from(cls, synthdef): # TODO: ver estos métodos constructores en general, posiblemente sea mejor llamar a __new__ con argumentos.
        return synthdef.as_synth_dec()

    def send(self, server, completion_msg):
        self.def.send(server, completion_msg) # parece ser una instancia de SynthDef

    def print_on(self, stream: io.StringIO):
        txt = "SynthDesc '" + self.name + "'\nControls:\n"
        stream.write(txt)
        for control in self.controls:
            control.print_on(stream)
            stream.write('\n')
        for input in self.inputs:
            stream.write('    I ')
            input.print_on(stream)
            stream.write('\n')
        for output in self.outputs:
            stream.write('    O ')
            output.print_on(stream)
            stream.write('\n')

    # TODO: sigue...


class SynthDescLib():
    all = dict()
    glob = SynthDescLib('global')
    # // tryToLoadReconstructedDefs = false:
    # // since this is done automatically, w/o user action,
    # // it should not try to do things that will cause warnings
    # // (or errors, if one of the servers is not local)
    ServerBoot.add(lambda server: ServerDescLib.send(server, False)) # BUG: depende del orden de los imports # this.send(server, false) # this es la clase.

    def __new__(cls):
        pass

    def __init__(self):
        pass

    @classmethod
    def get_lib(cls, libname):
        pass

    @classmethod
    def default(cls):
        return cls.glob

    @classmethod
    def send(cls, server, try_reconstructed=True):
        pass


# TODO: Estas clases están ligadas a la arquitectura de Object en sclang.
# Tengo que ver con qué recursos de Python representarlas.
#
# // Basic metadata plugins
#
# // to disable metadata read/write
class AbstractMDPlugin():
    pass


# // simple archiving of the dictionary
class TextArchiveMDPlugin(AbstractMDPlugin):
    pass
