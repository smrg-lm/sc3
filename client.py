"""
Se encarga de:
    * configuración
    * loop liblo para server
    * otras cosas globales
    * midi?

    En sclang existen LanguageConfig, w/r archivos yaml. Las opciones sclang -h.
    Sclang Startup File. La clase Main que hereda de Process. Las clases que
    heredan de AbstractSystemAction: StartUp, ShutDown, ServerBoot, ServerTree,
    CmdPeriod y seguramente otras más.

    VER DOCUMENTACIÓN: 'OSC COMMUNICATION'
"""

import threading as _threading
import atexit as _atexit

import liblo as _lo
import supercollie.utils as ut


DEFAULT_CLIENT_PORT = 57120
DEFAULT_CLIENT_PROTOCOL = _lo.UDP


class Client(object):
    default = None

    def __init__(self, port=DEFAULT_CLIENT_PORT, proto=DEFAULT_CLIENT_PROTOCOL):
        self.port = port
        self._starting_port = port
        self._port_range = 10
        self.proto = proto
        self.client_id = 0 # BUG: ver cómo se manejan los client id
        self.servers = []
        self._is_running = False
        # TODO: Imita a Server, pero ver si no hay otra forma mejor, si pueden haber varias instancias, etc. Lo están usan NetAddr y Server para sus send.
        if Client.default is None:
            Client.default = self

    def start(self):
        if self._is_running: return
        self._init_osc() # BUG: hay que capturar la excepción si falla y cambiar el puerto, si es por eso.
        self._is_running = True
        _atexit.register(self.stop) # BUG: no compruebo que no se agreguen más si se reinicia el cliente.

    def _init_osc(self):
        try:
            self._osc_server_thread = _lo.ServerThread(self.port, self.proto)
            self._osc_server_thread.start()
        except _lo.ServerError as e:
            if e.num == 9904: # b'cannot find free port'
                if self.port < self.port + self._port_range:
                    self.port += 1
                    self._init_osc()
            else:
                raise e

    def stop(self):
        if not self._is_running: return
        self._stop_osc()
        self._is_running = False

    def _stop_osc(self):
        self._osc_server_thread.stop()
        self._osc_server_thread.free()

    def restart(self):
        self.stop()
        self.start()

    def add_server(self, server):
        # TODO: El cliente no puede tener varios servidores iguales
        # creo que habían decoradores para las propiedades
        self.servers.append(server)

    def remove_server(self, server):
        pass # TODO

    def is_running(self):
        return self._is_running

    # *** Métodos de NetAddr ***

    # def port(self): # TODO: sería NetAddr.langPort, haciendo que el atributo port sea privado e inmutable.
    #     return self._port

    # def send_raw(self, target, raw_bytes): # send a raw message without timestamp to the addr (es int8array, creo)
    #     msg = _lo.Message('/', raw_bytes) # sclang no especifica dirección osc.
    #     self._osc_server_thread.send(target, msg) # posible BUG: VER: para liblo el tipo bytes envía un mensaje blob.
    #                                               # En Server:sendSynthDef hace this.sendMsg("/d_recv", buffer); buffer es Int8Array que lee de un archivo.
    #                                               # No se usa en ninguna parte de la librería de clases salvo para Server-sendRaw que tampoco se usa.

    def send_msg(self, target, *args):
        """args es la lista de valores para crear un mensaje"""
        msg = _lo.Message(*args) # BUG: falta la conversión de tipos con tupla
        self._osc_server_thread.send(target, msg)

    def send_bundle(self, target, time, *args): # // sclang warning: this primitive will fail to send if the bundle size is too large # // but it will not throw an error.  this needs to be fixed
        """args son listas de valores para crear varios mensajes"""
        messages = [_lo.Message(*x) for x in args] # BUG: falta la conversión de tipos con tupla
        time = time or 0 # BUG: qué pasaba con valores negativos?
        bundle = _lo.Bundle(float(time), *messages)
        self._osc_server_thread.send(target, bundle)

    def send_status_msg(self):
        self.send_msg('/status')

    # def send_clumped_bundles(self, time, *args): # TODO: importante, lo usa para enviar paquetes muy grandes como stream, ver que hace liblo.

    def sync(self, condition=None, bundles=None, latency=None): # TODO: importante, es la fuente de s.sync
        condition = condition or _threading.Condition()
        if bundles is None:
            id = self.make_sync_responder(condition)
            self.send_bundle(('127.0.0.1', 57120), latency, ['/sync', id]) # TEST BUG: falta default target que creo que sería el servidor por defecto, está puesto sclang
            with condition:
                condition.wait() # BUG: poner timeout y lanzar una excepción?
        else:
            raise NotImplementedError('Implementar sync con bundles') # TODO

    def make_sync_responder(self, condition): # TODO: funciona en realación al método de arriba.
        id = ut.UniqueID.next()
        def responder(*msg):
            print(' ****** added method argument *msg:', msg)
            if msg[1][0] == id: # TODO: msg es ('/synced', [1001], 'i', <liblo.Address object at 0x7f56c88b3d80>, None)
                self._osc_server_thread.del_method('/synced', 'i') # BUG: no dice qué tipo de dato es typespec # BUG: borra la función por path y tipo de dato no por la identidad de la función.
                with condition:
                    condition.notify()
        self._osc_server_thread.add_method('/synced', 'i', responder)
        return id
