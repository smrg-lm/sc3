"""NetAddr.sc"""

import ipaddress
import socket

from ..seq import clock as clk
from ..seq import stream as stm
from . import main as _libsc3
from . import utils as utl
from . import responsedefs as rdf
from . import _oscinterface as osci


__all__ = ['NetAddr']  #, 'BundleNetAddr']


class NetAddr():
    # use_doubles = False # BUG: VER: era método de clase a primitiva. Lo único que hace es no convertir a float los doubles de sclang cuando se envía el dato en el código en c++, variable globa gUseDoubles. Y ajusta el tag osc correspondiente (d/f)
    #                     # BUG: para pasar un 'f' hay que hacer una tupla (typetag, valor), lo mismo pasa con timetag e int, y con char, string, symbol. True, False, nil, infinitum no tiene traducción directa.
    # broadcast_flag = False # BUG: VER: era propiedad de clase a primitiva. Funciona solo para udp gUDPport != 0, gUDPport->udpSocket.set_option(option, ec).

    #__slots__ = ()

    def __init__(self, hostname, port):
        if hostname is None:
            self._addr = 0  # Server:in_process
        else:
            self._addr = int(ipaddress.IPv4Address(hostname))  # Exception if invalid.
        self._hostname = hostname
        self._port = port
        self._target = (hostname, port)
        self._proto = 'udp'
        self._osc_interface = _libsc3.main._osc_interface

    @property
    def hostname(self):
        return self._hostname

    @property
    def addr(self):
        return self._addr

    @property
    def port(self):
        return self._port

    @property
    def proto(self):
        return self._proto

    @property
    def is_local(self):
        return self.match_lang_ip(self._hostname)  # *** BUG? no sé por qué sclang calcula hostname con addr.asIPString que lo que hace es volver a hostsname...

    @property
    def local_end_point(self):  # bind_addr
        if self._osc_interface.socket:
            return type(self)(*self._osc_interface.socket.getsockname())

    # @classmethod
    # def local_addr(cls):  # local_end_point?
    #     return cls('127.0.0.1', cls.lang_port())

    @staticmethod
    def lang_port():
        return _libsc3.main._osc_interface.port

    @staticmethod
    def match_lang_ip(ipstring):
        #if ipaddress.IPv4Address(self._addr).is_loopback: # sclang compara solo con 127.0.0.1 como loopback
        if ipstring == '127.0.0.1':
            return True
        addr_info = socket.getaddrinfo(socket.gethostname(), None)
        for item in addr_info:
            if item[4][0] == ipstring:
                return True
        return False


    ### TCP Connections ###

    def connect(self, on_complete=None, on_failure=None,
                local_port=None, port_range=10, timeout=3):
        # Async.
        if self.is_connected:
            self.disconnect()
        if self._proto == 'udp':
            self._proto = 'tcp'
        self._osc_interface = osci.OscTcpInteface(
            local_port or self.lang_port() + 1, port_range)
        self._osc_interface.bind()
        self._osc_interface.try_connect(
            self._target, timeout, on_complete, on_failure)

    def disconnect(self):
        # Sync.
        self._osc_interface.disconnect()

    @property
    def is_connected(self):
        return self._osc_interface.is_connected


    # @classmethod
    # def client_ip(cls):
    #     ...  # BUG: este método no está definido en sclang, aunque debería?, supongo que tiene que retornar la dirección de ip, o en la red local, el problema es que no hay una sola y simple solución multiplataforma.
               # BUG: ver las repuestas de abajo en: https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib


    # def send_raw(self, raw_bytes): # send a raw message without timestamp to the addr.
    #     _libsc3.main._osc_interface.send_raw((self.hostname, self.port), raw_bytes)

    def send_msg(self, *args):
        self._osc_interface.send_msg(self._target, *args)

    def send_bundle(self, time, *args):
        if time is not None:
            time += _libsc3.main.current_tt.seconds
            time = clk.SystemClock.elapsed_time_to_osc(time)
        self._osc_interface.send_bundle(self._target, time, *args)

    # def send_clumped_bundles(self, time, *args):

    def send_status_msg(self):
        self._osc_interface.send_msg(self._target, '/status')

    def sync(self, condition=None, bundle=None, latency=None):
        condition = condition or stm.Condition()
        if bundle is None:
            id = self._make_sync_responder(condition)
            self.send_bundle(latency, ['/sync', id])
            yield from condition.wait()
        else:
            # BUG: esto no está bien testeado, y acarreo el problema del tamaño exacto de los mensajes.
            sync_size = _libsc3.main._osc_interface.msg_size(['/sync', utl.UniqueID.next()])  # *** msg_size dije que vuelva a NetAddr.
            max_size = 65500 - sync_size # *** BUG: is max dgram size? Wiki: The field size sets a theoretical limit of 65,535 bytes (8 byte header + 65,527 bytes of data) for a UDP datagram. However the actual limit for the data length, which is imposed by the underlying IPv4 protocol, is 65,507 bytes (65,535 − 8 byte UDP header − 20 byte IP header).
            if _libsc3.main._osc_interface.bundle_size(bundle) > max_size:
                clumped_bundles = self.clump_bundle(bundle, max_size)
                for item in clumped_bundles:
                    id = self._make_sync_responder(condition)
                    item.append(['/sync', id])
                    self.send_bundle(latency, *item)
                    if latency is not None:
                        latency += 1e-9 # nanoseconds
                    yield from condition.wait()
            else:
                id = self._make_sync_responder(condition)
                bundle = bundle[:]
                bundle.append(['/sync', id])
                self.send_bundle(latency, *bundle)
                yield from condition.wait()

    def _make_sync_responder(self, condition):
        id = utl.UniqueID.next()

        def resp_func(msg, *_):
            if msg[1] == id:
                resp.free()
                condition.test = True
                condition.signal()

        resp = rdf.OSCFunc(resp_func, '/synced', self)
        return id

    # NOTE: Importante, lo usa para enviar paquetes muy grandes como stream,
    # liblo tira error y no envía.
    # *** BUG: revisar método en contexto, timetag y ver si se pueden procesar incrementalmente los sub msg/bndl.
    def clump_bundle(self, msg_list, new_bundle_size): # msg_list siempre es un solo bundle [['/path', arg1, arg2, ..., argN], ['/path', arg1, arg2, ..., argN], ...]
        ret = [[]]
        clump_count = 0
        acc_size = 0
        aux = 0
        for item in msg_list:
            aux = _libsc3.main._osc_interface.msg_size(item)
            if acc_size + aux > new_bundle_size: # BUG: 65500 es aproximado al límite del datagrama menos la envoltura ipv4, ver sync.
                acc_size = aux
                clump_count += 1
                ret.append([])
                ret[clump_count].append(item)
            else:
                acc_size += aux
                ret[clump_count].append(item)
        if len(ret[0]) == 0: ret.pop(0)
        return ret

    # // Asymmetric: "that" may be nil or have nil port (wildcards)
    # def matches(self, that): # TODO: no sé qué es esto.

    # def ip(self): # TODO: ^addr.asIPString, addr es Integer as_ip_string(int), ver por dónde usa addr como entero.

    def has_bundle(self): # TODO: distingue de BundleNetAddr
        return False

    def recover(self): # TODO: VER: se usa en el homónimo de BundleNetAddr y en Server-cmdPeriod
        return self

    def __eq__(self, other):
        if type(self) == type(other):
            return self._target == other._target
        else:
            return False

    def __hash__(self):
        return hash((type(self), hash(self._target)))

    def __repr__(self):
        return f"{type(self).__name__}('{self.hostname}', {self.port})"


# BUG: hay que implementar para server
# class BundleNetAddr(NetAddr):
#     ...
