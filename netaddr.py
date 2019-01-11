"""
NetAddr.sc

LIBLO: tiene las clases:

* Server
* ServerThread
* make_method (que es un decorador para registrar funciones)

* Address
* Message
* Bundle

* ServerError (excepción)
* AddressError (excepción)

En sclang NetAddr actúa como un poco de todo, dirección, tipo de mensaje,
servidor, etc. Hay:

* NetAddr
* BundleNetAddr

Y métodos esparcidos por la librería de clases que llaman a estas clases.
Además, el cliente es todo el lenguaje y no una librería. Client pordía ser
un wrapper de SreverThread, y NetAddr de Address. Luego los tipos de mensajes
se determinan creando Message o Bundle en Client. Si se quiere establecer
una conexión TCP se podría crear otro cliente, pero no se si sería conveniente
que actúe al mismo nivel de abstracción que Client. Porque es posible que
cliente se componga de otras clases que también manejen los aspectos de
configuración del cliente que en sclang están dispersos en varias clases.

NetAddr podría tener los métodos send pero llamar a los métodos de Client
en vez de implementar otro servidor. También hay que ver cómo interactuan los
métodos send la clase Server (scsynth/supernova) que usan addr.

Tal vez:
Client
    ClientServer (nombre contradictorio, para osc) o ClientThread, ClientOSC, o UDPClient y TCPClient o UDPConnection, etc.
    ClientConfig o ClientOptions
    Platform
    MIDIClient?

VER DOCUMENTACIÓN: 'OSC COMMUNICATION'

ESTA CLASE PROBABLEMENTE QUEDE COMO WRAPPER DE LIBLO SEND CON ADDRESS,
PERO TAL VEZ SEA MEJOR USAR LA INSTANCIA GLOBAL DEL CLIENTE PARA QUE LOS
MENSAJES SALGAN DEL MISMO PUERTO.
"""

import ipaddress as _ipaddress

import liblo as _lo
import supercollie.client as cl


class NetAddr():
    # es initClass L005
    # connections = dict() # BUG: VER: esto también se usa para las conexiones TCP, guarda registro de las que están activas.
    # use_doubles = False # BUG: VER: era método de clase a primitiva. Lo único que hace es no convertir a float los doubles de sclang cuando se envía el dato en el código en c++, variable globa gUseDoubles. Y ajusta el tag osc correspondiente (d/f)
    #                     # BUG: para pasar un 'f' hay que hacer una tupla (typetag, valor), lo mismo pasa con timetag e int, y con char, string, symbol. True, False, nil, infinitum no tiene traducción directa.
    # broadcast_flag = False # BUG: VER: era propiedad de clase a primitiva. Funciona solo para udp gUDPport != 0, gUDPport->udpSocket.set_option(option, ec).

    # es sclang new L009
    def __init__(self, hostname, port):
        if hostname is not None:
            addr = int(_ipaddress.IPv4Address(hostname)) # en sclang es una función de boost, gethostbyname, no dan el mismo número, en sclang parece un overflow
        else:
            addr = 0
        self.addr = addr
        self.port = port
        self._hostname = hostname # es @property y sincroniza self.addr al setearla.
        self.socket = None # BUG: las NetAddr que tienen socket son TCP y se manejan con try_connect_tcp, try_disconnect_tcp, connect, disconnect, connectionsClosed. liblo no provee una interfaz así pero los mensajes puede especificar protocolo.

    @classmethod
    def from_ip(cls, addr, port): # TODO: addr es un entero, usa el método de Integer: asIPString que convierte un número en un string operando sobre bits.
        pass # BUG: primitiva

    @classmethod
    def lang_port(cls): # TODO: client_port? # En Client es el atributo port.
        return g_client.port # TODO: no está definida.

    @classmethod
    def match_lang_ip(cls, ipstring): # TODO: match_client_ip? simplemente dice si la dirección ip es la misma, en la misma máquina es 127.0.0.1
        pass # BUG: primitiva

    @classmethod
    def local_end_point(cls):
        return cls(cls.lang_ip(), cls.lang_port()) # BUG: cosa curiosa, ctrl-i en langIP, que no existe como método, me dirije a matchLangIP, que tiene un argumento.

    @classmethod
    def local_addr(cls):
        return cls('127.0.0.1', cls.lang_port())

    # @classmethod
    # def disconnect_all(cls):
    #     #if cls.connections: # TODO: esta comprobación no es necesaria si no es posible asignar nil a cls.connections que por defecto se inicializa con IdentityDictionary.new
    #     for naddr in cls.connections: # es dict() itera sobre las llaves
    #         naddr.disconnect() # BUG: esto es para TCP, además, debería ir en la clase Client, o algo más global/general que las direcciones de red.

    @property
    def hostname(self):
        return self._hostname

    @hostname.setter
    def hostname(self, value):
        self._hostname = value
        self.addr = int(_ipaddress.IPv4Address(value))

    @hostname.deleter
    def hostname(self):
        del self._hostname

    # def send_raw(self, raw_bytes): # send a raw message without timestamp to the addr.
    #     cl.Client.default.send_raw((self.hostname, self.port), raw_bytes)

    def send_msg(self, *args):
        cl.Client.default.send_msg((self.hostname, self.port), *args)

    # // warning: this primitive will fail to send if the bundle size is too large
	# // but it will not throw an error.  this needs to be fixed
    def send_bundle(self, time, *args):
        cl.Client.default.send_bundle((self.hostname, self.port), *args)

    # def send_status_msg(self): # TODO: esto es particular de la relación del cliente con el servidor
    #     cl.Client.default.send_msg('/status')

    # def send_clumped_bundles(self, time, *args): # TODO: importante, lo usa para enviar paquetes muy grandes como stream, ver que hace liblo.
    # def sync(self, condition, bundles, latency): # TODO: importante, es la fuente de s.sync
    # def make_sync_responder(self, condition): # TODO: funciona en realción al método de arriba.
    # def is_connected(self): # tcp
    # def connect(self, disconnect_handler): # tcp
    # def disconnect(self): # tcp
    # def try_connect_tcp(self, on_complete, on_failure, max_attempts=10):
    # def try_disconnect_tcp(self, on_complete, on_failure):

    # == { arg that; ^this.compareObject(that, #[\port, \addr]) } # OJO
    # hash { ^this.instVarHash(#[\port, \addr]) } # OJO

    # // Asymmetric: "that" may be nil or have nil port (wildcards)
    # def matches(self, that): # TODO: no sé qué es esto.

    # def is_local(self): # { ^this.class.matchLangIP(this.ip) } # TODO: un poco obvio, ver para qué se usa.
    # def ip(self): # TODO: ^addr.asIPString, addr es Integer as_ip_string(int), ver por dónde usa addr como entero.

    # def has_bundle(self): # TODO: No lo entiendo.
    #     return False

    # def print_on(self, stream):
    # def store_on(self, stream):

    # // PRIVATE
    # prConnect # primitiva tcp
    # prDisconnect # primitiva tcp
    # prConnectionClosed # tcp

    def recover(self): # TODO: VER: se usa en el homónimo de BundleNetAddr y en Server-cmdPeriod
        return self


class BundleNetAddr(NetAddr):
    pass
