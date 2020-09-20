"""SynthDesc.sc"""

import io
import logging
import glob

from ..base import utils as utl
from ..base import systemactions as sac
from ..base import model as mdl
from ..base import main as _libsc3
from . import ugen as ugn
from . import ugens as ugns
from . import server as srv
from . import synthdef as sdf
from . import _fmtrw as frw
from .ugens import inout as iou


__all__ = ['SynthDescLib']


_logger = logging.getLogger(__name__)


class SynthDescError(Exception):
    pass


class IODesc():
    def __init__(self, rate, num_channels, starting_channel, type):
        self.rate = rate
        self.num_channels = num_channels
        self.starting_channel = starting_channel or '?'
        self.type = type

    def __repr__(self):  # Was printOn.
        return (
            f"{type(self).__name__}(rate='{self.rate}', "
            f"num_channels={self.num_channels}, "
            f"starting_channel={self.starting_channel}, "
            f"type={self.type.__name__})")


# TODO: Estas clases están ligadas al protocolo Archiving de Object.sc (L800).
# Tengo que ver con qué recursos de Python representarlas.
#
# // Basic metadata plugins
#
# // to disable metadata read/write
class AbstractMDPlugin():
    @classmethod
    def clear_metadata(cls, path):
        ... # BUG: Falta implementar, es test para SynthDef _write_def_after_startup

    @classmethod
    def write_metadata(cls, metadata, synthdef, path):
        ... # BUG: Falta implementar, es test para SynthDef _write_def_after_startup, acá se llama en la función homónima de SynthDesc

    @classmethod
    def read_metadata(cls, path):
        return None # BUG: BUG: Falta implementar, hace varias cosas, retorna nil si no lo logra.

    # TODO: todo...


class TextArchiveMDPlugin(AbstractMDPlugin):
    # // simple archiving of the dictionary
    ... # TODO


class SynthDesc():
    _RATE_NAME = ('scalar', 'control', 'audio', 'demand')  # Used by index.

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
        self.sdef = None  # Was def, reserved word.
        self.has_gate = False
        self.keep_gate = False  # Was msg_func_keep_gate.
        self.has_array_args = None
        self.has_variants = False
        # self.can_free_synth = False  # Non core interface, removed.

    @classmethod
    def new_from(cls, synthdef):
        return synthdef.as_synth_dec()

    def send(self, server, completion_msg):
        self.sdef.send(server, completion_msg)

    def __str__(self):  # Was printOn.
        string = f"SynthDesc '{self.name}':"
        for control in self.controls:
            string += f'\n  K {repr(control)}'
        for input in self.inputs:
            string += f'\n  I {repr(input)}'
        for output in self.outputs:
            string += f'\n  O {repr(output)}'
        return string

    @classmethod
    def read(cls, path, keep_defs=False, dictionary=None):
        # // Don't use *read or *readFile to read into a SynthDescLib.
        # // Use SynthDescLib:read or SynthDescLib:readStream instead.
        dictionary = dictionary or dict()
        for filename in glob.glob(str(path)):
            with open(filename, 'rb') as file:
                dictionary = cls._read_file(file, keep_defs, dictionary)
        return dictionary

    @classmethod
    def _read_file(cls, stream, keep_defs=False, dictionary=None, path=''):
        # // path is for metadata -- only this method
        # // has direct access to the new SynthDesc.
        stream.read(4)  # getInt32 // SCgf
        version = frw.read_i32(stream)
        num_defs = frw.read_i16(stream)
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

    def read_synthdef(self, stream, keep_def=False):  # TODO
        raise NotImplementedError(
            'read_synthdef format version 1 not implemented')

    def read_ugen_spec(self, stream):  # TODO
        raise NotImplementedError(
            'read_ugen_spec format version 1 not implemented')

    def read_synthdef2(self, stream, keep_def=False):
        with _libsc3.main._def_build_lock:
            try:
                self.inputs = []
                self.outputs = []
                self.control_names = []
                self.control_dict = dict()

                self.name = frw.read_pascal_str(stream)

                self.sdef = sdf.SynthDef.dummy(self.name)
                _libsc3.main._current_synthdef = self.sdef

                num_constants = frw.read_i32(stream)
                self.constants = frw.read_f32_list(stream, num_constants)

                num_controls = frw.read_i32(stream)
                self.sdef._controls = frw.read_f32_list(stream, num_controls)
                self.controls = [
                    iou.ControlName('?', i, '?', self.sdef._controls[i], None)
                    for i in range(num_controls)]

                num_control_names = frw.read_i32(stream)
                for _ in range(num_control_names):
                    control_name = frw.read_pascal_str(stream)
                    control_index = frw.read_i32(stream)
                    self.controls[control_index].name = control_name
                    self.control_names.append(control_name)
                    self.control_dict[control_name] = self.controls[control_index]

                num_ugens = frw.read_i32(stream)
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

                self.sdef._control_names = [
                    x for x in self.controls if x.name is not None]
                self.has_array_args = any(
                    cn.name == '?' for cn in self.controls)

                num_variants = frw.read_i16(stream)
                self.has_variants = num_variants > 0
                # // maybe later, read in variant names and values
                # // this is harder than it might seem at first

                self.sdef._constants = dict()
                for i, k in enumerate(self.constants):
                    self.sdef._constants[k] = i

                if not keep_def:
                    # // throw away unneeded stuff
                    self.sdef = None
                    self.constats = None

                self._check_synthdesc2()
            finally:
                _libsc3.main._current_synthdef = None

    def read_ugen_spec2(self, stream):
        ugen_class = frw.read_pascal_str(stream)
        try:
            ugen_class = ugns.installed_ugens[ugen_class]
        except NameError as e:
            raise Exception(
                f"no UGen class found for '{ugen_class}' which was "
                f"specified in synth def file: {self.name}") from e

        rate_index = frw.read_i8(stream)
        num_inputs = frw.read_i32(stream)
        num_outputs = frw.read_i32(stream)
        special_index = frw.read_i16(stream)

        # NOTE: _write_input_spec writes _synth_index and _output_index as i32.
        input_specs = frw.read_i32_list(stream, num_inputs * 2)
        output_specs = frw.read_i8_list(stream, num_outputs)  # Not used.

        ugen_inputs = []
        for i in range(0, len(input_specs), 2):
            ugen_index = input_specs[i]
            output_index = input_specs[i + 1]
            if ugen_index < 0:
                input = self.constants[output_index]
            else:
                ugen = self.sdef._children[ugen_index]
                if isinstance(ugen, ugn.MultiOutUGen):
                    input = ugen._channels[output_index]
                else:
                    input = ugen
            ugen_inputs.append(input)

        rate = self._RATE_NAME[rate_index]
        ugen = ugen_class._new_from_desc(
            rate, num_outputs, ugen_inputs, special_index)
        if isinstance(ugen, ugn.OutputProxy):
            ugen = ugen.source_ugen
        ugen._add_to_synth()

        def add_iodesc(iolst, nchan):  # lambda
            b = ugen.inputs[0]
            if type(b) is ugn.OutputProxy\
            and isinstance(b.source_ugen, iou.Control):
                control = None
                cmp_index = b._output_index + b.source_ugen._special_index
                for item in self.controls:  # detect
                    if item.index == cmp_index:
                        control = item
                        break
                if control is not None:
                    b = control.name
            iolst.append(IODesc(rate, nchan, b, ugen_class))

        if issubclass(ugen_class, iou.AbstractControl):
            # // Control.newFromDesc does not set the specialIndex, since it
            # // doesn't call Control-init. Therefore we fill it in here.
            ugen._special_index = special_index
            for i in range(num_outputs):
                self.controls[i + special_index].rate = rate
        elif issubclass(ugen_class, iou.AbstractIn):
            add_iodesc(self.inputs, len(ugen._channels))
        elif issubclass(ugen_class, iou.AbstractOut):
            add_iodesc(self.outputs, ugen._num_audio_channels())

    def _check_synthdesc2(self):
        names = set()
        nm = None

        # For reasons I don't know, synthdef controls can have duplicated
        # names, beacuse control values can be assigned by position. That is
        # not possible if the file was created from this library or sclang's
        # standard interface, unless there is a bug somewhere. For simplicity
        # and consistnecy, I'm considering the files as malformed and throwing
        # an error. This can be review later.
        for cname in self.controls:
            nm = cname.name
            if nm != '?' and nm in names:
                raise SynthDescError(
                    f"SynthDesc '{self.name}' has duplicated "
                    f"control name '{nm}'")
            else:
                names.add(nm)

        if len(names) > 255:
            raise SynthDescError(
                "a SynthDef cannot have more than 255 "
                f"control names ('{self.name}')")

        if 'gate' in names:
            self.has_gate = True

    def write_metadata(self, path, md_plugin=None): # BUG falta MDPlugin # TODO: el nombre me resulta confuso en realación a lo que hace. En SynthDef writeDefFile y store llama a SynthDesc.populateMetadataFunc.value(desc) inmediatamente antes de esta función.
        if self.metadata is None:
            AbstractMDPlugin.clear_metadata(path)
            return
        md_plugin = md_plugin or self.md_plugin
        md_plugin.write_metadata(self.metadata, self.sdef, path)

    @classmethod
    def def_name_from_bytes(cls, data: bytearray): # TODO: posible BUG: Es el mismo type que devuelve SynthDef:as_bytes, si cambia allá cambia acá.
        # // parse the def name out of the bytes array sent with /d_recv
        stream = io.BytesIO(data)
        stream.read(4)  # getInt32 // SCgf
        version = frw.read_i32(stream)  # Not used.
        num_defs = frw.read_i16(stream)  # Not used.
        return frw.read_pascal_str(stream)

    def output_data(self): # TODO: no parece usar este método en ninguna parte
        ugens = self.sdef._children
        outs = [x for x in ugens if x.wirtes_to_bus()] # BUG: interfaz/protocolo, falta implementar
        return [{'rate': x.rate, 'num_channels': x._num_audio_channels()} for x in outs]


class MetaSynthDescLib(type):
    def __init__(cls, *_):
        cls.all = dict()

        def init_func(cls):
            cls.default = cls('default')  # Was global in sclang.
            sac.ServerBoot.add('all', cls.__on_server_boot)  # *** NOTE: *send calls global.send if server has booted, see below.

        utl.ClassLibrary.add(cls, init_func)


    ### System Actions ###

    def __on_server_boot(cls, server):
        # // tryToLoadReconstructedDefs = false:
        # // since this is done automatically, w/o user action,
        # // it should not try to do things that will cause warnings
        # // (or errors, if one of the servers is not local)
        if server._status_watcher.has_booted:
            cls.default.send(server, False)


class SynthDescLib(metaclass=MetaSynthDescLib):
    def __init__(self, name, servers=None):
        self.name = name
        self.all[name] = self
        self.synth_descs = dict()
        self.servers = set(servers or [srv.Server.default])

    @classmethod
    def get_lib(cls, libname):
        try:
            return cls.all[libname]
        except KeyError as e:
            raise Exception(f"library '{libname}' not found") from e

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
    #     if server._status_watcher.has_booted: cls.default.send(server, try_reconstructed)
    def send(self, server=None, try_reconstructed=True):
        server_list = utl.as_list(server) or self.servers
        for s in server_list:
            for desc in self.synth_descs.values():
                if 'shouldNotSend' in desc.sdef.metadata\
                and not desc.sdef.metadata['shouldNotSend']:  # BUG: camelCase
                    desc.send(s)
                elif try_reconstructed:
                    desc.sdef._load_reconstructed(s)

    def read(self, path=None, keep_defs=True):
        if path is None:
            path = sdf.SynthDef.synthdef_dir / '*.scsyndef'
        for filename in glob.glob(str(path)):
            with open(filename, 'rb') as file:
                self.read_stream(file, keep_defs, filename)

    def read_stream(self, stream, keep_defs=True, path=''):
        stream.read(4)  # getInt32 // SCgf
        version = frw.read_i32(stream)
        num_defs = frw.read_i16(stream)
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
        stream.read(4)  # getInt32 // SCgf
        version = frw.read_i32(stream)
        num_defs = frw.read_i16(stream)  # // should be 1  # Not used.
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
