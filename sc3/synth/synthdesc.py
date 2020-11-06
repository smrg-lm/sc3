"""SynthDesc.sc"""

import pathlib
import json
import io

from ..base import platform as plf
from ..base import utils as utl
from ..base import systemactions as sac
from ..base import classlibrary as clb
from ..base import model as mdl
from ..base import main as _libsc3
from . import spec as spc
from . import ugen as ugn
from . import ugens as ugns
from . import server as srv
from . import synthdef as sdf
from . import _fmtrw as frw
from .ugens import inout as iou


__all__ = ['SynthDescLib']


class MdPlugin():
    # Metadata is just a JSON object represented as a Python dictionary.
    # The parameter ``codec`` is a dict containing 'key codecs' ordered by key.
    # Key codecs are objects of three fields, key, encoder and decoder,
    # they know to encode non serializable Python objects and convert them
    # back for a particular metadata key (all the content of a key, e.g.
    # spec_codec knows to decode specs which is the only data type of the key),
    # encoder is function that return JSON serializable Python objects,
    # it acts just like storeArgs in sclang. decoder receives that objects
    # retrieved with json.load an reconstruct the right object for the key.
    # Custom MdPlugins are instance objects with a dict of key codecs, there
    # is no need to make subclasses. This is so we don't have to write a
    # serialization protocol for each sc3 object. Different metadata
    # organizations can be differentiated just by its content (e.g. special
    # keys, format keys, version keys or similar).

    SUFFIX = 'scjsonmd'  # The only extension.
    _default_codec = {'specs': spc.spec_codec}

    def __init__(self, codec=None):
        self.codec = codec or type(self)._default_codec

    def write(self, synthdef, path):  # Was *write_metadata.
        path = pathlib.Path(path) / f'{synthdef.name}.{self.SUFFIX}'
        if path.exists():
            path.unlink()
        if synthdef.metadata:
            metadata = synthdef.metadata.copy()
            for key in self.codec:
                if key in metadata:
                    metadata[key] = self.codec[key].encoder(metadata[key])
            with open(path, 'w') as file:
                json.dump(metadata, file)

    def read(self, synthdef, path):  # Was *read_metadata.
        path = pathlib.Path(path) / f'{synthdef.name}.{self.SUFFIX}'
        return self.read_file(path)

    def read_file(self, path):
        if path.exists():
            with open(path, 'r') as file:
                metadata = json.load(file)
            for key in self.codec:
                if key in metadata:
                    metadata[key] = self.codec[key].decoder(metadata[key])
            return metadata
        return None

    def delete(self, synthdef, path):  # Was *clear_metadata.
        path = pathlib.Path(path) / f'{synthdef.name}.{self.SUFFIX}'
        if path.exists():
            path.unlink()

    # def delete_all(self, path):
    #     for file in pahtlib.Path(path).glob(f'*.{self.SUFFIX}'):
    #         file.unlink()


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


class SynthDesc():
    _RATE_NAME = ('scalar', 'control', 'audio', 'demand')  # Used by index.

    md_plugin = MdPlugin()  # TODO: // override in your startup file.
    populate_metadata_func = lambda desc: None

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
    def new_from(cls, synthdef, keep_def=True):
        stream = io.BytesIO(synthdef.as_bytes())
        stream.read(4)  # SCgf
        version = frw.read_i32(stream)
        num_defs = frw.read_i16(stream)  # Always 1 here. Not used.
        desc = cls()  # desc = SynthDesc()
        if version >= 2:
            desc._read_synthdef2(stream, keep_def)
        else:
            desc._read_synthdef(stream, keep_def)
        desc.metadata = synthdef.metadata
        if keep_def:
            desc.sdef = synthdef
        return desc

    @classmethod
    def read(cls, path, keep_defs=False):
        path = pathlib.Path(path)
        ret = []
        for filename in path.parent.glob(path.name):
            with open(filename, 'rb') as file:
                ret.extend(cls._read_stream(file, keep_defs, filename))
        return ret

    @classmethod
    def _read_stream(cls, stream, keep_defs=False, path=None):  # Was readFile.
        # path is for metadata.
        stream.read(4)  # SCgf
        version = frw.read_i32(stream)
        num_defs = frw.read_i16(stream)
        ret = []
        for _ in range(num_defs):
            desc = SynthDesc()
            if version >= 2:
                desc._read_synthdef2(stream, keep_defs)
            else:
                desc._read_synthdef(stream, keep_defs)
            ret.append(desc)
            if path:
                desc.metadata = cls.md_plugin.read_file(
                    path.parent / f'{path.stem}.{type(cls.md_plugin).SUFFIX}')
            cls.populate_metadata_func(desc)
            in_memory_stream = isinstance(stream, io.BytesIO)
            if desc.sdef is not None and not in_memory_stream:
                if desc.metadata is None:
                    desc.metadata = dict()
                desc.metadata['reconstructed'] = True  # Was 'shouldNotSend'.
                desc.metadata['load_path'] = str(path)
                desc.sdef.metadata = desc.metadata
        return ret

    def _read_synthdef(self, stream, keep_def=False):  # TODO
        raise NotImplementedError(
            'read_synthdef format version 1 not implemented')

    def _read_ugen_spec(self, stream):  # TODO
        raise NotImplementedError(
            'read_ugen_spec format version 1 not implemented')

    def _read_synthdef2(self, stream, keep_def=False):
        with _libsc3.main._def_build_lock:
            try:
                self.inputs = []
                self.outputs = []
                self.control_names = []
                self.control_dict = dict()

                self.name = frw.read_pascal_str(stream)

                self.sdef = sdf.SynthDef._dummy(self.name)
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
                    self.control_dict[control_name] = \
                        self.controls[control_index]

                num_ugens = frw.read_i32(stream)
                for _ in range(num_ugens):
                    self._read_ugen_spec2(stream)

                # Append all default values of each multichannel
                # control to the fist ControlName default value.
                aux_ctrl = None
                for ctrl in self.controls:
                    if ctrl.name == '?':
                        default_value = utl.as_list(aux_ctrl.default_value)
                        default_value.append(ctrl.default_value)
                        aux_ctrl.default_value = default_value
                    else:
                        aux_ctrl = ctrl

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

    def _read_ugen_spec2(self, stream):
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

    def send(self, server, completion_msg=None):
        self.sdef.send(server, completion_msg)

    def write_metadata(self, path, md_plugin=None):
        md_plugin = md_plugin or self.md_plugin
        if self.metadata is None:
            md_plugin.delete(self.sdef, path)
        else:
            md_plugin.write(self.sdef, path)

    @classmethod
    def def_name_from_bytes(cls, data: bytearray):
        # // parse the def name out of the bytes array sent with /d_recv
        stream = io.BytesIO(data)
        stream.read(4)  # getInt32 // SCgf
        version = frw.read_i32(stream)  # Not used.
        num_defs = frw.read_i16(stream)  # Not used.
        return frw.read_pascal_str(stream)

    # def output_data(self):
    #     ugens = self.sdef._children
    #     outs = [x for x in ugens if x._writes_to_bus()]
    #     return [
    #         {'rate': x.rate, 'num_channels': x._num_audio_channels()}
    #         for x in outs]

    def __str__(self):  # Was printOn.
        string = f"SynthDesc '{self.name}':"
        for control in self.controls:
            string += f'\n  K {repr(control)}'
        for input in self.inputs:
            string += f'\n  I {repr(input)}'
        for output in self.outputs:
            string += f'\n  O {repr(output)}'
        return string


class MetaSynthDescLib(type):
    def __init__(cls, *_):
        cls.all = dict()

        def init_func(cls):
            cls.default = cls('default')  # Was global in sclang.
            sac.ServerBoot.add('all', cls.__on_server_boot)  # *** NOTE: *send calls global.send if server has booted, see below.

        clb.ClassLibrary.add(cls, init_func)


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

    def add(self, synth_desc):
        self.synth_descs[synth_desc.name] = synth_desc
        mdl.NotificationCenter.notify(self, 'sdesc_added', synth_desc)

    def remove_at(self, name): # BUG: es remove_at porque es un diccionario, pero es interfaz de esta clase que oculta eso, ver qué problemas puede traer.
        self.synth_descs.pop(name) #, None) # BUG: igualmente self.servers es un set y tirar KeyError con remove

    def add_server(self, server):
        self.servers.add(server)

    def remove_server(self, server):
        self.servers.remove(server)

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

    def send(self, server=None, try_reconstructed=True):
        server_list = utl.as_list(server) or self.servers
        for s in server_list:
            for desc in self.synth_descs.values():
                if not desc.sdef.metadata.get('reconstructed', False):
                    desc.send(s)
                elif try_reconstructed:
                    desc.sdef._load_reconstructed(s)

    def read(self, path=None, keep_defs=True):
        path = path or plf.Platform.synthdef_dir / f'*.{sdf.SynthDef._SUFFIX}'
        path = pathlib.Path(path)
        for desc in SynthDesc.read(path, keep_defs):
            self.add(desc)
            mdl.NotificationCenter.notify(self, 'sdesc_added', desc)
