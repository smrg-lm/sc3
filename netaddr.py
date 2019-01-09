"""NetAddr.sc"""

import liblo as _lo


class NetAddr():
    # es initClass L005
    connections = dict()
    broadcast_flag = False # BUG: ver valor por defecto, no entiendo cómo se hace para crear propiedades de clase, ver métodos abajo.

    # es sclang new L009
    def __init__(self, hostname, port):
        if hostname is not None:
            addr = get_host_by_name(hostname) # BUG: es un método de String en sclang.
        else:
            addr = 0
        self.addr = addr
        self.port = port
        self._hostname = hostname # es @property
        self.socket = None

    @classmethod
    def from_ip(cls, addr, port):
        _pass # BUG: primitiva

    @classmethod
    def lang_port(cls): # TODO: client_port?
        _pass # BUG: primitiva

    @classmethod
    def match_lang_ip(cls, ipstring): # TODO: match_client_ip?
        _pass # BUG: primitiva

    @classmethod
    def local_end_point(cls):
        return cls(cls.lang_ip(), cls.lang_port()) # BUG: cosa curiosa, ctrl-i en langIP, que no existe como método, me dirije a matchLangIP, que tiene un argumento.

    @classmethod
    def local_addr(cls):
        return cls('127.0.0.1', cls.lang_port())

    @classmethod
    def use_doubles(cls, flag=False):
        _pass # BUG: primitiva

    # @classmethod
    # def broadcast_flag(cls): # BUG: nombre, es getter, no se pueden crear propiedades de clase?
    #     return cls._broadcast_flag # BUG: ver primitiva
    # @classmethod
    # def broadcast_flag_(cls, flag=True): # BUG: nombre, es setter, no se pueden crear propiedades de clase?
    #     cls._broadcast_flag = flag # BUG: ver primitiva

    @classmethod
    def disconnect_all(cls):
        #if cls.connections: # TODO: esta comprobación no es necesaria si no es posible asignar nil a cls.connections que por defecto se inicializa con IdentityDictionary.new
        for naddr in cls.connections: # es dict() itera sobre las llaves
            naddr.disconnect()

    @property
    def hostname(self):
        return self._hostname

    @hostname.setter
    def hostname(self, value):
        self._hostname = value
        self.addr = get_host_by_name(value) # BUG: es un método de String en sclang.

    @hostname.deleter
    def hostname(self):
        del self._hostname

    def send_raw(self, rawlist):
        _pass # BUG: primitiva

    def send_msg(self, *args):
        _pass # BUG: primitiva

    # // warning: this primitive will fail to send if the bundle size is too large
	# // but it will not throw an error.  this needs to be fixed
    def send_bundle(self, time, *args):
        _pass # BUG: primitiva

    def send_status_msg(self):
        self.send_msg('/status')

    # def send_clumped_bundles(self, time, *args):
    # def sync(self, condition, bundles, latency):
    # def make_sync_responder(self, condition):
    # def is_connected(self):
    # def connect(self, disconnect_handler):
    # def disconnect(self):
    # def try_connect_tcp(self, on_complete, on_failure, max_attempts=10):
    # def try_disconnect_tcp(self, on_complete, on_failure):

    # == { arg that; ^this.compareObject(that, #[\port, \addr]) } # OJO
    # hash { ^this.instVarHash(#[\port, \addr]) } # OJO

    # // Asymmetric: "that" may be nil or have nil port (wildcards)
    # def matches(self, that):

    # def is_local(self): # { ^this.class.matchLangIP(this.ip) }
    # def ip(self): # ^addr.asIPString, addr es Integer as_ip_string(int)

    def has_bundle(self):
        return False

    # def print_on(self, stream):
    # def store_on(self, stream):

    # // PRIVATE
    # prConnect # primitiva
    # prDisconnect # primitiva
    # prConnectionClosed

    def recover(self): # TODO: VER: se usa en el homónimo de BundleNetAddr y en Server-cmdPeriod
        return self


class BundleNetAddr(NetAddr):
    pass
