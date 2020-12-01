"""SynthDef.sc"""

import inspect
import logging
import io
import pathlib
from collections.abc import Container

from ..base import classlibrary as clb
from ..base import utils as utl
from ..base import platform as plf
from ..base import systemactions as sac
from ..base import functions as fn
from ..base import main as _libsc3
from . import spec as spc
from . import ugen as ugn
from . import server as srv
from . import synthdesc as sdc
from . import _fmtrw as frw
from . import _graphparam as gpp
from . import node as nod
from .ugens import inout as iou
from .ugens import fftunpacking as ffu


__all__ = ['SynthDef', 'synthdef']


_logger = logging.getLogger(__name__)


class MetaSynthDef(type):
    tmp_name_prefix = 'tmp__'
    _tmp_def_count = 0

    def __init__(cls, *_):

        def init_func(cls):
            # // Ensure exists.
            if not plf.Platform.support_dir.exists():
                _logger.info(
                    'creating Platform.support_dir '
                    f'at {plf.Platform.support_dir}')
            plf.Platform.synthdef_dir.mkdir(parents=True, exist_ok=True)

        clb.ClassLibrary.add(cls, init_func)

    def generate_tmp_name(cls):
        name = cls.tmp_name_prefix + str(cls._tmp_def_count)
        cls._tmp_def_count += 1
        return name


class SynthDef(metaclass=MetaSynthDef):
    """Build the instructions to create synthesis nodes in the server.

    SynthDef instances build the instructions to create synthesis nodes
    in the server from a function containing interconnected UGen objects.
    In order for the server to have the synthesis definition available it
    should be sent using ``add``, ``load``, ``send`` or ``store`` methods.

    Parameters
    ----------
    name : str
        The name of the synthesis definition used by the server
        to create synth nodes.
    func: function
        A common function containing UGen objects.
    rates : list
        An optional list of rate specifications that map to
        the ``func`` defined parameters. If value is `None` (default)
        control rate instances will be created instead. Possible
        values are `'ar'`, `'kr'`, `'ir'`, `'tr'` or a number
        (indicating lag value for `'kr'` controls). This parameter
        overrides rates defined by function annotations.
    prepend : list
        An optional list of positional values that will be
        passed to ``func`` when evaluated. This prevents controls
        from being created for those parameters.
    variants : dict
        An optional dictionary with different keys that specify
        dictionaries of default values to create synthesis nodes
        in the server. When using variants, synthesis definition
        names are composed as `'synthname.variantkey'`.
    metadata : dict
        An user defined JSON serializable dictionary to
        provide information about the synthesis definition.
    """

    _SUFFIX = 'scsyndef'
    _RATE_NAMES = ('ar', 'kr', 'ir', 'tr')

    @classmethod
    def _dummy(cls, name):
        # Creates an empty object used by SynthDesc.
        obj = cls.__new__(cls)

        obj._name = name
        obj._func = None
        obj._variants = dict()
        obj.metadata = dict()
        obj.desc = None
        obj._bytes = None

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

    def __init__(self, name, func, rates=None, prepend=None,
                 variants=None, metadata=None):
        self._name = name
        self._func = None
        self._variants = variants or dict()
        self.metadata = metadata or dict()
        self.desc = None
        self._bytes = None

        # self._controls = None  # init_build, is set by ugens using _libsc3.main._current_synthdef
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
        self._rewrite_in_progress = False

        # callable interface
        # self._callable_args = None

        self._build(func, rates or [], prepend or [])

    def _build(self, func, rates, prepend):
        with _libsc3.main._def_build_lock:
            try:
                _libsc3.main._current_synthdef = self
                self._init_build()
                self._build_ugen_graph(func, rates, prepend)
                self._finish_build()
                self._func = func
                _libsc3.main._current_synthdef = None
            except Exception:
                _libsc3.main._current_synthdef = None
                raise

    @property
    def name(self):
        return self._name

    @property
    def func(self):
        return self._func

    @property
    def variants(self):
        return self._variants

    @classmethod
    def wrap(cls, func, rates=None, prepend=None):
        if _libsc3.main._current_synthdef is not None:
            return _libsc3.main._current_synthdef._build_ugen_graph(
                func, rates or [], prepend or [])
        else:
            raise Exception(
                'SynthDef wrap should be called inside '
                'a SynthDef graph function')

    def _init_build(self):
        # UGen.buildSynthDef, lock above.
        self._constants = dict()
        self._constant_set = set()
        self._controls = []
        self._control_index = 0
        self._max_local_bufs = None

    def _build_ugen_graph(self, func, rates, prepend):
        # // Save/restore controls in case of SynthDef.wrap.
        save_ctl_names = self._control_names
        self._control_names = []
        prepend = utl.as_list(prepend)
        self._args_to_controls(func, rates, len(prepend))
        result = func(*(prepend + self._build_controls()))
        self._control_names = save_ctl_names
        return result

    def _args_to_controls(self, func, rates, skip_args=0):  # Was addControlsFromArgsOfFunc.
        if not inspect.isfunction(func):
            raise TypeError('func argument is not a function')

        sig = inspect.signature(func)
        self._callable_args = list(sig.parameters.keys())
        params = list(sig.parameters.values())

        if not params:
            return

        pork = inspect.Parameter.POSITIONAL_OR_KEYWORD
        for p in params:
            if p.kind != pork:
                raise ValueError(
                    'all func parameters must be POSITIONAL_OR_KEYWORD')

        for p in params[skip_args:]:
            if isinstance(p.default, tuple)\
            and any(isinstance(v, Container) for v in p.default):
                raise ValueError(f"tuple rank > 1 for parameter '{p.name}'")

        # // What we do here is separate the ir, tr and kr rate arguments,
        # // create one Control ugen for all of each rate, and then construct
        # // the argument array from combining the OutputProxies of these two
        # // Control ugens in the original order.
        names = [x.name for x in params]
        names = names[skip_args:]
        values = self._get_valid_arg_values(params)
        values = values[skip_args:]
        values = self._apply_metadata_specs(names, values)

        empty = inspect.Signature.empty
        annotations = [
            x.annotation if x.annotation != empty else None for x in params]
        annotations = annotations[skip_args:]

        rates += [0] * (len(names) - len(rates))
        rates = [x if x is not None else 0.0 for x in rates]

        rate_names = self._RATE_NAMES

        for a in annotations:
            if a is not None and a not in rate_names:
                raise ValueError(
                    f'rate annotation {repr(a)} not in {rate_names}')

        for i, name in enumerate(names):
            value = values[i]
            annot = annotations[i]
            lag = rates[i]

            if annot and annot != 'kr'\
            and isinstance(lag, (int, float)) and lag != 0:
                _logger.warning(
                    f"lag value {lag} for '{annot}' parameter "
                    f"'{name}' will be ignored")

            overridden = lag in rate_names

            if lag == 'ir' or annot == 'ir' and not overridden:
                self._add_ir(name, value)
            elif lag == 'tr' or annot == 'tr' and not overridden:
                self._add_tr(name, value)
            elif lag == 'ar' or annot == 'ar' and not overridden:
                self._add_ar(name, value)
            else:
                if lag == 'kr': lag = 0.0
                self._add_kr(name, value, lag)

    def _get_valid_arg_values(self, params):
        valid_args = (int, float, bool, complex, type(None))  # + tuple
        ret = []
        empty = inspect.Signature.empty
        for param in params:
            if param.default != empty:
                if isinstance(param.default, valid_args):
                    ret.append(param.default)
                elif isinstance(param.default, tuple):
                    ret.append(list(param.default))
                else:
                    _logger.warning(
                        "invalid value as default argument, "
                        f"'{param.default}' replaced by None")
                    ret.append(None)
            else:
                ret.append(None)
        return ret

    def _apply_metadata_specs(self, names, values):
        # This method depends on MdPlugin 'specs' key.
        # I'm not sure if SynthDef is the right place for it
        # but it's called when building the definition and may add
        # a default value for control parameters if they are None.
        new_values = []
        if 'specs' in self.metadata:
            specs = self.metadata['specs']
            for i, value in enumerate(values):
                if value is not None:
                    new_values.append(value)
                else:
                    if names[i] in specs:
                        new_values.append(specs[names[i]].default)
                    else:
                        new_values.append(0.0)
        else:
            new_values = [x if x is not None else 0.0 for x in values]
        return new_values

    # // Allow incremental building of controls.
    # BUG, BUG: de cada parámetro value hace value.copy, ver posibles consecuencias...
    def _add_non_control(self, name, values):  # Not used in the standard library.
        self._add_control_name(iou.ControlName(name, None, 'noncontrol',
            values, len(self._control_names)))

    def _add_ir(self, name, values):  # *** VER dice VALUES en plural, pero salvo que se pase un array como valor todos los que calcula son escalares u objetos no iterables.
        self._add_control_name(iou.ControlName(name, len(self._controls), 'scalar',
            values, len(self._control_names)))  # values *** VER el argumento de ControlName es defaultValue que puede ser un array para expansión multicanal de controles, pero eso puede pasar acá saliendo de los argumentos?

    def _add_tr(self, name, values):
        self._add_control_name(iou.ControlName(name, len(self._controls), 'trigger',
            values, len(self._control_names)))

    def _add_ar(self, name, values):
        self._add_control_name(iou.ControlName(name, len(self._controls), 'audio',
            values, len(self._control_names)))

    def _add_kr(self, name, values, lags):  # Acá también dice lags en plural pero es un valor simple como string (symbol) o number según interpreto del código anterior.
        self._add_control_name(iou.ControlName(name, len(self._controls), 'control',
            values, len(self._control_names), lags))

    def _add_control_name(self, cn):
        self._control_names.append(cn)
        self._all_control_names.append(cn)

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

        build_ita_controls(ir_cns, iou.Control, 'ir')
        build_ita_controls(tr_cns, iou.TrigControl, 'kr')
        build_ita_controls(ar_cns, iou.AudioControl, 'ar')

        if kr_cns:
            values = []
            lags = []
            for cn in kr_cns:
                values.append(cn.default_value)
                valsize = len(utl.as_list(cn.default_value))
                if valsize > 1:
                    lags.extend(utl.wrap_extend(utl.as_list(cn.lag), valsize))
                else:
                    lags.append(cn.lag)
            index = self._control_index

            if any(x != 0 for x in lags):
                ctrl_ugens = iou.LagControl.kr(utl.flat(values), lags)  # LagControl.kr(values.flat, lags) //.asArray.reshapeLike(values);
            else:
                ctrl_ugens = iou.Control.kr(utl.flat(values))  # Control.kr(values.flat)
            ctrl_ugens = utl.as_list(ctrl_ugens) # .asArray
            ctrl_ugens = utl.reshape_like(ctrl_ugens, values)  # .reshapeLike(values);

            for i, cn in enumerate(kr_cns):
                cn.index = index
                index += len(utl.as_list(cn.default_value))
                arguments[cn.arg_num] = ctrl_ugens[i]
                self._set_control_names(ctrl_ugens[i], cn)

        self._control_names = [
            x for x in self._control_names if x.rate != 'noncontrol']
        return arguments

    def _set_control_names(self, ctrl_ugens, cn):
        if isinstance(ctrl_ugens, list):
            for ctrl_ugen in ctrl_ugens:
                ctrl_ugen.name = cn.name
        else:
            ctrl_ugens.name = cn.name

    def _finish_build(self):
        self._add_copies_if_needed()  # ping, only for WidthFirstUGen ugens.
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


    # OC: Multi channel expansion causes a non optimal breadth-wise
    # ordering of the graph. The topological sort below follows
    # branches in a depth first order, so that cache performance
    # of connection buffers is optimized.

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
            # // All ugens with no antecedents are made available.
            ugen._make_available()

    def _index_ugens(self):
        for i, ugen in enumerate(self._children):
            ugen._synth_index = i

    def _collect_constants(self):  # ping
        for ugen in self._children:
            ugen._collect_constants()  # pong

    def _check_inputs(self):  # ping
        first_err = None
        for ugen in self._children:
            err = ugen._check_inputs() # pong, en sclang devuelve nil o un string, creo que esos serían todos los casos según la lógica de este bloque.
            if err: # *** TODO EN SCLANG ES ASIGNA A err Y COMPRUEBA notNil, acá puede ser none, pero ver qué retornan de manera sistemática, ver return acá abajo.
                # err = ugen.class.asString + err;
                # err.postln;
                # ugen._dump_args
                if first_err is None:
                    first_err = ugen.name + ' ' + err
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


    # // UGens do these (ping pong methods).

    def _add_ugen(self, ugen):
        if not self._rewrite_in_progress:
            ugen._synth_index = len(self._children)
            ugen._width_first_antecedents = self._width_first_ugens[:]
            self._children.append(ugen)

    def _remove_ugen(self, ugen):
        # // Lazy removal: clear entry and later remove all None entries.
        self._children[ugen._synth_index] = None

    def _replace_ugen(self, a, b):
        if not isinstance(b, ugn.SynthObject):
            raise Exception('_replace_ugen assumes a SynthObject')

        b._width_first_antecedents = a._width_first_antecedents
        b._descendants = a._descendants
        b._synth_index = a._synth_index
        self._children[a._synth_index] = b

        for item in self._children:
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

    def dump_ugens(self):
        """Print the generated graph instructions in a human readable way."""

        print(self._name)
        for ugen in self._children:
            inputs = None
            if ugen.inputs is not None:
                inputs = [
                    x._dump_name() if isinstance(x, ugn.SynthObject)
                    else x for x in ugen.inputs]
            print([ugen._dump_name(), ugen.rate, inputs])

    def add(self, libname=None, completion_msg=None, keep_def=True):
        """Send the definition to the servers and keep a description.

        Adds the synthesis definition to the SynthDescLib specified by
        ``libname`` and sends it to the library's registered servers.
        All operations take place in memory (no scsyndef file is written).
        This method is used for most cases.

        Parameters
        ----------
        libname : str
            SynthDescLib library name. If not specified `'default'` will
            be used.
        completion_msg : function
            A function that receives a server as argument and return an OSC
            message. This message will be executed in the server after the
            definition is loaded.
        keep_def : bool
            A flag indicating if the function's code will be kept in the
            SynthDesc object, default value is `True`.
        """

        # // Make SynthDef available to all servers.
        desc = sdc.SynthDesc.new_from(self, keep_def)
        if libname is None:
            sdc.SynthDescLib.get_lib('default').add(desc)
            servers = set(
                s for s in srv.Server.all if s._status_watcher.has_booted)
        else:
            lib = sdc.SynthDescLib.get_lib(libname)
            lib.add(desc)
            servers = lib.servers
        for server in servers:
            self._do_send(server, fn.value(completion_msg, server))

    def _do_send(self, server, completion_msg):
        buffer = self.as_bytes()
        if len(buffer) < (65535 // 4):  # BUG: size limitation for rt safety, compare with ArrayedCollection:clumpBundles.
            server.send_msg('/d_recv', buffer, completion_msg)
        else:
            if server.is_local:
                _logger.warning(
                    f'SynthDef {self._name} too big for sending. '
                    'Retrying via synthdef file')
                self._write_def_file(plf.Platform.tmp_dir)
                server.send_msg(
                    '/d_load',
                    str(plf.Platform.tmp_dir / f'{self._name}.{self._SUFFIX}'),
                    completion_msg)
            else:
                _logger.warning(f'SynthDef {self._name} too big for sending')

    def as_bytes(self):
        """Binary format of the synthesis definition."""

        if self._bytes is None:
            stream = io.BytesIO()
            self._write_def_list([self], stream)
            self._bytes = stream.getbuffer()
        return self._bytes

    def _write_def_file(self, dir, overwrite=True, md_plugin=None):
        if not self.metadata.get('reconstructed', False):
            dir = dir or plf.Platform.synthdef_dir
            dir = pathlib.Path(dir)
            path = dir / f'{self._name}.{self._SUFFIX}'
            if overwrite or not path.exists():
                with open(path, 'wb') as file:
                    self._write_def_list([self], file)
                desc = sdc.SynthDesc.new_from(self)
                sdc.SynthDesc.populate_metadata_func(desc)
                desc.write_metadata(dir, md_plugin)
                sdc.SynthDescLib.get_lib('default').add(desc)

    @staticmethod
    def _write_def_list(lst, file):
        # This method is Collection-writeDef in sclang, is the only one
        # that creates the header. Called from as_bytes.
        file.write(b'SCgf')  # putString 'a null terminated String'
        frw.write_i32(file, 2)  # // file version
        frw.write_i16(file, len(lst))  # // number of defs in file.
        for synthdef in lst:
            synthdef._write_def(file)

    def _write_def(self, file):
        try:
            frw.write_pascal_str(file, self._name)
            self._write_constants(file)

            # // Controls have been added by the Control UGens.
            frw.write_i32(file, len(self._controls))
            for item in self._controls:
                frw.write_f32(file, item)

            allcns_tmp = [
                x for x in self._all_control_names if x.rate != 'noncontrol']
            frw.write_i32(file, len(allcns_tmp))
            for item in allcns_tmp:
                # comprueba if (item.name.notNil) # TODO: posible BUG? (ver arriba _set_control_names). Pero no debería poder agregarse items sin no son ControlNames. Arrays anidados como argumentos, de más de un nivel, no están soportados porque fallar _set_control_names según analicé.
                #if item.name: # TODO: y acá solo comprueba que sea un string no vacío, pero no comprueba el typo ni de name ni de item.
                if not isinstance(item, iou.ControlName): # TODO: test para debugear luego.
                    raise Exception(
                        'SynthDef self._all_control_names '
                        'has non ControlName object')
                elif not item.name: # ídem.
                    raise Exception(
                        'SynthDef self._all_control_names has '
                        f'empty ControlName object = {item.name}')
                frw.write_pascal_str(file, item.name)
                frw.write_i32(file, item.index)

            frw.write_i32(file, len(self._children))
            for item in self._children:
                item._write_def(file)

            frw.write_i16(file, len(self._variants))
            if len(self._variants) > 0:
                allcns_map = dict()
                for cn in allcns_tmp:
                    allcns_map[cn.name] = cn

                for varname, pairs in self._variants.items():
                    varname = self._name + '.' + varname
                    if len(varname) > 32:
                        _logger.warning(
                            f"variant '{varname}' name too log, "
                            "not writing more variants")
                        return False

                    varcontrols = self._controls[:]
                    for cname, values in pairs.items():
                        if allcns_map.keys().isdisjoint([cname]):
                            _logger.warning(
                                f"control '{cname}' of variant '{varname}' "
                                "not found, not writing more variants")
                            return False

                        cn = allcns_map[cname]
                        values = utl.as_list(values)
                        if len(values) > len(utl.as_list(cn.default_value)):
                            _logger.warning(
                                f"control: '{cname}' of variant: '{varname}' "
                                "size mismatch, not writing more variants")
                            return False

                        index = cn.index
                        for i, val in enumerate(values):
                            varcontrols[index + i] = val

                    frw.write_pascal_str(file, varname)
                    for item in varcontrols:
                        frw.write_f32(file, item)
            return True
        except Exception as e:
            raise Exception('SynthDef: could not write def') from e

    def _write_constants(self, file):
        size = len(self._constants)
        arr = [None] * size
        for value, index in self._constants.items():
            arr[index] = value
        frw.write_i32(file, size)
        for item in arr:
            frw.write_f32(file, item)

    # writeOnce, removed, see documentation.
    # removeAt, discarded, use SynthDescLib directly.


    # // Methods for special optimizations.

    def send(self, server=None, completion_msg=None):
        """Send the definition to the server.

        Parameters
        ----------
        server : Server | list
            A single server object or list.
        completion_msg : function
            A function that receives a server as argument and return an OSC
            message. This message will be executed in the server after the
            definition is loaded.
        """

        # // Only send to servers.
        if server is None:
            servers = list(
                s for s in srv.Server.all if s._status_watcher.has_booted)
        else:
            servers = utl.as_list(server)
        for server in servers:
            if not server._status_watcher.has_booted:
                _logger.warning(
                    f"Server '{server.name}' not running, "  # *** BUG in sclang: prints server.name instead of each.name
                    "could not send SynthDef")
            if self.metadata.get('reconstructed', False):
                self._load_reconstructed(
                    server, fn.value(completion_msg, server))
            else:
                self._do_send(server, fn.value(completion_msg, server))

    def _load_reconstructed(self, server, completion_msg):
        # // This method warns and does not halt because
        # // loading existing def from disk is a viable
        # // alternative to get the synthdef to the server.
        _logger.warning(
            f"SynthDef '{self._name}' was reconstructed from a "
            f"{self._SUFFIX} file, it does not contain all the "
            "required structure to send back to the server")
        if server.is_local:
            _logger.warning(f"loading from disk instead for Server '{server}'")
            bundle = ['/d_load', self.metadata['load_path'], completion_msg]
            server.send_bundle(None, bundle)
        else:
            raise Exception(
                f"Server '{server}' is remote, cannot load from disk")

    def load(self, server, completion_msg=None, dir=None):
        """Write the definition to a file that is loaded from the server.

        This method is used for definitions too large to be sent over UDP.

        Parameters
        ----------
        server : Server | list
            A single server object or list.
        completion_msg : function
            A function that receives a server as argument and return an OSC
            message. This message will be executed in the server after the
            definition is loaded.
        dir : str | pathlib.Path
            Directory in which the file is saved, if not specified
            platform's default directory is used.
        """

        server = server or srv.Server.default
        completion_msg = fn.value(completion_msg, server)
        if self.metadata.get('reconstructed', False):
            self._load_reconstructed(server, completion_msg)
        else:
            # // Should remember what dir synthDef was written to.
            dir = dir or plf.Platform.synthdef_dir
            dir = pathlib.Path(dir)
            self._write_def_file(dir)
            server.send_msg(
                '/d_load', str(dir / f'{self._name}.{self._SUFFIX}'),
                completion_msg)

    def store(self, libname='default', dir=None, completion_msg=None,
              md_plugin=None):
        """Add a description, write the definition to disk and send
        it to the registered servers.

        Similar to ``add`` but write to disk.

        Parameters
        ----------
        libname : str
            SynthDescLib library name. If not specified `'default'` will
            be used.
        dir : str | pathlib.Path
            Directory in which the file is saved, if not specified
            platform's default directory is used.
        completion_msg : function
            A function that receives a server as argument and return an OSC
            message. This message will be executed in the server after the
            definition is loaded.
        md_plugin :
            TODO: Not defined yet.
        """

        # // Write to file and make synth description.
        lib = sdc.SynthDescLib.get_lib(libname)
        dir = dir or plf.Platform.synthdef_dir
        dir = pathlib.Path(dir)
        path = dir / f'{self._name}.{self._SUFFIX}'
        if not self.metadata.get('reconstructed', False):
            with open(path, 'wb') as file:
                self._write_def_list([self], file)
            desc = sdc.SynthDesc.new_from(self)
            desc.metadata = self.metadata
            sdc.SynthDesc.populate_metadata_func(desc)
            desc.write_metadata(dir, md_plugin)
            lib.add(desc)
            for server in lib.servers:
                self._do_send(server, fn.value(completion_msg, server))
        else:
            lib.read(path)
            for server in lib.servers:
                self._load_reconstructed(
                    server, fn.value(completion_msg, server))

    # def store_once(self, libname='default', dir=None, completion_msg=None,
    #                md_plugin=None):
    #     # // This method needs a reconsideration.
    #     dir = dir or plf.Platform.synthdef_dir
    #     dir = pathlib.Path(dir)
    #     path = dir / f'{self._name}.{self._SUFFIX}'
    #     if not path.exists():
    #         self.store(libname, dir, completion_msg, md_plugin)
    #     else:
    #         # // Load synthdesc from disk because
    #         # // SynthDescLib still needs to have the info.
    #         lib = sdc.SynthDescLib.get_lib(libname)
    #         lib.read(path)

    # play
    # def store_args(self):

    # canFreeSynth.sc Is an added interface used at least by JITlib and wslib.
    # It adds too much to core, better to find another non instrusive way.
    # can_release_synth Is used by GraphBuilder.sc for automatic outputs
    # creation (e.g. in {}.play) with *wrapOut in Function-asSynthDef.
    # hasGateControl Used in canReleaseSynth.

    def __call__(self, *args, target=None, add_action='addToHead',
                 register=False, **kwargs):
        # NOTE: kwargs can duplicate args.
        arg_list = [v for p in zip(self._callable_args, args) for v in p]
        arg_list += [v for p in kwargs.items() for v in p]
        with gpp.node_param(target)._as_target().server.bind():
            return nod.Synth(self.name, arg_list, target, add_action, register)


### Decorator syntax ###

def _create_synthdef(func, **kwargs):
    sdef = SynthDef(func.__name__, func, **kwargs)
    sdef.add()  # Running servers or offline patterns.
    sac.ServerBoot.add('all', lambda server: sdef.add())  # Next boot.
    return sdef

def synthdef(func=None, **kwargs):
    """Decorator function to build and add definitions.

    The name of the decorated function becomes the name of the
    definition. After instantiation the `add` method is called
    and is also set to be called at subsequent server's boot.

    It can be used with optional keyword only arguments.

    Examples
    --------
    ::

        @synthdef
        def test(freq=440, amp=0.1, pan=0, gate=1):
            sig = SinOsc(freq) * amp
            sig *= EnvGen(Env.asr(), gate)
            Out(0, Pan2(sig, pan))

        # Same as:

        def test(freq=440, amp=0.1, pan=0, gate=1):
            ...

        sd = SynthDef('test', test)
        sd.add()

        # With arguments:

        @synthdef(rates=[0.02, 0.02], variants={'low': {'freq': 110}})
        def test(freq=440, amp=0.1, pan=0, gate=1):
            ...

        # Same as:

        def test(freq=440, amp=0.1, pan=0, gate=1):
            ...

        sd = SynthDef('test', test, [0.02, 0.02], None, {'low': {'freq': 110}})
        sd.add()

    """

    if func is None:
        # action: 'load', 'send', 'store', 'add'? (needs kwargs filtering).
        return lambda func: _create_synthdef(func, **kwargs)
    else:
        return _create_synthdef(func)
