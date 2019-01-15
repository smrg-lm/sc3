"""SynthDesc.sc"""

import io
import glob # import pathlib.Path no es necesario, sclang usa glob
import struct
import warnings

import supercollie._global as _gl
import supercollie.synthdef as sd # BUG: cíclico
import supercollie.inout as scio
import supercollie.utils as ut
import supercollie.ugens as ug


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
        self.sdef = None
        self.msg_func = None
        self.has_gate = False
        self.has_array_args = None
        self.has_variants = None
        self.can_free_synth = False
        self._msg_func_keep_gate = False # @property

    @classmethod
    def new_from(cls, synthdef): # TODO: ver estos métodos constructores en general, posiblemente sea mejor llamar a __new__ con argumentos.
        return synthdef.as_synth_dec()

    def send(self, server): #, completion_msg): # BUG: ver completion_msg que no se usa o recibe. Tal vez tenga que mirar a más bajo nivel, pero las funciones send_msg/bundle osc no tienen esa lógica.
        self.sdef.send(server) #, completion_msg) # parece ser una instancia de SynthDef

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

    # // don't use *read or *readFile to read into a SynthDescLib. Use SynthDescLib:read or SynthDescLib:readStream instead
    @classmethod
    def read(cls, path, keep_defs=False, dictionary=None):
        dictionary = dictionary or dict()
        for filename in glob.glob(path):
            with open(filename, 'rb') as file:
                dictionary = cls._read_file(file, keep_defs, dictionary)
        return dictionary

    # // path is for metadata -- only this method has direct access to the new SynthDesc
    @classmethod
    def _read_file(cls, stream, keep_defs=False, dictionary=None, path=None):
        stream.read(4) # getInt32 // SCgf # TODO: la verdad que podría comprobar que fuera un archivo válido.
        version = struct.unpack('>i', file.read(4))[0] # getInt32
        num_defs = struct.unpack('>h', file.read(2))[0] # getInt16
        for _ in num_def:
            if version >= 2:
                desc = SynthDesc()
                desc.read_synthdef2(stream, keep_defs)
            else:
                desc = SynthDesc()
                desc.read_synthdef(stream, keep_defs)
            dictionary[desc.name] = desc
            # // AbstractMDPlugin dynamically determines the md archive type
            # // from the file extension
            if path:
                desc.metadata = AbstractMDPlugin.read_metadata(path)
            cls.populate_metadata_func(desc)
            in_memory_stream = isinstance(stream, io.BytesIO) # TODO: entiendo que es sl significado de { stream.isKindOf(CollStream).not }: de la condición de abajo, porque expresión no explica la intención. Supongo que refiere a que no sea un stream en memoria sino un archivo del disco. En Python los streams en memoria son StringIO y BytesIO. TextIOWrapper y BufferReader se usa para archivos y son hermanas de aquellas en la jerarquía de clases, por lo tanto debería funcionar.
            if desc.sdef is not None and not in_memory_stream:
                if desc.sdef.metadata is None:
                    desc.sdef.metadata = dict()
                desc.sdef.metadata['shouldNotSend'] = True # BUG/TODO: los nombres en metadata tienen que coincidir con las convenciones de sclang... (?)
                desc.sdef.metadata['loadPath'] = path
        return dictionary

    def read_synthdef(self, stream, keep_def=False): # TODO
        raise NotImplementedError('read_synthdef format version 1 not implemented')

    # // synthdef ver 2
    def read_synthdef2(self, stream, keep_def=False):
        with _gl.def_build_lock:
            try:
                self.inputs = []
                self.outputs = []
                self.control_names = []
                self.control_dict = dict()

                aux_str_len = struct.unpack('B', stream.read(1))[0] # getPascalString 01
                aux_string = stream.read(aux_str_len) # getPascalString 02
                self.name = str(aux_string, 'ascii') # getPascalString 03

                self.sdef = sd.SynthDef.dummy() # BUG: es dummy y se va llenando acá pero no se puede llamar a __init__ porque este llama a _build
                _gl.current_synthdef = self.sdef

                num_constants = struct.unpack('>i', stream.read(4))[0] # getInt32
                aux_f = stream.read(num_constants * 4) # read FloatArray 01
                aux_f = struct.unpack('>' + 'f' * num_constants, aux_f) # read FloatArray 02
                self.constants = list(aux_f) # read FloatArray 03

                num_controls = struct.unpack('>i', stream.read(4))[0] # getInt32
                aux_f = stream.read(num_controls * 4) # read FloatArray 01
                aux_f = struct.unpack('>' + 'f' * num_controls, aux_f) # read FloatArray 02
                self.sdef.controls = list(aux_f) # read FloatArray 03
                self.controls = [
                    scio.ControlName('?', i, '?', self.sdef.controls[i], None)\
                    for i in range(num_controls)]

                num_control_names = struct.unpack('>i', stream.read(4))[0] # getInt32
                for _ in range(num_control_names):
                    aux_str_len = struct.unpack('B', stream.read(1))[0] # getPascalString 01
                    aux_string = stream.read(aux_str_len) # getPascalString 02
                    control_name = str(aux_string, 'ascii') # getPascalString 03
                    control_index = struct.unpack('>i', stream.read(4))[0] # getInt32
                    self.controls[control_index].name = control_name
                    self.control_names.append(control_name)
                    self.control_dict[control_name] = self.controls[control_index]

                num_ugens = struct.unpack('>i', stream.read(4))[0] # getInt32
                for _ in range(num_ugens):
                    self.read_ugen_spec2(stream)

                #self.controls # BUG: controls.inject(nil) { arg x, y; ... } asume que el primer y.name no va a ser '?' para que no llame a z.defaultValue, no entiendo por qué.
                aux_ctrl = None
                for ctrl in self.controls:
                    if ctrl.name == '?':
                        default_value = ut.as_list(aux_ctrl.default_value)
                        default_value.append(ctrl.default_value)
                        aux_ctrl.default_value = default_value
                    else:
                        aux_ctrl = ctrl
                # end of BUG: inject(nil), revisar

                self.sdef.control_names = [x for x in self.controls if x.name] # select x.name.notNil
                self.has_array_args = any(cn.name == '?' for cn in self.controls)

                num_variants = struct.unpack('>h', stream.read(2))[0] # getInt16
                self.has_variants = num_variants > 0
                # // maybe later, read in variant names and values
                # // this is harder than it might seem at first

                self.sdef.constants = dict()
                for i, k in enumerate(self.constants):
                    self.sdef.constants[k] = i

                if not keep_def:
                    # // throw away unneeded stuff
                    self.sdef = None
                    self.constats = None

                self.make_msg_func()
            finally:
                _gl.current_synthdef = None

    def read_ugen_spec(self, stream): # TODO
        raise NotImplementedError('read_ugen_spec format version 1 not implemented')

    # // synthdef ver 2
    def read_ugen_spec2(self, stream):
        aux_str_len = struct.unpack('B', stream.read(1))[0] # getPascalString 01
        aux_string = stream.read(aux_str_len) # getPascalString 02
        ugen_class = str(aux_string, 'ascii') # getPascalString 03
        try:
            ugen_class = eval(ugen_class) # globals=None, locals=None) BUG: falta el contexto en el cuál buscar
        except NameError as e:
            msg = 'no UGen class found for {} which was specified in synth def file: {}'
            raise Exception(msg.format(ugen_class, self.name)) from e

        rate_index = struct.unpack('b', stream.read(1))[0] # getInt8
        num_inputs = struct.unpack('>i', stream.read(4))[0] # getInt32
        num_outputs = struct.unpack('>i', stream.read(4))[0] # getInt32
        special_index = struct.unpack('>h', stream.read(2))[0] # getInt16

        aux_i32 = stream.read(num_inputs * 4 * 2) # read Int32Array 01 # nota: write_input_spec escribe synth_index y output_index como int32
        aux_i32 = struct.unpack('>' + 'i' * (num_inputs * 2), aux_i32) # read Int32Array 02
        input_specs = list(aux_i32) # read Int32Array 03

        aux_i8 = stream.read(num_outputs) # read Int8Array 01
        aux_i8 = struct.unpack('b' * num_outpus, aux_i8) # read Int8Array 02
        output_specs = list(aux_i8) # read Int8Array 03

        ugen_inputs = []
        for i in range(0, len(input_specs), 2):
            ugen_index = input_specs[i]
            output_index = input_specs[i+1]
            if ugen_index < 0:
                input = self.constants[output_index]
            else:
                ugen = self.sdef.children[ugen_index]
                if isinstance(ugen, ug.MultiOutUGen):
                    input = ugen.channels[output_index]
                else:
                    input = ugen
            ugen_inputs.append(input)

        rate = ['scalar', 'control', 'audio'][rateIndex]
        ugen = ugen_class.new_from_desc(rate, num_outputs, ugen_inputs, special_index) # BUG: implementar UGen.new_from_desc, está comentada.
        if isinstance(input, ug.OutputProxy):
            ugen = ugen.source_ugen # BUG: esta propiedad se llama source en sclang y la implementan todas las clases pero solo se usa para OutputProxy. Comentarios en UGen.init_topo_sort
        ugen.add_to_synth() # BUG: vaya a saber uno por qué en el código original se pasa a si mismo como parámetro si addToSynth no recibe en ninguna implementación, esto es porque sclang ignora los argumentos demás.

        def add_io(lst, nchan): # lambda
            b = ugen.inputs[0]
            if b.__class__ is ug.OutputProxy and isinstance(b.source_ugen, scio.Control):
                control = None
                for item in self.controls: # detect
                    if item.index == (b.output_index + b.source_ugen.special_index):
                        control = item
                        break
                if control:
                    b = control.name
            lst.append(IODesc(rate, nchan, b, ugen_class))

        if ugen_class.is_control_ugen(): # BUG: otra de esas cosas de sclang, AudioControl y Control implementan y devuelve True, Object devuelve False, además en Object es método de instancia y no de calse como en las otras.
            # // Control.newFromDesc does not set the specialIndex, since it doesn't call Control-init.
            # // Therefore we fill it in here:
            ugen.special_index = special_index
            for i in range(num_outputs):
                self.controls[i+special_index].rate = rate
        else:
            if ugen_class.is_input_ugen(): # BUG: implementan AbstractIn (true) y Object (false) ídem is_control_ugen()
                add_io(self.inputs, len(ugen.channels))
            elif ugen_class.is_output_ugen(): # BUG: implementan AbstractOut (true) y Object (false) ídem is_control_ugen()
                add_io(self.outputs, ugen.num_audio_channels())
            else:
                self.can_free_synth = self.can_free_synth or ugen.can_free_synth() # BUG: también es una función implementadas por muchas ugens (true) y y Object (false). Es una propiedad solo en esta clase.

    def make_msg_func(self):
        comma = False
        names = set()

        # // if a control name is duplicated, the msgFunc will be invalid
        # // that "shouldn't" happen but it might; better to check for it
        # // and throw a proper error
        for cname in self.controls:
            if cname.name[0].isalpha(): # BUG: creo que cname.name siempre es str, pero usa asString, revisar.
                name = cname.name
                if name in names:
                    msg = "could not build msg_func for this SynthDesc: duplicate control name '{}'"
                    warnings.warn(msg.format(name))
                    comma = True
                else:
                    names.add(name)

        if len(names) > 255:
            msg = "a SynthDef cannot have more than 255 control names ('{}')"
            raise Exception(msg.format(self.name))

        # // reusing variable to know if I should continue or not
        if comma:
            msg = "SynthDef '{}' has been saved in the library and loaded on the server, if running. Use of this synth in Patterns will not detect argument names automatically because of the duplicate name(s)."
            warnings.warn(msg.format(self.name))
            self.msg_func = None
            return

        comma = False
        names = 0 # // now, count the args actually added to the func
        suffix = hex(self.__hash__() & 0xFFFFFFFF) # 32 bits positive

        string = 'def sdesc_' + suffix + '('
        for i, cname in enumerate(self.controls):
            name = cname.name
            if name != '?':
                if name == 'gate':
                    self.has_gate = True
                    if self.msg_func_keep_gate:
                        if comma:
                            string += ', '
                        else:
                            comma = True
                        string += name
                        names += 1
                else:
                    if name[1] == '_':
                        name2 = name[2:]
                    else:
                        name2 = name
                    if comma:
                        string += ', '
                    else:
                        comma = True
                    string += name2
                    names += 1
        string += '):\n'

        comma = False

        string += '    x_' + suffix + ' = []'
        for i, cname in enumerate(self.controls):
            name = cname.name
            if name != '?':
                if self.msg_func_keep_gate or name != 'gate':
                    if name[1] == '_':
                        name2 = name[2:]
                    else:
                        name2 = name
                    string += '    if ' + name2 + ':'
                    string += '        x_' + suffix + '.append(' + name + ')'
                    string += '        x_' + suffix + '.append(' + name2 + ')\n'
                    names += 1
        string += '    x_' + suffix + '\n'
        string += 'self.msg_func = sdesc_' + suffix'

        # // do not compile the string if no argnames were added
        if names > 0:
            exec(string)

    @property
    def msg_func_keep_gate(self):
        return self._msg_func_keep_gate
    @msg_func_keep_gate.setter
    def msg_func_keep_gate(self, value):
        if value != self.msg_func_keep_gate:
            self._msg_func_keep_gate = value
            self.make_msg_func()

    def write_metadata(self, path, md_plugin): # TODO: el nombre me resulta confuso en realación a lo que hace. En SynthDef writeDefFile y store llama a SynthDesc.populateMetadataFunc.value(desc) inmediatamente antes de esta función.
        if self.metadata is None:
            AbstractMDPlugin.clear_metadata(path)
            return
        if md_plugin is None:
            self.__class__.md_plugin.write_metadata(self.metadata, self.sdef, path)

    # // parse the def name out of the bytes array sent with /d_recv
    @classmethod
    def def_name_from_bytes(cls, data: bytesarray): # TODO: posible BUG: Es el mismo type que devuelve SynthDef:as_bytes, si cambia allá cambia acá.
        stream = io.BytesIO(data)

        stream.read(4) # getInt32 SCgf
        stream.read(4) # getInt32 version
        struct.unpack('>h', file.read(2)) # getInt16 num_defs # BUG: typo: en sclang declara y asigna num_defs pero no la usa

        aux_str_len = struct.unpack('B', stream.read(1))[0] # getPascalString 01
        aux_string = stream.read(aux_str_len) # getPascalString 02
        return str(aux_string, 'ascii') # getPascalString 03

    def output_data(self): # TODO: no parece usar este método en ninguna parte
        ugens = self.sdef.children
        outs = [x for x in ugens if x.wirtes_to_bus()] # BUG: interfaz/protocolo, falta implementar
        return [{'rate': x.rate, 'num_channels': x.num_audio_channels()} for x in outs]


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
