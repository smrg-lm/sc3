"""SynthDef.sc"""

import inspect
import logging
import io
import struct
import pathlib

from ..base import utils as utl
from ..base import platform as plf
from ..base import systemactions as sac
from ..base import functions as fn
from . import _global as _gl
from . import ugen as ugn
from . import server as srv
from . import synthdesc as sdc
from .ugens import inout as scio
from .ugens import fftunpacking as ffu


_logger = logging.getLogger(__name__)


class MetaSynthDef(type):
    def __init__(cls, *_):

        def init_func(cls):
            cls.synthdef_dir = plf.Platform.synthdef_dir
            cls.synthdef_dir.mkdir(exist_ok=True) # // Ensure exists

        utl.ClassLibrary.add(cls, init_func)


class SynthDef(metaclass=MetaSynthDef):
    @classmethod
    def dummy(cls, name):
        obj = cls.__new__(cls)

        obj.name = name
        obj.func = None
        obj.variants = dict()
        obj.metadata = dict()
        obj.desc = None

        obj._controls = None
        obj._control_names = []
        obj._all_control_names = []
        obj._control_index = 0
        obj._children = []

        obj._constants = dict()
        obj._constant_set = set()
        obj._max_local_bufs = None

        obj._available = []
        obj._width_first_ugens = []
        obj._rewrite_in_progress = False

        return obj

    #*new L35
    def __init__(self, name, graph_func, rates=None,
                 prepend_args=None, variants=None, metadata=None):
        self.name = name
        self.func = None
        self.variants = variants or dict()
        self.metadata = metadata or dict()
        self.desc = None

        # self._controls = None  # init_build, is set by ugens using _gl.current_synthdef
        self._control_names = []
        self._all_control_names = []
        self._control_index = 0
        self._children = []

        # self._constants = dict()  # init_build
        # self._constant_set = set()  # init_build
        # self._max_local_bufs = None  # init_build, used by LocalBus*new1 check for nil.

        # topo sort
        self._available = []
        self._width_first_ugens = []
        self._rewrite_in_progress = False # = la inicializa a True en optimizeGraph L472 y luego la vuelve a nil, pero es mejor que sea false por los 'if'

        self._build(graph_func, rates or [], prepend_args or [])

    def _build(self, graph_func, rates, prepend_args):
        with _gl.def_build_lock:
            try:
                _gl.current_synthdef = self
                self._init_build()
                self._build_ugen_graph(graph_func, rates, prepend_args)
                self._finish_build()
                self.func = graph_func
                _gl.current_synthdef = None
            except Exception as e:
                _gl.current_synthdef = None
                raise e

    # L53
    @classmethod
    def wrap(cls, func, rates=None, prepend_args=None): # TODO: podría ser, además, un decorador en Python pero para usar dentro de una @synthdef o graph_func
        if _gl.current_synthdef is not None:
            return _gl.current_synthdef._build_ugen_graph(
                func, rates or [], prepend_args or [])
        else:
            raise Exception('SynthDef wrap should be called inside '
                            'a SynthDef graph function')

    # L69
    def _init_build(self):
        # UGen.buildSynthDef, lock above.
        self._constants = dict()
        self._constant_set = set()
        self._controls = []
        self._control_index = 0
        self._max_local_bufs = None

    def _build_ugen_graph(self, graph_func, rates, prepend_args):
        # // Save/restore controls in case of SynthDef.wrap.
        save_ctl_names = self._control_names
        self._control_names = []
        prepend_args = utl.as_list(prepend_args)
        self._args_to_controls(graph_func, rates, len(prepend_args))
        result = graph_func(*(prepend_args + self._build_controls()))
        self._control_names = save_ctl_names
        return result

    def _args_to_controls(self, func, rates, skip_args=0):  # Was addControlsFromArgsOfFunc.
        if not inspect.isfunction(func):
            raise TypeError('@synthdef only apply to functions')

        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        names = [x.name for x in params]
        if len(names) < 1:
            return None

        # // What we do here is separate the ir, tr and kr rate arguments,
        # // create one Control ugen for all of each rate, and then construct
        # // the argument array from combining the OutputProxies of these two
        # // Control ugens in the original order.
        names = names[skip_args:]
        values = [x.default if x != inspect.Signature.empty else None
                  for x in params]
        values = values[skip_args:]
        values = self._apply_metadata_specs(names, values)

        annotations = [x.annotation if x != inspect.Signature.empty else None
                       for x in params]
        annotations = annotations[skip_args:]

        rates += [0] * (len(names) - len(rates))
        rates = [x if x is not None else 0.0 for x in rates]

        for i, name in enumerate(names):
            note = annotations[i]
            value = values[i]
            lag = rates[i]
            msg = 'Lag value {} for {} arg {} will be ignored'

            if (lag == 'ir') or (note == 'ir'):
                if isinstance(lag, (int, float)) and lag != 0:
                    _logger.warning(msg.format(lag, 'i-rate', name))
                self._add_ir(name, value)
            elif (lag == 'tr') or (note == 'tr'):
                if isinstance(lag, (int, float)) and lag != 0:
                    _logger.warning(msg.format(lag, 'trigger', name))
                self._add_tr(name, value)
            elif (lag == 'ar') or (note == 'ar'):
                if isinstance(lag, (int, float)) and lag != 0:
                    _logger.warning(msg.format(lag, 'audio', name))
                self._add_ar(name, value)
            else:
                if lag == 'kr': lag = 0.0
                self._add_kr(name, value, lag)

    # método agregado
    def _apply_metadata_specs(self, names, values):
        # no veo una forma conscisa como en sclang
        new_values = []
        if 'specs' in self.metadata:
            specs = self.metadata['specs']
            for i, value in enumerate(values):
                if value is not None:
                    new_values.append(value)
                else:
                    if names[i] in specs:
                        spec = xxx.as_spec(specs[names[i]]) # BUG: as_spec devuelve un objeto ControlSpec o None, implementan Array, Env, Nil, Spec y Symbol  **** FALTA no está hecha la clase Spec ni la función para los strings!
                    else:
                        spec = xxx.as_spec(names[i])
                    if spec is not None:
                        new_values.append(spec.default()) # BUG **** FALTA no está hecha la clase Spec/ControlSpec, no sé si default es un método
                    else:
                        new_values.append(0.0)
        else:
            new_values = [x if x is not None else 0.0 for x in values]
        return new_values # values no la reescribo acá por ser mutable

    # // Allow incremental building of controls.
    # BUG, BUG: de cada parámetro value hace value.copy, ver posibles consecuencias...
    def _add_non_control(self, name, values):  # Not used in the standard library.
        self._add_control_name(scio.ControlName(name, None, 'noncontrol',
            values, len(self._control_names)))

    def _add_ir(self, name, values):  # *** VER dice VALUES en plural, pero salvo que se pase un array como valor todos los que calcula son escalares u objetos no iterables.
        self._add_control_name(scio.ControlName(name, len(self._controls), 'scalar',
            values, len(self._control_names)))  # values *** VER el argumento de ControlName es defaultValue que puede ser un array para expansión multicanal de controles, pero eso puede pasar acá saliendo de los argumentos?

    def _add_tr(self, name, values):
        self._add_control_name(scio.ControlName(name, len(self._controls), 'trigger',
            values, len(self._control_names)))

    def _add_ar(self, name, values):
        self._add_control_name(scio.ControlName(name, len(self._controls), 'audio',
            values, len(self._control_names)))

    def _add_kr(self, name, values, lags):  # Acá también dice lags en plural pero es un valor simple como string (symbol) o number según interpreto del código anterior.
        self._add_control_name(scio.ControlName(name, len(self._controls), 'control',
            values, len(self._control_names), lags))

    def _add_control_name(self, cn):
        self._control_names.append(cn)
        self._all_control_names.append(cn)

    # L178
    def _build_controls(self):
        nn_cns = [x for x in self._control_names if x.rate == 'noncontrol']
        ir_cns = [x for x in self._control_names if x.rate == 'scalar']
        tr_cns = [x for x in self._control_names if x.rate == 'trigger']
        ar_cns = [x for x in self._control_names if x.rate == 'audio']
        kr_cns = [x for x in self._control_names if x.rate == 'control']

        arguments = [0] * len(self._control_names)
        values = []
        index = None
        ctrl_ugens = None
        lags = None
        valsize = None

        for cn in nn_cns:
            arguments[cn.arg_num] = cn.default_value

        def build_ita_controls(ita_cns, ctrl_class, method):
            nonlocal arguments, values, index, ctrl_ugens
            if ita_cns:
                values = []
                for cn in ita_cns:
                    values.append(cn.default_value)
                index = self._control_index
                ctrl_ugens = getattr(ctrl_class, method)(utl.flat(values))
                ctrl_ugens = utl.as_list(ctrl_ugens)
                ctrl_ugens = utl.reshape_like(ctrl_ugens, values) # .reshapeLike(values);
                for i, cn in enumerate(ita_cns):
                    cn.index = index
                    index += len(utl.as_list(cn.default_value))
                    arguments[cn.arg_num] = ctrl_ugens[i]
                    self._set_control_names(ctrl_ugens[i], cn)

        build_ita_controls(ir_cns, scio.Control, 'ir')
        build_ita_controls(tr_cns, scio.TrigControl, 'kr')
        build_ita_controls(ar_cns, scio.AudioControl, 'ar')

        if kr_cns:
            values = []
            lags = []
            for cn in kr_cns:
                values.append(cn.default_value)
                valsize = len(utl.as_list(cn.default_value))
                if valsize > 1:
                    lags.append(utl.wrap_extend(utl.as_list(cn.lag), valsize))
                else:
                    lags.append(cn.lag)
            index = self._control_index # TODO: esto puede ir abajo si los kr no cambian el índice.

            if any(x != 0 for x in lags):
                ctrl_ugens = scio.LagControl.kr(utl.flat(values), lags) # LagControl.kr(values.flat, lags) //.asArray.reshapeLike(values);
            else:
                ctrl_ugens = scio.Control.kr(utl.flat(values)) # Control.kr(values.flat)
            ctrl_ugens = utl.as_list(ctrl_ugens) # .asArray
            ctrl_ugens = utl.reshape_like(ctrl_ugens, values) # .reshapeLike(values);

            for i, cn in enumerate(kr_cns):
                cn.index = index
                index += len(utl.as_list(cn.default_value))
                arguments[cn.arg_num] = ctrl_ugens[i]
                self._set_control_names(ctrl_ugens[i], cn)

        self._control_names = [x for x in self._control_names
                              if x.rate != 'noncontrol']
        return arguments

    # L263
    def _set_control_names(self, ctrl_ugens, cn):
        # *** BUG: can't find where is this name change is used (name getter of OutputProxy)
        if isinstance(ctrl_ugens, list):
            for ctrl_ugen in ctrl_ugens: # TODO:, posible BUG? Este loop me da la pauta de que no soporta más que un nivel de anidamiento? (!) Qué pasaba si hay más de un nivel acá?
                ctrl_ugen.name = cn.name
        else:
            ctrl_ugens.name = cn.name

    # L273
    def _finish_build(self):
        self._add_copies_if_needed()  # ping, only for PV_Chain ugens.
        self._optimize_graph()
        self._collect_constants()
        self._check_inputs()  # // Will die on error.
        # // re-sort graph. reindex.
        self._topological_sort()
        self._index_ugens()
        # UGen.buildSynthDef = nil; moved to SynthDef in _build try/except

    def _add_copies_if_needed(self):
        # // Could also have PV_UGens store themselves in a separate collection.
        for child in self._width_first_ugens:
            if isinstance(child, ffu.PV_ChainUGen):
                child._add_copies_if_needed()  # pong

    # L468
    # OC: Multi channel expansion causes a non optimal breadth-wise
    # ordering of the graph. The topological sort below follows
    # branches in a depth first order, so that cache performance
    # of connection buffers is optimized.

    # L472
    def _optimize_graph(self):  # ping
        self._init_topo_sort()

        self._rewrite_in_progress = True
        for ugen in self._children[:]:  # ***** Hace _children.copy.do porque modifica los valores de la lista sobre la que itera. VER RECURSIVIDAD: SI MODIFICA UN VALOR ACCEDIDO POSTERIORMENTE None._optimize_graph FALLA??
            ugen._optimize_graph()  # pong
        self._rewrite_in_progress = False

        # // Fixup removed ugens.
        old_size = len(self._children)
        self._children = [x for x in self._children if x is not None]
        if old_size != len(self._children):
            self._index_ugens()

    def _init_topo_sort(self):  # ping
        self._available = []
        for ugen in self._children:
            ugen._antecedents = set()
            ugen._descendants = set()
        for ugen in self._children:
            # // This populates the _descendants and _antecedents.
            ugen._init_topo_sort()  # pong
        for ugen in reversed(self._children):
            ugen._descendants = list(ugen._descendants)
            ugen._descendants.sort(key=lambda x: x._synth_index)
            # // All ugens with no antecedents are made available.
            ugen._make_available()

    def _index_ugens(self): # CAMBIADO A ORDEN DE LECTURA
        for i, ugen in enumerate(self._children):
            ugen._synth_index = i

    # L489
    def _collect_constants(self): # ping
        for ugen in self._children:
            ugen._collect_constants() # pong

    # L409
    def _check_inputs(self): # ping
        first_err = None
        for ugen in self._children:
            err = ugen._check_inputs() # pong, en sclang devuelve nil o un string, creo que esos serían todos los casos según la lógica de este bloque.
            if err: # *** TODO EN SCLANG ES ASIGNA A err Y COMPRUEBA notNil, acá puede ser none, pero ver qué retornan de manera sistemática, ver return acá abajo.
                # err = ugen.class.asString + err;
                # err.postln;
                # ugen.dump_args
                if first_err is None: first_err = err
        if first_err:
            #"SynthDef % build failed".format(this.name).postln;
            raise ValueError(first_err)
        return True # porque ugen._check_inputs() retorna nil y acá true

    def _topological_sort(self):
        self._init_topo_sort()
        ugen = None
        out_stack = []
        while len(self._available) > 0:
            ugen = self._available.pop()
            ugen._arrange(out_stack)
        self._children = out_stack
        self._cleanup_topo_sort()

    def _cleanup_topo_sort(self):
        for ugen in self._children:
            ugen._antecedents = set()
            ugen._descendants = set()
            ugen._width_first_antecedents = []

    # L428
    # // UGens do these. (ping pong methods)

    def _add_ugen(self, ugen):
        if not self._rewrite_in_progress:
            ugen._synth_index = len(self._children)
            ugen._width_first_antecedents = self._width_first_ugens[:]
            self._children.append(ugen)

    def _remove_ugen(self, ugen):
        # // Lazy removal: clear entry and later remove all None entries
        self._children[ugen._synth_index] = None

    def _replace_ugen(self, a, b):
        if not isinstance(b, ugn.UGen):
            raise Exception('_replace_ugen assumes a UGen')

        b._width_first_antecedents = a._width_first_antecedents
        b._descendants = a._descendants
        b._synth_index = a._synth_index
        self._children[a._synth_index] = b

        for item in self._children:  # counter not used in sclang
            if item is not None:
                for i, input in enumerate(item.inputs):
                    if input is a:
                        aux = list(item.inputs)
                        aux[i] = b
                        item._inputs = tuple(aux)

    def _add_constant(self, value):
        if value not in self._constant_set:
            self._constant_set.add(value)
            self._constants[value] = len(self._constants)

    # L535
    def dump_ugens(self):
        # BUG: in sclang, some variables are not used.
        print(self.name)
        for ugen in self._children:
            inputs = None
            if ugen.inputs is not None:
                inputs = [x._dump_name() if isinstance(x, ugn.UGen)
                          else x for x in ugen.inputs]
            print([ugen._dump_name(), ugen.rate, inputs])

    # L549
    # // Make SynthDef available to all servers.
    def add(self, libname=None, completion_msg=None, keep_def=True):
        self.as_synthdesc(libname or 'default', keep_def)  # This call adds synthdesc to the lib as side effect which is the intended effect here.
        if libname is None:
            servers = srv.Server.all_booted_servers()
        else:
            servers = sdc.SynthDescLib.get_lib(libname).servers
        for server in servers:
            self._do_send(server, fn.value(completion_msg, server))  # BUG: Why each(server).value in sclang?

    # L645
    def as_synthdesc(self, libname='default', keep_def=True):
        stream = io.BytesIO(self.as_bytes())
        libname = libname or 'default'
        lib = sdc.SynthDescLib.get_lib(libname)
        desc = lib.read_desc_from_def(stream, keep_def, self, self.metadata)
        return desc

    # L587
    def _do_send(self, server, completion_msg):
        buffer = self.as_bytes()
        if len(buffer) < (65535 // 4):  # BUG: size limitation for rt safety, compare with ArrayedCollection:clumpBundles.
            server.send_msg('/d_recv', buffer, completion_msg)
        else:
            if server.is_local:
                _logger.warning(f'SynthDef {self.name} too big for sending. '
                                'Retrying via synthdef file')
                self._write_def_file(SynthDef.synthdef_dir)
                server.send_msg(
                    '/d_load',
                    str(SynthDef.synthdef_dir / (self.name + '.scsyndef')),
                    completion_msg)
            else:
                _logger.warning(f'SynthDef {self.name} too big for sending')

    def as_bytes(self):
        stream = io.BytesIO()
        self.write_def_list([self], stream)
        return stream.getbuffer()

    def _write_def_file(self, dir, overwrite=True, md_plugin=None):
        if not self.metadata.get('shouldNotSend', False):
            dir = dir or SynthDef.synthdef_dir
            dir = pathlib.Path(dir)
            file_existed_before = pathlib.Path(
                dir / (self.name + '.scsyndef')).exists()
            self._write_def_after_startup(self.name, dir, overwrite)
            if overwrite or not file_existed_before:
                desc = self.as_synthdesc()
                desc.metadata = self.metadata
                sdc.SynthDesc.populate_metadata_func(desc)
                desc.write_metadata(dir / self.name, md_plugin)

    def _write_def_after_startup(self, name, dir, overwrite=True): # TODO/BUG/WHATDA, este método es sclang Object:writeDefFile
        def defer_func():
            nonlocal name
            if name is None:
                raise Exception('missing SynthDef file name')
            else:
                name = pathlib.Path(dir / (name + '.scsyndef'))
                if overwrite or not name.exists():
                    with open(name, 'wb') as file:
                        sdc.AbstractMDPlugin.clear_metadata(name) # BUG: No está implementado
                        self.write_def_list([self], file)
        # // make sure the synth defs are written to the right path
        sac.StartUp.defer(defer_func) # BUG: No está implementada

    @staticmethod
    def write_def_list(lst, file):
        # This method is Collection-writeDef in sclang, is the only one
        # that creates the header. Called from as_bytes.
        file.write(b'SCgf')  # putString 'a null terminated String'
        file.write(struct.pack('>i', 2))  # putInt32(2); // file version
        file.write(struct.pack('>h', len(lst)))  # putInt16(this.size); // number of defs in file.
        for synthdef in lst:
            synthdef.write_def(file)

    def write_def(self, file):
        try:
            file.write(struct.pack('B', len(self.name))) # 01 putPascalString, unsigned int8 -> bytes
            file.write(bytes(self.name, 'ascii')) # 02 putPascalString

            self._write_constants(file)

            # //controls have been added by the Control UGens
            file.write(struct.pack('>i', len(self._controls)))  # putInt32
            for item in self._controls:
                file.write(struct.pack('>f', item)) # putFloat

            allcns_tmp = [x for x in self._all_control_names
                          if x.rate != 'noncontrol'] # reject
            file.write(struct.pack('>i', len(allcns_tmp))) # putInt32
            for item in allcns_tmp:
                # comprueba if (item.name.notNil) # TODO: posible BUG? (ver arriba _set_control_names). Pero no debería poder agregarse items sin no son ControlNames. Arrays anidados como argumentos, de más de un nivel, no están soportados porque fallar _set_control_names según analicé.
                #if item.name: # TODO: y acá solo comprueba que sea un string no vacío, pero no comprueba el typo ni de name ni de item.
                if not isinstance(item, scio.ControlName): # TODO: test para debugear luego.
                    raise Exception('ERROR: SynthDef self._all_control_names has non ControlName object')
                elif not item.name: # ídem.
                    raise Exception(f'ERROR: SynthDef self._all_control_names has empty ControlName object = {item.name}')
                file.write(struct.pack('B', len(item.name))) # 01 putPascalString, unsigned int8 -> bytes
                file.write(bytes(item.name, 'ascii')) # 02 putPascalString
                file.write(struct.pack('>i', item.index))

            file.write(struct.pack('>i', len(self._children)))  # putInt32
            for item in self._children:
                item._write_def(file)

            file.write(struct.pack('>h', len(self.variants))) # putInt16
            if len(self.variants) > 0:
                allcns_map = dict()
                for cn in allcns_tmp:
                    allcns_map[cn.name] = cn

                for varname, pairs in self.variants.items():
                    varname = self.name + '.' + varname
                    if len(varname) > 32:
                        _logger.warning(f"variant '{varname}' name too log, "
                                        "not writing more variants")
                        return False

                    varcontrols = self._controls[:]
                    for cname, values in pairs.items():
                        if allcns_map.keys().isdisjoint([cname]):
                            _logger.warning(f"control '{cname}' of variant "
                                            f"'{varname}' not found, not "
                                            "writing more variants")
                            return False

                        cn = allcns_map[cname]
                        values = utl.as_list(values)
                        if len(values) > len(utl.as_list(cn.default_value)):
                            _logger.warning(f"control: '{cname}' of variant: "
                                            f"'{varname}' size mismatch, not  "
                                            "writing more variants")
                            return False

                        index = cn.index
                        for i, val in enumerate(values):
                            varcontrols[index + i] = val

                    file.write(struct.pack('B', len(varname))) # 01 putPascalString, unsigned int8 -> bytes
                    file.write(bytes(varname, 'ascii')) # 02 putPascalString
                    for item in varcontrols:
                        file.write(struct.pack('>f', item)) # putFloat
            return True
        except Exception as e:
            raise Exception('SynthDef: could not write def') from e

    def _write_constants(self, file):
        size = len(self._constants)
        arr = [None] * size
        for value, index in self._constants.items():
            arr[index] = value
        file.write(struct.pack('>i', size)) # putInt32
        for item in arr:
            file.write(struct.pack('>f', item)) # putFloat

    # // Only write if no file exists
    def write_once(self, dir, md_plugin): # Nota: me quedo solo con el método de instancia, usar el método de clase es equivalente a crear una instancia sin llamar a add u otro método similar.
        self._write_def_file(dir, False, md_plugin)  # TODO: ver la documentación, este método es obsoleto.

    # L561
    @classmethod
    def remove_at(cls, name, libname='default'):  # *** BUG: Este método es de dudosa utilidad para SynthDef en core.
        lib = sdc.SynthDescLib.get_lib(libname)
        lib.remove_at(name)
        for server in lib.servers:
            server.send_msg('/d_free', name) # BUG: no entiendo por qué usa server.value (que retorna el objeto server). Además, send_msg también es método de String en sclang lo que resulta confuso.

    # L570
    # // Methods for special optimizations

    # // Only send to servers.
    def send(self, server=None, completion_msg=None):
        servers = utl.as_list(server or srv.Server.all_booted_servers())
        for server in servers:
            if not server.has_booted:
                _logger.warning(f"Server '{server.name}' not running, "  # *** BUG in sclang: prints server.name instead of each.name
                                "could not send SynthDef")
            if self.metadata.get('shouldNotSend', False):
                self._load_reconstructed(
                    server, fn.value(completion_msg, server))
            else:
                self._do_send(server, fn.value(completion_msg, server))

    # L653
    # // This method warns and does not halt because loading existing def from
    # // disk is a viable alternative to get the synthdef to the server.
    def _load_reconstructed(self, server, completion_msg):
        _logger.warning(f"SynthDef '{self.name}' was reconstructed from a "
                        ".scsyndef file, it does not contain all the required "
                        "structure to send back to the server")
        if server.is_local:
            _logger.warning(f"loading from disk instead for Server '{server}'")
            bundle = ['/d_load', self.metadata['loadPath'], completion_msg]
            server.send_bundle(None, bundle)
        else:
            raise Exception(f"Server '{server}' is remote, "
                            "cannot load from disk")

    # // Send to server and write file.
    def load(self, server, completion_msg=None, dir=None):
        server = server or srv.Server.default
        completion_msg = fn.value(completion_msg, server)
        if self.metadata.get('shouldNotSend', False):
            self._load_reconstructed(server, completion_msg)
        else:
            # // should remember what dir synthDef was written to
            dir = dir or SynthDef.synthdef_dir
            dir = pathlib.Path(dir)
            self._write_def_file(dir)
            server.send_msg(
                '/d_load', str(dir / (self.name + '.scsyndef')), completion_msg)

    # L615
    # // Write to file and make synth description.
    def store(self, libname='default', dir=None, completion_msg=None,
              md_plugin=None):
        lib = sdc.SynthDescLib.get_lib(libname)
        dir = dir or SynthDef.synthdef_dir
        dir = pathlib.Path(dir)
        path = dir / (self.name + '.scsyndef')
        if not self.metadata.get('shouldNotSend', False):
            with open(path, 'wb') as file:
                self.write_def_list([self], file)
            lib.read(path)
            for server in lib.servers:
                self._do_send(server, fn.value(completion_msg, server))  # BUG: Why server.value
            desc = lib.at(self.name)
            desc.metadata = self.metadata
            sdc.SynthDesc.populate_metadata_func(desc)
            desc.write_metadata(path, md_plugin)
        else:
            lib.read(path)
            for server in lib.servers:
                self._load_reconstructed(
                    server, fn.value(completion_msg, server))

    # L670
    # // This method needs a reconsideration
    def store_once(self, libname='default', dir=None, completion_msg=None,
                   md_plugin=None):
        dir = dir or SynthDef.synthdef_dir
        dir = pathlib.Path(dir)
        path = dir / (self.name + '.scsyndef')
        if not path.exists():
            self.store(libname, dir, completion_msg, md_plugin)
        else:
            # // load synthdesc from disk
            # // because SynthDescLib still needs to have the info
            lib = sdc.SynthDescLib.get_lib(libname)
            lib.read(path)

    # L683
    def play(self, target, args, add_action='addToHead'):
        raise Exception('SynthDef.play no está implementada') # BUG: esta función de deprecated y des-deprecated

    # def store_args(self):

    # canFreeSynth.sc Is an added interface used at least by JITlib and wslib.
    # It adds too much to core, better to find another non instrusive way.
    # can_release_synth Is used by GraphBuilder.sc for automatic outputs
    # creation (e.g. in {}.play) with *wrapOut in Function-asSynthDef.
    # hasGateControl Used in canReleaseSynth.


# decorator syntax
class synthdef():
    '''Clase para ser usada como decorador y espacio de nombres de decoradores,
    decoradores para ser usados simplemente como atajo sintáctico de las
    funciones más comunes, instancia sin y con parámetros y add.

    @synthdef
    def synth1():
        pass

    @synthdef.params(
        rates=[],
        variants={},
        metadata={})
    def synth2():
        pass

    @synthdef.add()
    def synth3():
        pass
    '''

    def __new__(cls, graph_func):
        return SynthDef(graph_func.__name__, graph_func)

    @staticmethod
    def params(rates=None, prepend_args=None, variants=None, metadata=None):
        def make_def(graph_func):
            return SynthDef(graph_func.__name__, graph_func,
                            rates, prepend_args, variants, metadata)
        return make_def

    @staticmethod
    def add(libname=None, completion_msg=None, keep_def=True):
        '''Es atajo solo para add, la SynthDef se construye con los parametros
        por defecto, el caso más simple, si se quieren más parámetros no tiene
        sentido agregar todo acá, se crea con params y luego se llama a add.
        De lo contrario el atajo termina siendo más largo y menos claro.'''
        def make_def(graph_func):
            sdef = synthdef(graph_func)
            sdef.add(libname, completion_msg, keep_def)
            return sdef
        return make_def
