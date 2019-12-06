"""NetAddr.sc"""

import ipaddress as _ipaddress
import socket as _socket

from ..seq import clock as clk
from ..seq import stream as stm
from . import main as _libsc3
from . import utils as utl
from . import responsedefs as rdf


class NetAddr():
    # es initClass L005
    # connections = dict() # BUG: VER: esto también se usa para las conexiones TCP, guarda registro de las que están activas.
    # use_doubles = False # BUG: VER: era método de clase a primitiva. Lo único que hace es no convertir a float los doubles de sclang cuando se envía el dato en el código en c++, variable globa gUseDoubles. Y ajusta el tag osc correspondiente (d/f)
    #                     # BUG: para pasar un 'f' hay que hacer una tupla (typetag, valor), lo mismo pasa con timetag e int, y con char, string, symbol. True, False, nil, infinitum no tiene traducción directa.
    # broadcast_flag = False # BUG: VER: era propiedad de clase a primitiva. Funciona solo para udp gUDPport != 0, gUDPport->udpSocket.set_option(option, ec).

    # es sclang new L009
    def __init__(self, hostname, port):
        if hostname is None:
            self._addr = 0 # Server:in_process
        else:
            self._addr = int(_ipaddress.IPv4Address(hostname)) # tira error si la dirección es inválida
        self._hostname = hostname # es @property y sincroniza self._addr y self._target al setearla.
        self._port = port # es @property y sincroniza self._target al setearla
        self._target = (hostname, port)

    @property
    def hostname(self):
        return self._hostname

    @hostname.setter
    def hostname(self, value):
        self._addr = int(_ipaddress.IPv4Address(value))
        self._hostname = value
        self._target = (self._hostnane, self._port)

    @property
    def addr(self):
        return self._addr

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self._port = value
        self._target = (self._hostnane, self._port)

    @classmethod
    def local_addr(cls): # TODO: este método también es próximo a inútil
        return cls('127.0.0.1', cls.lang_port())

    @classmethod
    def lang_port(cls):
        return _libsc3.main._osc_interface.port

    @staticmethod
    def match_lang_ip(ipstring):
        #if _ipaddress.IPv4Address(self._addr).is_loopback: # sclang compara solo con 127.0.0.1 como loopback
        if ipstring == '127.0.0.1':
            return True
        addr_info = _socket.getaddrinfo(
            _socket.gethostname(), None,
            _socket.AddressFamily.AF_INET
        ) # TODO/BUG: prMatchLangIP en OSCData.cpp incluye AF_INET6 aunque SuperCollider no soporta IPv6
        for item in addr_info:
            if item[4][0] == ipstring:
                return True
        return False

    def is_local(self):
        return self.match_lang_ip(self._hostname) # BUG? no sé por qué sclang calcula hostname con addr.asIPString que lo que hace es volver a hostsname...

    # @classmethod
    # def from_ip(cls, i32addr, port): # TODO: no le veo uso a este método en la lógica reducida de usar NetAddr como interfaz de Client.
    #     hostname = str(_ipaddress.IPv4Address(addr))
    #     return cls(hostname, port)

    # @classmethod
    # def client_ip(cls):
    #     ...  # BUG: este método no está definido en sclang, aunque debería?, supongo que tiene que retornar la dirección de ip, o en la red local, el problema es que no hay una sola y simple solución multiplataforma.
               # BUG: ver las repuestas de abajo en: https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib

    # @classmethod
    # def local_end_point(cls):
    #     return cls(cls.client_ip(), cls.lang_port()) # depende de client_ip

    # @classmethod
    # def disconnect_all(cls):
    #     #if cls.connections: # TODO: esta comprobación no es necesaria si no es posible asignar nil a cls.connections que por defecto se inicializa con IdentityDictionary.new
    #     for naddr in cls.connections: # es dict() itera sobre las llaves
    #         naddr.disconnect() # BUG: esto es para TCP, además, debería ir en la clase Client, o algo más global/general que las direcciones de red.

    # def send_raw(self, raw_bytes): # send a raw message without timestamp to the addr.
    #     _libsc3.main._osc_interface.send_raw((self.hostname, self.port), raw_bytes)

    def send_msg(self, *args):
        _libsc3.main._osc_interface.send_msg(self._target, *args)

    def send_bundle(self, time, *args):
        if time is not None:
            time += _libsc3.main.current_tt.seconds
            time = clk.SystemClock.elapsed_time_to_osc(time)
        _libsc3.main._osc_interface.send_bundle(self._target, time, *args)

    def send_status_msg(self):
        _libsc3.main._osc_interface.send_msg(self._target, '/status')

    # def send_clumped_bundles(self, time, *args):

    def sync(self, condition=None, bundle=None, latency=None):
        condition = condition or stm.Condition()
        if bundle is None:
            id = self._make_sync_responder(condition)
            self.send_bundle(latency, ['/sync', id])
            yield from condition.wait()
        else:
            # BUG: esto no está bien testeado, y acarreo el problema del tamaño exacto de los mensajes.
            sync_size = _libsc3.main._osc_interface.msg_size(['/sync', utl.UniqueID.next()])
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

    # def is_connected(self): # tcp
    # def connect(self, disconnect_handler): # tcp
    # def disconnect(self): # tcp
    # def try_connect_tcp(self, on_complete, on_failure, max_attempts=10):
    # def try_disconnect_tcp(self, on_complete, on_failure):

    # == { arg that; ^this.compareObject(that, #[\port, \addr]) } # OJO
    # hash { ^this.instVarHash(#[\port, \addr]) } # OJO

    # // Asymmetric: "that" may be nil or have nil port (wildcards)
    # def matches(self, that): # TODO: no sé qué es esto.

    # def ip(self): # TODO: ^addr.asIPString, addr es Integer as_ip_string(int), ver por dónde usa addr como entero.

    def has_bundle(self): # TODO: distingue de BundleNetAddr
        return False

    # def print_on(self, stream):
    # def store_on(self, stream):

    # // PRIVATE
    # prConnect # primitiva tcp
    # prDisconnect # primitiva tcp
    # prConnectionClosed # tcp

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
