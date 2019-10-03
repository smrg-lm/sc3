
import threading
import atexit

from . import main as _libsc3
from . import utils as utl
from . import netaddr as nad
from . import responsedefs as rdf
from . import _osclib as oli
from ..seq import clock as clk
from ..seq import stream as stm


class OscInteface():
    def __init__(self, client_port=57120, protocol='udp', port_range=10):
        '''proto es 'udp' o 'tcp', algunos servidores pueden usar abmos.'''
        self._port = client_port
        self._protocol = protocol
        self._port_range = port_range
        self._recv_functions = set()
        self._server = None
        self._client = None  # *** BUG: TODO: para send.
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

    def recv(self, addr, time, *msg):
        '''
        This method is the handler of all incoming OSC messages or bundles
        to be registered once for each OSC server interface in subclasses.

        Args:
            addr: A tuple (sender_ip:str, sender_port:int).
            time: OSC timetag as 64bits unsigned integer.
            *msg: OSC message as address followed by values.
        '''
        _libsc3.main.update_logical_time()
        addr = nad.NetAddr(addr[0], addr[1])

        if time is None:
            time = _libsc3.main.elapsed_time()
        else:
            time = clk.SystemClock.osc_to_elapsed_time(time)

        def sched_func():
            for func in self.recv_functions:  # *** BUG: no optimal, responsedefs is sitll incomplete.
                func(list(msg), time, addr, self.port)

        clk.AppClock.sched(0, sched_func)  # *** BUG: SystemClock?

    def add_recv_func(self, func):
        self._recv_functions.add(func)

    def remove_recv_func(self, func):
        self._recv_functions.remove(func)

    def running(self):
        return self._running

    def start(self):
        if self._running:
            return
        # if self.protocol == 'udp':  # *** BUG: ver TCP.
        for i in range(self.port_range):
            try:
                self._port += i
                self._server = oli.ThreadingOSCUDPServer(
                    ('127.0.0.1', self._port), oli.UDPHandler)
                break
            except OSError as e:
                if e.errno == 98 and i < self.port_range:  # Address already in use.
                    pass
                elif e.errno == 98 and i == self.port_range - 1:
                    err = OSError(
                        '[Errno 98] Port range already in use: '
                        f'{self.port}-{self.port_range - 1}')
                    err.errno = 98
                    raise err
                else:
                    raise e
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            name=f'{type(self).__name__} port {self._port}')
        self._server_thread.daemon = True
        self._server_thread.start()
        self._running = True
        atexit.register(self.stop)

    def stop(self):
        if not self._running:
            return
        self._server.shutdown()
        self._running = False
        atexit.unregister(self.stop)

    def build_msg(self, arg_list):  # ['/path', arg1, arg2, ..., argN]
        ...

    def send_msg(self, target, *args):
        '''
        args are values to create one message.
        target is a tuple (hostname, port).
        sclang converts True to 1, False to 0, None and empsty lists to 0.
        Non empty lists are converted to blobs containing osc messages or
        bundles. Empty strings are sent unchanged.
        '''
        pass  # *** BUG: se necesita hacer la lógica de conversión de acá arriba.

    def build_bundle(self, arg_list):  # [time, ['/path', arg1, arg2, ..., argN], ['/path', arg1, arg2, ..., argN], ...]
        ...

    def send_bundle(self, target, time, *args):
        '''
        args are lists of values to creae a message or bundle each.
        target is a tuple (hostname, port).
        If time is None the OSC library must send 1 (immediate) as timetag.
        If time is negative it will be substracted from elapsed time and be
        an already late timetag (no check for sign).
        '''
        # *** BUG: la estampa temporal se setean en NetAddr como tiempo lógico de current_tt + latency.
        # *** BUG: acá si time es None quiere decir IMMEDIATELY (1).
        ...

    def sync(self, target, condition=None, bundle=None, latency=0): # BUG: dice array of bundles, los métodos bundle_size y send_bundle solo pueden enviar uno. No me cierra/me confunde en sclang porque usa send bundle agregándole latencia.
        condition = condition or stm.Condition()
        if bundle is None:
            id = self._make_sync_responder(target, condition)
            self.send_bundle(target, latency, ['/sync', id])
            yield from condition.wait()
        else:
            # BUG: esto no está bien testeado, y acarreo el problema del tamaño exacto de los mensajes.
            sync_size = self.msg_size(['/sync', utl.UniqueID.next()])
            max_size = 65500 - sync_size # *** BUG: is max dgram size? TODO: CHECK.
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

    def msg_size(self, arg_list): # ['/path', arg1, arg2, ..., argN]
        msg = build_msg(arg_list)  # *** BUG: el problema es no estar construyendo el mensaje dos veces igual.
        return msg.size  # *** BUG: este método está demás, hay que hacer todo en quién llama y guardar el msg.

    def bundle_size(self, arg_list): # [time, ['/path', arg1, arg2, ..., argN], ['/path', arg1, arg2, ..., argN], ...]
        bndl = build_bundle(arg_list)  # *** BUG: el problema es no estar construyendo el atado dos veces igual.
        return bndl.size  # *** BUG: este método está demás, hay que hacer todo en quién llama y guardar el bndl.
