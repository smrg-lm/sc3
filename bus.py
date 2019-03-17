"""Bus.sc"""

from supercollie.graphparam import UGenParameter, NodeParameter
from . import server as srv
import supercollie.utils as utl
import supercollie.responsedefs as rdf


class Bus(UGenParameter, NodeParameter):
    def __init__(self, rate='audio', index=0, num_channels=2, server=None): # NOTE: es *new
        self.rate = rate # todos tienen solo getter salvo _map_symbol que es privado.
        self.index = index
        self.num_channels = num_channels
        self.server = server or srv.Server.default
        # self._map_symbol = None

    @classmethod
    def new_from(cls, bus, offset, num_channels=1):
        if offset > bus.num_channels\
        or num_channels + offset > bus.num_channels:
            msg = 'Bus:new_from tried to reach outside the channel range of {}'
            raise Exception(msg.format(bus))
        return cls(bus.rate, bus.index + offset, num_channels)

    @classmethod
    def control(cls, server, num_channels=1):
        server = server or srv.Server.default
        alloc = server.control_bus_allocator.alloc(num_channels)
        if alloc is None:
            msg = 'Bus:control failed to get a control bus allocated, '
            msg += 'num_channels = {}, server = {}'
            raise Exception(msg.format(num_channels, server.name)) # BUG: sclang retorna nil
        return cls('control', alloc, num_channels, server)

    @classmethod
    def audio(cls, server, num_channels=1):
        server = server or srv.Server.default
        alloc = server.audio_bus_allocator.alloc(num_channels)
        if alloc is None:
            msg = 'Bus:audio failed to get a audio bus allocated, '
            msg += 'num_channels = {}, server = {}'
            raise Exception(msg.format(num_channels, server.name)) # BUG: sclang retorna nil
        return cls('audio', alloc, num_channels, server)

    @classmethod
    def alloc(cls, rate, server, num_channels=1):
        if rate == 'control':
            return cls.control(server, num_channels)
        elif rate == 'audio':
            return cls.audio(server, num_channels)
        raise Exception("Bus:alloc invalid rate '{}'".format(rate)) # BUG: sclang retorna nil

    def settable(self): # NOTE: está pitonizado, era isSettable
        return self.rate != 'audio'

    def set(self, *values):  # // shouldn't be larger than self.num_channels
        if self.index is None:
            msg = "cannot call 'set' on a Bus that has been freed"
            raise Exception(msg)
        elif self.settable():
            values = [[self.index + i, val] for i, val in enumerate(values)]
            self.server.send_bundle(0, ['/c_set'].extend(utl.flat(values)))
        print('cannot set an audio rate bus') # BUG: log, warnings

    def set_msg(self, *values):
        if self.index is None:
            msg = "cannot construct a '/c_set' on a Bus that has been freed"
            raise Exception(msg)
        elif self.settable():
            values = [[self.index + i, val] for i, val in enumerate(values)]
            return ['/c_set'].extend(utl.flat(values))
        raise Exception('cannot set an audio rate bus')

    def setn(self, values):
        if self.index is None:
            msg = "cannot call 'setn' on a Bus that has been freed"
            raise Exception(msg)
        elif self.settable():
            self.server.send_bundle(0, ['/c_setn', len(values)].extend(values))
        print('cannot set an audio rate bus') # BUG: log, warnings

    def setn_msg(self, values):
        if self.index is None:
            msg = "cannot construct a '/c_setn' for a Bus that has been freed"
            raise Exception(msg)
        elif self.settable():
            return ['/c_setn', len(values)].extend(values)
        raise Exception('cannot set an audio rate bus')

    def set_at(self, offset, *values):
        if self.index is None:
            msg = 'cannot call set_at on a Bus that has been freed'
            raise Exception(msg)
        elif self.settable():
            values = [[self.index + offset + i, val]\
                      for i, val in enumerate(values)]
            self.server.send_bundle(0, ['/c_set'].extend(utl.flat(values)))
        print('cannot set an audio rate bus') # BUG: log, warnings

    def setn_at(self, offset, values):
        if self.index is None:
            msg = 'cannot call setn_at on a Bus that has been freed'
            raise Exception(msg)
        # // could throw an error if values.size > numChannels
        elif self.settable():
            self.server.send_bundle(0,
                ['/c_setn', self.index + offset, len(values)].extend(values))
        print('cannot set an audio rate bus') # BUG: log, warnings

    def set_pairs(self, *pairs):
        if self.index in None:
            msg = 'cannot call set_pairs on a Bus that has been freed'
            raise Exception(msg)
        elif self.settable():
            pairs = [[self.index + pair[0], pair[1]]\
                     for pair in utl.gen_cclumps(pairs, 2)]
            self.server.send_bundle(0, ['/c_set'].extend(utl.flat(paris)))

    def get(self, action=None):
        if self.index in None:
            msg = 'cannot call get on a Bus that has been freed'
            raise Exception(msg)
        if self.num_channels == 1:
            if action is None:
                def func(val):
                    msg = 'Bus {} index: {} value: {}'
                    print(msg.format(self.rate, self.index, val))
                action = func

            def osc_func(msg, *args):
                # // The response is of the form [/c_set, index, value].
                # // We want "value," which is at index 2.
                action(msg[2])

            rdf.OSCFunc(
                osc_func, '/c_set', self.server.addr, # BUG: es c_set? está el comentario de arriba pero se ve raro, tal vez por eso lo comenta.
                arg_template=[self.index]
            ).one_shot()
            self.server.list_send_msg(['/c_get', self.index]) # BUG: este método no lo implementé, ver de cambiarlo, ver cuánto se usa
        else:
            self.getn(self.num_channels, action)

    def get_msg(self):
        if self.index in None:
            msg = "cannot construct a '/c_get' for a Bus that has been freed"
            raise Exception(msg)
        return ['/c_get', self.index]

    def getn(self, count=None, action=None):
        if self.index in None:
            msg = 'cannot call getn on a Bus that has been freed'
            raise Exception(msg)
        if action is None:
            def func(vals):
                msg = 'Bus {} index: {} values: {}'
                print(msg.format(self.rate, self.index, vals))
            action = func

        def osc_func(msg, *args):
            # // The response is of the form [/c_set, index, count, ...values].
            # // We want the values, which are at indexes 3 and above.
            action(msg[3:])

        rdf.OSCFunc(
            osc_func, '/c_setn', self.server.addr,
            arg_template=[self.index]
        ).one_shot() # NOTE: ver si one_shot se puede usar en las funcinoes de server que se liberan a sí mismas
        self.server.list_send_msg( # BUG: este método no está implementado, ver de cambiarlo? ver cuánto se usa
            ['/c_getn', self.index, count or self.num_channels]) # BUG: revisar los 'or'

    def getn_msg(self, count=None):
        if self.index in None:
            msg = "cannot construct a '/c_getn' for a Bus that has been freed"
            raise Exception(msg)
        return ['/c_getn', self.index, count or self.num_channels] # BUG: or no es lo mismo con número, e.g. si count es 0 pasa num_channels, aunque creo que no tiene sentido que sea cero.
        # BUG: revisar todos los 'or' BUG, BUG

    def get_synchronous(self):
        pass

    def getn_synchronous(self, count):
        pass

    def set_synchronous(self, *values):
        pass

    def setn_synchronous(self, values):
        pass

    def fill(self, value, num_chans):
        pass

    def fill_msg(self, value):
        pass

    def free(self, clear=False):
        pass

    # // allow reallocation

    def alloc(self):
        pass

    def realloc(self):
        pass

    # // alternate syntaxes
    # TODO: hay métodos que son importantes (e.g. asMap), VER.

    # UGen graph parameter interface #

    def as_ugen_input(self, *_):
        return self.index

    def as_control_input(self):
        return self.index

    def as_ugen_rate(self):
        return self.rate

    # Node parameter interface #
    # NOTE: Usa todos los valores por defecto de Object
