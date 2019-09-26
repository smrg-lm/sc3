
from abc import ABC, abstractmethod
import threading
import atexit

import liblo as _lo

from . import main as _libsc3
from . import utils as utl
from . import netaddr as nad
from . import responsedefs as rdf
from ..seq import clock as clk
from ..seq import stream as stm


class AbstractOSCInteface(ABC):
    def __init__(self, client_port=57120, protocol='udp', port_range=10):
        '''proto es 'udp' o 'tcp', algunos servidores pueden usar abmos.'''
        self._port = client_port
        self._protocol = protocol
        self._port_range = port_range
        self._recv_functions = set()
        self._running = False

    @property
    def port(self):
        return self._port

    @property
    def protocol(self):
        return self._protocol

    @property
    def port_range(self):
        return self._port_range

    @property
    def recv_functions(self):
        return self._recv_functions

    def add_recv_func(self, func):
        self._recv_functions.add(func)  # functions are/should be evaluated in AppClock.

    def remove_recv_func(self, func):
        self._recv_functions.remove(func)

    def running(self):
        return self._running

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def send_msg(self, target, *args):
        '''args es la lista de valores para crear un mensaje'''
        pass

    @abstractmethod
    def send_bundle(self, target, time, *args):
        '''args son listas de valores para crear varios mensajes'''
        pass

    def sync(self, target, condition=None, bundle=None, latency=0): # BUG: dice array of bundles, los métodos bundle_size y send_bundle solo pueden enviar uno. No me cierra/me confunde en sclang porque usa send bundle agregándole latencia.
        condition = condition or stm.Condition()
        if bundle is None:
            id = self._make_sync_responder(target, condition)
            self.send_bundle(target, latency, ['/sync', id])
            yield from condition.wait()
        else:
            # BUG: esto no está bien testeado, y acarreo el problema del tamaño exacto de los mensajes.
            sync_size = self.msg_size(['/sync', utl.UniqueID.next()])
            max_size = 65500 - sync_size # BUG: 65500 es un límite práctico que puede estar mal si las cuentas de abajo están mal.
            if self.bundle_size(bundle) > max_size:
                clumped_bundles = self.clump_bundle(bundle, max_size)
                for item in clumped_bundles:
                    id = self._make_sync_responder(target, condition)
                    item.append(['/sync', id])
                    self.send_bundle(target, latency, *item)
                    latency += 1e-9 # nanosecond, TODO: esto lo hace así no sé por qué.
                    yield from condition.wait()
            else:
                id = self._make_sync_responder(target, condition)
                bundle = bundle[:]
                bundle.append(['/sync', id])
                self.send_bundle(target, latency, *bundle)
                yield from condition.wait()

    def _make_sync_responder(self, target, condition):
        id = utl.UniqueID.next()

        def resp_func(msg, *args):
            if msg[1] == id:
                resp.free()
                condition.test = True
                condition.signal()

        resp = rdf.OSCFunc(
            resp_func, '/synced',
            nad.NetAddr(target[0], target[1]))
        return id

    # NOTE: Importante, lo usa para enviar paquetes muy grandes como stream,
    # liblo tira error y no envía.
    def clump_bundle(self, msg_list, new_bundle_size): # msg_list siempre es un solo bundle [['/path', arg1, arg2, ..., argN], ['/path', arg1, arg2, ..., argN], ...]
        ret = [[]]
        clump_count = 0
        acc_size = 0
        aux = 0
        for item in msg_list:
            aux = self.msg_size(item)
            if acc_size + aux > new_bundle_size: # BUG: 65500 es un límite práctico que puede estar mal si las cuentas de abajo están mal.
                acc_size = aux
                clump_count += 1
                ret.append([])
                ret[clump_count].append(item)
            else:
                acc_size += aux
                ret[clump_count].append(item)
        if len(ret[0]) == 0: ret.pop(0)
        return ret

    def msg_size(self, arg_list): # arg_list siempre es ['/path', arg1, arg2, ..., argN]
        size = 0 # bytes
        typetags = -1 # path no cuenta
        aux = 0 # solo inicializo porque se usa dentro del loop
        for item in arg_list:
            t = type(item)
            if t is str:
                aux = len(item)
                mod4 = aux & 3 # aux % 4
                size += aux
                if mod4:
                    size += 4 - mod4 # alineamiento
                else:
                    size += 4 # null y alineamiento
            elif t is bytes:
                aux = 4 # size count
                aux += len(item)
                mod4 = aux & 3 # aux % 4
                size += aux
                if mod4:
                    size += 4 - mod4 # alineamiento
            elif t is int or t is float or t is tuple:
                size += 4 # BUG: 8 si se usan doubles
            else:
                raise TypeError('invalid type ({}) for OSC message'.format(t)) # BUG: pueden haber tipos de datos que son válidos porque liblo traduce después?
            typetags += 1
        size += 1 # 1 byte para la ',' del type tag
        size += typetags # type tag por cada argumento osc
        mod4 = (1 + typetags) & 3 # (1 + typetags) % 4
        if mod4:
            size += 4 - mod4 # alienamiento
        return size # bytes # + 12 # BUG: falta algo, acá se pueden sumar 12 por: 8 bytes udp (BUG: depende de proto) header, 20 bits (redondeado a 4 bytes con alineamiento aunque no se si corresponde) ip header, igual me faltan alrededor de 20 bytes entre msg y bundle, salvo que sea algo dinámico y me falen más. En sclang hay una nota que justo son 20 bytes: // 65515 = 65535 - 16 - 4 (sync msg size)

    def bundle_size(self, args): # args siempre es [['/path', arg1, arg2, ..., argN], ['/path', arg1, arg2, ..., argN], ...]
        size = 0
        for item in args:
            size += self.msg_size(item)
        return size + 40 # bytes # BUG: 8 bytes para '#bundle', 8 para time tag, 4 para el tamaño del atado, pero la cuenta en msg está mal, falta(n) algo(s). Y creo que los mensajes pueden tener distinto formato, no me quedó claro.


class LOInterface(AbstractOSCInteface):
    def start(self):
        if self._running:
            return

        def recv(*msg):
            _libsc3.main.update_logical_time()

            time = _libsc3.main.elapsed_time()
            addr = nad.NetAddr(msg[3].hostname, msg[3].port)
            arr = [msg[0]]
            arr.extend(msg[1])

            def sched_func():
                for func in self.recv_functions:
                     func(arr, time, addr, self.port)

            clk.AppClock.sched(0, sched_func)  # NOTE: Lo envía al thread de AppClock que es seguro.

        def start_handler(*msg):
            pass

        def end_handler(*msg):
            pass

        def init():
            data_object = dict()  # not used, is msg[4]

            if self.protocol == 'udp':
                protocol = _lo.UDP
            elif self.protocol == 'tcp':
                protocol = _lo.TCP
            else:
                raise ValueError("protocol has to be 'udp' or 'tcp'")

            try:
                self._osc_server_thread = _lo.ServerThread(self.port, protocol)
                self._osc_server_thread.start()
            except _lo.ServerError as e:
                if e.num == 9904:  # liblo: cannot find free port.
                    if self.port < self.port + self.port_range:
                        self._port += 1
                        init()
                else:
                    raise e
            self._osc_server_thread.add_method(None, None, recv, data_object)
            self._osc_server_thread.add_bundle_handlers(start_handler, end_handler, data_object)

        init()
        self._running = True
        atexit.register(self.stop)

    def stop(self):
        if not self._running:
            return
        self._osc_server_thread.stop()
        self._osc_server_thread.free()
        self._running = False
        atexit.unregister(self.stop)

    # *** BUG: sclang convierte nil y [] en cero, "" lo deja como "", True en 1
    # *** BUG: False en 0, los array dentro de los mensajes los convierte en
    # *** BUG: blobs que contienen un mensaje o atado osc. También falta la
    # *** BUG: conversión tuplas como arrays.
    def send_msg(self, target, *args):
        """args es la lista de valores para crear un mensaje"""
        msg = _lo.Message(*args)
        self._osc_server_thread.send(target, msg) # BUG: AttributeError: 'Client' object has no attribute '_osc_server_thread'. Este error no es informativo de que el cliente no está en ejecución (la variable de instsancia no existe)

    def send_bundle(self, target, time, *args): # // sclang warning: this primitive will fail to send if the bundle size is too large # // but it will not throw an error.  this needs to be fixed
        """args son listas de valores para crear varios mensajes"""
        messages = [_lo.Message(*x) for x in args] # BUG: falta la conversión de tipos con tupla
                                                   # BUG: ver si los bundles en sc pueden ser recursivos!!!
        if time is None: # BUG: qué pasaba con valores negativos y nrt?
            time = 0.0
        # *** BUG: No está hecho porque falta definir la interfaz osc:
        # *** BUG: la estampa temporal de bundle tiene que ser el tiempo lógico
        # *** BUG: de current_tt + latency. esto aún no lo hice. según entiendo
        # *** BUG: de esa manera el servidor debería ejecutar los mensajes con
        # *** BUG: precisión, pero no parece ser el caso en sclang. ver si no es
        # *** BUG: un bug allá.
        bundle = _lo.Bundle(_lo.time() + float(time), *messages) # BUG: estoy usando el tiempo de liblo en vez del de SystemClock, que está mal y tengo que revisar, pero luego ver qué tanta diferencia puede haber entre la implementaciones.
        self._osc_server_thread.send(target, bundle)
