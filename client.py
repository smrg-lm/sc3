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

    Y MAIN, CLIENT PODDRÍA SER UN MIEMBRO DE MAIN QUE ADEMÁS TIENE PLATFORM!

    VER DOCUMENTACIÓN: 'OSC COMMUNICATION'

    pickle PUEDE SER ÚTIL para guardar la instancia de client y que se
    puedan ejecutar distintas instancias de python con el mismo cliente
    sin tener que tener las sesiones andando en paralelo, e.g. para ejecutar
    scripst por separado desde la terminal.
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
        self._osc_server_thread.send(target, msg) # BUG: AttributeError: 'Client' object has no attribute '_osc_server_thread'. Este error no es informativo de que el cliente no está en ejecución (la variable de instsancia no existe)

    def send_bundle(self, target, time, *args): # // sclang warning: this primitive will fail to send if the bundle size is too large # // but it will not throw an error.  this needs to be fixed
        """args son listas de valores para crear varios mensajes"""
        messages = [_lo.Message(*x) for x in args] # BUG: falta la conversión de tipos con tupla
                                                   # BUG: ver si los bundles en sc pueden ser recursivos!!!
        time = time or 0 # BUG: qué pasaba con valores negativos?
        bundle = _lo.Bundle(float(time), *messages)
        self._osc_server_thread.send(target, bundle)

    def send_status_msg(self):
        self.send_msg('/status')

    def sync(self, condition=None, bundle=None, latency=0): # BUG: dice array of bundles, los métodos bundle_size y send_bundle solo pueden enviar uno. No me cierra/me confunde en sclang porque usa send bundle agregándole latencia.
        condition = condition or _threading.Condition()
        if bundle is None:
            id = self.make_sync_responder(condition)
            self.send_bundle(('127.0.0.1', 57120), latency, ['/sync', id]) # TEST BUG: falta default target que creo que sería el servidor por defecto, está puesto sclang
            with condition:
                condition.wait() # BUG: poner timeout y lanzar una excepción?
        else:
            # BUG: esto no está bien testeado, y acarreo el problema del tamaño exacto de los mensajes.
            sync_size = self.msg_size(['/sync', ut.UniqueID.next()])
            max_size = 65500 - sync_size # BUG: 65500 es un límite práctico que puede estar mal si las cuentas de abajo están mal.
            if self.bundle_size(bundle) > max_size:
                clumped_bundles = self.clump_bundle(bundle, max_size)
                for item in clumped_bundles:
                    id = self.make_sync_responder(condition)
                    item.append(['/sync', id])
                    self.send_bundle(('127.0.0.1', 57120), latency, *item) # TEST BUG: falta default target que creo que sería el servidor por defecto, está puesto sclang
                    latency += 1e-9 # nanosecond, TODO: esto lo hace así no sé por qué.
                    with condition:
                        condition.wait() # BUG: poner timeout y lanzar una excepción?
            else:
                id = self.make_sync_responder(condition)
                bundle = bundle[:]
                bundle.append(['/sync', id])
                self.send_bundle(('127.0.0.1', 57120), latency, *bundle) # TEST BUG: falta default target que creo que sería el servidor por defecto, está puesto sclang
                with condition:
                    condition.wait() # BUG: poner timeout y lanzar una excepción?

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

    # def send_clumped_bundles(self, time, *args): # TODO: importante, lo usa para enviar paquetes muy grandes como stream, liblo tira error y no envía
    def clump_bundle(self, msg_list, new_bundle_size): # msg_list siempre es un solo bundle [['/path', arg1, arg2, ..., argN], ['/path', arg1, arg2, ..., argN], ...]
        ret = [[]]
        clump_count = 0
        acc_size = 0
        aux = 0 # solo inicializo porque se usa dentro del loop
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
