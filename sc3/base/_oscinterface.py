
import threading
import atexit
import errno

from ..seq import clock as clk
from . import main as _libsc3
from . import netaddr as nad
from . import _osclib as oli


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
        # _libsc3.main.update_logical_time()  # *** BUG: Clock.sched actualiza abajo, VER TIEMPO LÓGICO.
        addr = nad.NetAddr(addr[0], addr[1])

        if time is None:
            time = _libsc3.main.elapsed_time()  # *** BUG: VER TIEMPO LÓGICO, probar en sclang recibiendo desde una rutina con tempoclock.
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
                if e.errno == errno.EADDRINUSE and i < self.port_range:
                    pass
                elif e.errno == errno.EADDRINUSE and i == self.port_range - 1:
                    err = OSError(
                        f'[Errno {errno.EADDRINUSE}] Port range already in use: '
                        f'{self.port}-{self.port_range - 1}')
                    err.errno = errno.EADDRINUSE
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

    def _build_msg(self, arg_list):  # ['/path', arg1, arg2, ..., argN]
        msg_builder = oli.OscMessageBuilder(arg_list.pop(0))
        for arg in arg_list:
            if arg is None:
                msg_builder.add_arg(0)
            elif isinstance(arg, bool):
                msg_builder.add_arg(int(arg))
            elif isinstance(arg, list):
                if len(arg) == 0:
                    msg_builder.add_arg(0)
                elif isinstance(arg[0], str):
                    msg_builder.add_arg(self._build_msg(arg).dgram)
                elif isinstance(arg[0], (int, float, type(None))):
                    msg_builder.add_arg(self._build_bundle(arg).dgram)
                else:
                    raise oli.OscMessageBuildError(
                        'lists within messages must be a valid '
                        f'OSC message or bundle: {arg}')
            elif arg == '[':
                msg_builder.args.append(
                    (msg_builder.ARG_TYPE_ARRAY_START, None))
            elif arg == ']':
                msg_builder.args.append(
                    (msg_builder.ARG_TYPE_ARRAY_STOP, None))
            else:
                msg_builder.add_arg(arg)  # Infiere correctamente el resto de los tipos.
        return msg_builder.build()

    def send_msg(self, target, *args):
        '''
        args are values to create one message.
        target is a tuple (hostname, port).
        sclang converts True to 1, False to 0, None and empsty lists to 0.
        Non empty lists are converted to blobs containing osc messages or
        bundles. Empty strings are sent unchanged.
        '''
        msg = self._build_msg(list(args))
        # *** BUG: Check size?
        self._server.socket.sendto(msg.dgram, target)

    def _build_bundle(self, arg_list):  # [time, ['/path', arg1, arg2, ..., argN], ['/path', arg1, arg2, ..., argN], ...]
        bndl_builder = oli.OscBundleBuilder(arg_list.pop(0) or oli.IMMEDIATELY)  # Only None is IMMEDIATELY, zero can't reach this stage through addr.send_bundle.
        for arg in arg_list:
            if isinstance(arg[0], str):
                bndl_builder.add_content(self._build_msg(arg))
            elif isinstance(arg[0], (int, float, type(None))):
                bndl_builder.add_content(self._build_bundle(arg))
            else:
                raise oli.OscMessageBuildError(
                    'lists within messages must be a valid '
                    f'OSC message or bundle: {arg}')
        return bndl_builder.build()

    def send_bundle(self, target, time, *args):
        '''
        args are lists of values to creae a message or bundle each.
        target is a tuple (hostname, port).
        If time is None the OSC library must send 1 (immediate) as timetag.
        If time is negative it will be substracted from elapsed time and be
        an already late timetag (no check for sign).
        '''
        bndl = self._build_bundle([time, *args])
        # *** BUG: Check size?
        self._server.socket.sendto(bndl.dgram, target)

    # *** *** BUG: volver estos métodos a NetAddr de alguna manera.
    def msg_size(self, arg_list): # ['/path', arg1, arg2, ..., argN]
        msg = _build_msg(arg_list)  # *** BUG: el problema es no estar construyendo el mensaje dos veces igual.
        return msg.size  # *** BUG: este método está demás, hay que hacer todo en quién llama y guardar el msg.

    # *** BUG: ver _NetAddr_BundleSize
    def bundle_size(self, arg_list): # [time, ['/path', arg1, arg2, ..., argN], ['/path', arg1, arg2, ..., argN], ...]
        bndl = _build_bundle(arg_list)  # *** BUG: el problema es no estar construyendo el atado dos veces igual.
        return bndl.size  # *** BUG: este método está demás, hay que hacer todo en quién llama y guardar el bndl.
