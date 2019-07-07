"""SynthDesc.sc"""

import io
import struct
import warnings
import glob # sclang usa glob y glob se encarga de '*' (que no lista los archivos ocultos), hace str(path) para poder usar Path en la interfaz
#from pathlib import Path # BUG: no se si es necesario, se usa cuando sd.SynthDef.synthdef_dir devuelve un objeto Path en SynthDescLib:read.

from . import _hackprovisorio_borrar as _hkpb

from . import _global as _gl
from . import inout as scio
from . import utils as utl
from . import ugens as ugn
from . import server as srv
from . import systemactions as sac
from . import model as mdl
from . import synthdef as sdf


class IODesc():
    def __init__(self, rate, num_channels, starting_channel, type):
        self.rate = rate
        self.num_channels = num_channels
        self.starting_channel = starting_channel or '?'
        self.type = type

    #def print_on(self, stream: io.StringIO):
    def __str__(self):
        string = str(self.rate) + ' '
        string += self.type.__name__ + ' '
        string += str(self.starting_channel) + ' '
        string += str(self.num_channels)
        return string


# TODO: Estas clases están ligadas al protocolo Archiving de Object.sc (L800).
# Tengo que ver con qué recursos de Python representarlas.
#
# // Basic metadata plugins
#
# // to disable metadata read/write
class AbstractMDPlugin():
    @classmethod
    def clear_metadata(cls, path):
        pass # BUG: Falta implementar, es test para SynthDef write_def_after_startup
    @classmethod
    def write_metadata(cls, metadata, synthdef, path):
        pass # BUG: Falta implementar, es test para SynthDef write_def_after_startup, acá se llama en la función homónima de SynthDesc
    @classmethod
    def read_metadata(cls, path):
        return None # BUG: BUG: Falta implementar, hace varias cosas, retorna nil si no lo logra.
    # TODO: todo...


# // simple archiving of the dictionary
class TextArchiveMDPlugin(AbstractMDPlugin):
    pass # TODO


class SynthDesc():
    md_plugin = TextArchiveMDPlugin # // override in your startup file
    populate_metadata_func = lambda *args: None # BUG: aún no sé quién/cómo setea esta función
                                                # BUG: VER SynthDescs and SynthDef metadata en SynthDesc.schelp

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
        self.msg_func = lambda event: [] # NOTE: Se llama si la SynthDef no define argumentos. Necesita definir el argumento porque siempre se pasa Event para obtener las llaves, y tiene que devolver una lista.
        self.has_gate = False
        self.has_array_args = None
        self.has_variants = False
        self.can_free_synth = False
        self._msg_func_keep_gate = False # @property

    @classmethod
    def new_from(cls, synthdef): # TODO: ver estos métodos constructores en general, posiblemente sea mejor llamar a __new__ con argumentos.
        return synthdef.as_synth_dec()

    def send(self, server): #, completion_msg): # BUG: ver completion_msg que no se usa o recibe. Tal vez tenga que mirar a más bajo nivel, pero las funciones send_msg/bundle osc no tienen esa lógica.
        self.sdef.send(server) #, completion_msg) # parece ser una instancia de SynthDef

    #def print_on(self, stream: io.StringIO):
    def __str__(self):
        string = "SynthDesc '" + self.name + "'\nControls:\n"
        for control in self.controls:
            string += control.__str__() + '\n'
        for input in self.inputs:
            string += '    I ' + input.__str__() + '\n'
        for output in self.outputs:
            string += '    O ' + output.__str__()
        return string

    # // don't use *read or *readFile to read into a SynthDescLib. Use SynthDescLib:read or SynthDescLib:readStream instead
    @classmethod
    def read(cls, path, keep_defs=False, dictionary=None):
        dictionary = dictionary or dict()
        for filename in glob.glob(str(path)):
            with open(filename, 'rb') as file:
                dictionary = cls._read_file(file, keep_defs, dictionary)
        return dictionary

    # // path is for metadata -- only this method has direct access to the new SynthDesc
    @classmethod
    def _read_file(cls, stream, keep_defs=False, dictionary=None, path=''):
        stream.read(4) # getInt32 // SCgf # TODO: la verdad que podría comprobar que fuera un archivo válido.
        version = struct.unpack('>i', stream.read(4))[0] # getInt32
        num_defs = struct.unpack('>h', stream.read(2))[0] # getInt16
        for _ in num_defs:
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

                self.sdef = sdf.SynthDef.dummy(self.name) # BUG: Object:prNew es objeto vacío, dummy, y se va llenando acá pero no se puede llamar a __init__ porque este llama a _build
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
                    scio.ControlName('?', i, '?', self.sdef.controls[i], None)
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
                        default_value = utl.as_list(aux_ctrl.default_value)
                        default_value.append(ctrl.default_value)
                        aux_ctrl.default_value = default_value
                    else:
                        aux_ctrl = ctrl
                # end of BUG: inject(nil), revisar

                self.sdef.control_names = [x for x in self.controls if x.name is not None] # select x.name.notNil
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
            ugen_class = _hkpb.installed_ugens[ugen_class] # Resuelto con hkpb por ahora, algo así no mucho más está bien. # eval(ugen_class) # BUG: globals=None, locals=None) BUG: falta el contexto en el cuál buscar. Tendría que poder buscar una clase en las librerías e importar solo de ese módulo.
        except NameError as e:
            msg = "no UGen class found for '{}' which was specified in synth def file: {}"
            raise Exception(msg.format(ugen_class, self.name)) from e

        rate_index = struct.unpack('b', stream.read(1))[0] # getInt8
        num_inputs = struct.unpack('>i', stream.read(4))[0] # getInt32
        num_outputs = struct.unpack('>i', stream.read(4))[0] # getInt32
        special_index = struct.unpack('>h', stream.read(2))[0] # getInt16

        aux_i32 = stream.read(num_inputs * 4 * 2) # read Int32Array 01 # nota: write_input_spec escribe synth_index y output_index como int32
        aux_i32 = struct.unpack('>' + 'i' * (num_inputs * 2), aux_i32) # read Int32Array 02
        input_specs = list(aux_i32) # read Int32Array 03

        aux_i8 = stream.read(num_outputs) # read Int8Array 01
        aux_i8 = struct.unpack('b' * num_outputs, aux_i8) # read Int8Array 02
        # output_specs = list(aux_i8) # read Int8Array 03 # NOTE: leyó para avanzar pero no se usa

        ugen_inputs = []
        for i in range(0, len(input_specs), 2):
            ugen_index = input_specs[i]
            output_index = input_specs[i + 1]
            if ugen_index < 0:
                input = self.constants[output_index]
            else:
                ugen = self.sdef.children[ugen_index]
                if isinstance(ugen, ugn.MultiOutUGen):
                    input = ugen.channels[output_index]
                else:
                    input = ugen
            ugen_inputs.append(input)

        rate = ['scalar', 'control', 'audio'][rate_index]
        ugen = ugen_class.new_from_desc(rate, num_outputs, ugen_inputs, special_index)
        if isinstance(ugen, ugn.OutputProxy):
            ugen = ugen.source_ugen # BUG: esta propiedad se llama source en sclang y la implementan todas las clases pero solo se usa para OutputProxy. Comentarios en UGen.init_topo_sort
        ugen.add_to_synth() # BUG: vaya a saber uno por qué en el código original se pasa a si mismo como parámetro si addToSynth no recibe en ninguna implementación, esto es porque sclang ignora los argumentos demás.

        def add_io(lst, nchan): # lambda
            b = ugen.inputs[0]
            if b.__class__ is ugn.OutputProxy and isinstance(b.source_ugen, scio.Control):
                control = None
                for item in self.controls: # detect
                    if item.index == (b.output_index + b.source_ugen.special_index):
                        control = item
                        break
                if control is not None:
                    b = control.name
            lst.append(IODesc(rate, nchan, b, ugen_class))

        if ugen_class.is_control_ugen(): # TODO, revisar protocolo: otra de esas cosas de sclang, AudioControl y Control implementan y devuelve True, Object devuelve False, además en Object es método de instancia y no de calse como en las otras.
            # // Control.newFromDesc does not set the specialIndex, since it doesn't call Control-init.
            # // Therefore we fill it in here:
            ugen.special_index = special_index
            for i in range(num_outputs):
                self.controls[i + special_index].rate = rate
        else:
            if ugen_class.is_input_ugen(): # TODO, revisar protocolo: implementan AbstractIn (true) y Object (false) ídem is_control_ugen()
                add_io(self.inputs, len(ugen.channels))
            elif ugen_class.is_output_ugen(): # TODO, revisar protocolo: implementan AbstractOut (true) y Object (false) ídem is_control_ugen()
                add_io(self.outputs, ugen.num_audio_channels())
            else:
                self.can_free_synth = self.can_free_synth or ugen.can_free_synth() # TODO, revisar protocolo: también es una función implementadas por muchas ugens (true) y y Object (false). Es una propiedad solo en esta clase.

    def make_msg_func(self):
        duplicated_cn = False
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
                    duplicated_cn = True
                else:
                    names.add(name)

        if len(names) > 255:
            msg = "a SynthDef cannot have more than 255 control names ('{}')"
            raise Exception(msg.format(self.name))

        if duplicated_cn:
            msg = "SynthDef '{}' has been saved in the library and loaded on the server, if running. Use of this synth in Patterns will not detect argument names automatically because of the duplicate name(s)."
            warnings.warn(msg.format(self.name))
            self.msg_func = None
            return

        # comma = False
        # names = 0 # // now, count the args actually added to the func
        # suffix = hex(self.__hash__() & 0xFFFFFFFF) # 32 bits positive
        #
        # string = 'def sdesc_' + suffix + '(event, ' # NOTE: es una función que se asigna a una llave de Event, que se evalúa/llama con valueEnvir en 'note', acá se necesita self al evaluarse como método al llamar a la llave con __getattr__ para tener los parámetros del evento.
        # for i, cname in enumerate(self.controls):
        #     name = cname.name
        #     if name != '?':
        #         if name == 'gate':
        #             self.has_gate = True
        #             if self.msg_func_keep_gate:
        #                 if comma:
        #                     string += ', '
        #                 else:
        #                     comma = True
        #                 string += name
        #                 names += 1
        #         else:
        #             if len(name) > 2 and name[1] == '_':
        #                 name2 = name[2:] # BUG: en sclang, no comprueba len, los índices y name2 puede ser un string vacío: x = "a_"[2..]; x.size == 0
        #             else:
        #                 name2 = name
        #             if comma:
        #                 string += ', '
        #             else:
        #                 comma = True
        #             string += name2
        #             names += 1
        # string += '):\n'
        #
        # comma = False # BUG: VER EL USO DE ESTA VARIABLE, ES REALMENTE CONFUSO, E.G. POR QUÉ LA VUELVE A FALSE? POR QUÉ LA USA AL PRINCIPIO ANTES DEL FOR DE LOS ARGUMENTOS PARA NOMBRE DUPLICADOS?!

        # NOTE: gate tiene que estar en names desde el primer for.
        if 'gate' in names:
            self.has_gate = True # NOTE: este método se llama con add() y por lo tanto inicializa antes, aunque Event.play también lo llama y ¿actualiza, por qué? o será por defs cargadas del disco?

        # NOTE: Implementación alterantiva, y sin argumentos, los valores se
        # NOTE: obtienen del parámetro event.
        # NOTE: *** VER POR QUÉ ESTO NECESITA SER UNA FUNCIÓN QUE DEVUELVE UNA
        # NOTE: *** LISTA Y NO PUEDE SER UNA LISTA, A COMPLETAR EN ToDO CASO.
        names_count = 0 # // count the args actually added to the func # NOTE: no reutilizamos ninguna variable que genere confusión.
        suffix = hex(self.__hash__() & 0xFFFFFFFF) # 32 bits positive
        string = 'def sdesc_' + suffix + '(event):\n' # NOTE: es una función que se asigna a una llave de Event, que se evalúa/llama con valueEnvir en 'note', acá se necesita self al evaluarse como método al llamar a la llave con __getattr__ para tener los parámetros del evento.
        string += '    ret = []\n'

        for i, cname in enumerate(self.controls):
            name = cname.name
            if name != '?':
                if self.msg_func_keep_gate or name != 'gate':
                    if len(name) > 2 and name[1] == '_':
                        name2 = name[2:] # BUG: en sclang, no comprueba len, los índices y name2 puede ser un string vacío: x = "a_"[2..]; x.size == 0
                    else:
                        name2 = name
                    string += "    if hasattr(event, '" + name2 + "'):\n" # NOTE: antes era None porque eran los argumentos de valueEnvir.
                    string += "        ret.append('" + name + "')\n"
                    string += "        ret.append(event.value('" + name2 + "'))\n"
                    names_count += 1
        string += '    return ret\n'
        string += 'self.msg_func = sdesc_' + suffix

        print('*** SynthDesc msg_func:'); print(string)

        # // do not compile the string if no argnames were added
        if names_count > 0:
            exec(string)

    @property
    def msg_func_keep_gate(self):
        return self._msg_func_keep_gate
    @msg_func_keep_gate.setter
    def msg_func_keep_gate(self, value):
        if value != self.msg_func_keep_gate:
            self._msg_func_keep_gate = value
            self.make_msg_func()

    def write_metadata(self, path, md_plugin): # BUG falta MDPlugin # TODO: el nombre me resulta confuso en realación a lo que hace. En SynthDef writeDefFile y store llama a SynthDesc.populateMetadataFunc.value(desc) inmediatamente antes de esta función.
        if self.metadata is None:
            AbstractMDPlugin.clear_metadata(path)
            return
        md_plugin = md_plugin or self.md_plugin
        md_plugin.write_metadata(self.metadata, self.sdef, path)

    # // parse the def name out of the bytes array sent with /d_recv
    @classmethod
    def def_name_from_bytes(cls, data: bytearray): # TODO: posible BUG: Es el mismo type que devuelve SynthDef:as_bytes, si cambia allá cambia acá.
        stream = io.BytesIO(data)

        stream.read(4) # getInt32 SCgf
        stream.read(4) # getInt32 version
        struct.unpack('>h', stream.read(2)) # getInt16 num_defs # BUG: typo: en sclang declara y asigna num_defs pero no la usa

        aux_str_len = struct.unpack('B', stream.read(1))[0] # getPascalString 01
        aux_string = stream.read(aux_str_len) # getPascalString 02
        return str(aux_string, 'ascii') # getPascalString 03

    def output_data(self): # TODO: no parece usar este método en ninguna parte
        ugens = self.sdef.children
        outs = [x for x in ugens if x.wirtes_to_bus()] # BUG: interfaz/protocolo, falta implementar
        return [{'rate': x.rate, 'num_channels': x.num_audio_channels()} for x in outs]


@utl.initclass
class SynthDescLib():
    @classmethod
    def __init_class__(cls): # TODO: es para no poner código fuera de la definición, es equivalente a scalng
        cls.all = dict()
        cls.default = cls('global') # BUG era global en vez de default, pero el método default retornaba global. Es default, no global, el mismo patrón que server y client.

        # // tryToLoadReconstructedDefs = false:
        # // since this is done automatically, w/o user action,
        # // it should not try to do things that will cause warnings
        # // (or errors, if one of the servers is not local)
        def action(server):
            if server.has_booted:
                cls.default.send(server, False)
        sac.ServerBoot.add(action) # NOTE: *send llama a global.send if server has booted, ver abajo

    def __init__(self, name, servers=None):
        self.name = name
        self.all[name] = self
        self.synth_descs = dict()
        self.servers = set(servers or [srv.Server.default]) # BUG: para esto hay que asegurarse que Server se inicialice antes, tal vez con un import en __init_class__

    @classmethod
    def get_lib(cls, libname):
        try:
            return cls.all[libname]
        except KeyError as e:
            msg = "library '{}' not found"
            raise Exception(msg.format(libname)) from e

    # Todos los métodos duplicados entre instancia y clase se volvieron
    # solo de instancia. El atributo global pasó a ser default como en server
    # y client. Las llamadas se deben hacer a través de SynthDescLib.default.
    # BUG: ESTO AFECTA LAS LLAMADAS A LA CLASE DESDE OTRAS CLASES.

    def add(self, synth_desc):
        self.synth_descs[synth_desc.name] = synth_desc
        mdl.NotificationCenter.notify(self, 'synthDescAdded', synth_desc) # NOTE: era dependancy # NOTE: No sé dónde SynthDefLib agrega los dependats, puede que lo haga a través de otras clases como AbstractDispatcher

    def remove_at(self, name): # BUG: es remove_at porque es un diccionario, pero es interfaz de esta clase que oculta eso, ver qué problemas puede traer.
        self.synth_descs.pop(name) #, None) # BUG: igualmente self.servers es un set y tirar KeyError con remove

    def add_server(self, server):
        self.servers.add(server)

    def remove_server(self, server):
        self.servers.remove(server)

    # Salvo anotación contraria, todos los métodos de clase no hacían
    # mas que llamar a global con el método de instancia.
    # BUG: ESTO AFECTA LAS LLAMADAS A LA CLASE DESDE OTRAS CLASES.
    def at(self, name):
        return self.synth_descs[name]

    def match(self, name):
        if '.' in name:
            dot_index = name.index('.')
        else:
            return self.synth_descs[name] # BUG: tira KeyError, en sclang nil para la variable ~synthDesc puede significar otra cosa. La usa solo en PmonoStream.prInit al parecer.

        if name[:dot_index] in self.synth_descs:
            desc = self.synth_descs[name[:dot_index]]
            if desc.has_variants:
                return desc # BUG: no me cierra que no compruebe que el nombre de la variente exista, ver PmonoStream.prInit

        return self.synth_descs[name] # BUG: tira KeyError, en sclang nil para la variable ~synthDesc puede significar otra cosa. La usa solo en PmonoStream.prInit al parecer.

    # @classmethod
    # def send(cls, server=None, try_reconstructed=True): # BUG: este método se usa en la inicialización de esta clase con ServerBoot.add, la variante de instancia no comprueba si el servidor está corriendo.
    #     if server.has_booted(): cls.default.send(server, try_reconstructed)
    def send(self, server=None, try_reconstructed=True):
        server_list = utl.as_list(server) or self.servers
        for s in server_list:
            # BUG: aún no entiendo por qué hace server = server.value, usa el método de Object que retorna this.
            for desc in self.synth_descs:
                if 'shouldNotSend' in desc.sdef.metadata and not desc.sdef.metadata['shouldNotSend']: # BUG: la notación camello.
                    desc.send(s)
                elif try_reconstructed:
                    desc.sdef.load_reconstructed(s) # BUG: falta implementar en SynthDef

    def read(self, path=None, keep_defs=True):
        if path is None:
            path = sdf.SynthDef.synthdef_dir / '*.scsyndef'
            # BUG: typo: sclang declara result y no la usa
        for filename in glob.glob(str(path)):
            with open(filename, 'rb') as file:
                self.read_stream(file, keep_defs, filename)

    def read_stream(self, stream, keep_defs=True, path=''):
        stream.read(4) # getInt32 // SCgf # TODO: la verdad que podría comprobar que fuera un archivo válido.
        version = struct.unpack('>i', stream.read(4))[0] # getInt32
        num_defs = struct.unpack('>h', stream.read(2))[0] # getInt16
        result_set = set()
        for _ in range(num_defs):
            if version >= 2:
                desc = SynthDesc()
                desc.read_synthdef2(stream, keep_defs)
            else:
                desc = SynthDesc()
                desc.read_synthdef(stream, keep_defs)
            self.synth_descs[desc.name] = desc
            result_set.add(desc)
            # // AbstractMDPlugin dynamically determines the md archive type
            # // from the file extension
            if path:
                desc.metadata = AbstractMDPlugin.read_metadata(path)
            SynthDesc.populate_metadata_func(desc)
            in_memory_stream = isinstance(stream, io.BytesIO) # TODO: entiendo que es sl significado de { stream.isKindOf(CollStream).not }: de la condición de abajo, porque expresión no explica la intención. Supongo que refiere a que no sea un stream en memoria sino un archivo del disco. En Python los streams en memoria son StringIO y BytesIO. TextIOWrapper y BufferReader se usa para archivos y son hermanas de aquellas en la jerarquía de clases, por lo tanto debería funcionar.
            if desc.sdef is not None and not in_memory_stream:
                if desc.sdef.metadata is None:
                    desc.sdef.metadata = dict()
                desc.sdef.metadata['shouldNotSend'] = True # BUG/TODO: los nombres en metadata tienen que coincidir con las convenciones de sclang... (?)
                desc.sdef.metadata['loadPath'] = path
        for new_desc in result_set:
            mdl.NotificationCenter.notify(self, 'synthDescAdded', new_desc) # NOTE: era dependancy # NOTE: No sé dónde SynthDefLib agrega los dependats, puede que lo haga a través de otras clases como AbstractDispatcher
        return result_set

    def read_desc_from_def(self, stream, keep_def, sdef, metadata=None):
        stream.read(4) # getInt32 // SCgf # TODO: la verdad que podría comprobar que fuera un archivo válido.
        version = struct.unpack('>i', stream.read(4))[0] # getInt32 // version
        num_defs = struct.unpack('>h', stream.read(2))[0] # getInt16 # // should be 1 # NOTE: avanza el cabezal pero no usa el resultado.
        if version >= 2:
            desc = SynthDesc()
            desc.read_synthdef2(stream, keep_def)
        else:
            desc = SynthDesc()
            desc.read_synthdef(stream, keep_def)
        if keep_def: desc.sdef = sdef
        if metadata is not None: desc.metadata = metadata
        self.synth_descs[desc.name] = desc
        mdl.NotificationCenter.notify(self, 'synthDescAdded', desc) # NOTE: era dependancy # NOTE: No sé dónde SynthDefLib agrega los dependats, puede que lo haga a través de otras clases como AbstractDispatcher
        return desc # BUG: esta función se usa para agregar las descs a la libreríá pero el valor de retorno no se usa en SynthDef-add. Ver el resto de la librería de clases.
