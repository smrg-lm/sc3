"""
Se encarga de:
    * configuración
    * loop liblo para server
    * otras cosas globales
    * midi?

    Tal vez esta clase sería un mix con el status whatcher...
    Tal vez esta clase no sea necesaria y solo se necesite Server...
    Salvo por el manejo si se tienen varios servidores...
    Tal vez esta clase sería privada e interna de la clase Server...
    Porque la funcionalidad y las clases de liblo ya cubren las necesidades osc.
"""

import liblo as _liblo

class Client(object):
    def __init__(self, port=57120, proto=_liblo.UDP):
        self.port = port
        self.proto = proto
        self.client_id = 0 # ver bien qué es esto que está en Server.sc
        self.servers = []
        self.__is_running = False

    def start(self):
        if self.__is_running:
            return

        # osc stuff
        self.__server_thread = _liblo.ServerThread(self.port, self.proto)
        self.__server_thread.start() # conviene hacerle manglin solo si no se va a usar desde ningún otro lado sino la instancia tiene que se global o pueden haber varias instancias...

        self.__is_running = True

    def stop(self):
        if not self.__is_running:
            return

        # osc stuff
        self.__server_thread.stop()
        self.__server_thread.free()

        self.__is_running = False

    def restart(self):
        self.stop()
        self.start()

    def is_running(self):
        return self.__is_running

    def add_server(self, server):
        # TODO: El cliente no puede tener varios servidores iguales
        # creo que habían decoradores para las propiedades
        self.servers.append(server)

    def remove_server(self, server):
        pass
