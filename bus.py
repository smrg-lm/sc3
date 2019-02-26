"""Bus.sc"""

import supercollie.server as srv
import supercollie.utils as utl


class Bus():
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
            msg = "cannot call 'set' on a Bus that has been freed"
            raise Exception(msg)
        elif self.settable():
            values = [[self.index + i, val] for i, val in enumerate(values)]
            return ['/c_set'].extend(utl.flat(values))
        raise Exception('cannot set an audio rate bus'))

    def setn(self, values):
        if self.index is None:
            msg = "cannot call 'set' on a Bus that has been freed"
            raise Exception(msg)
        elif self.settable():
            self.server.send_bundle(0, ['/c_setn', len(values)].extend(values))
        print('cannot set an audio rate bus') # BUG: log, warnings

    def setn_msg(self, values):
        if self.index is None:
            msg = "cannot call 'set' on a Bus that has been freed"
            raise Exception(msg)
        elif self.settable():
            return ['/c_setn', len(values)].extend(values)
        raise Exception('cannot set an audio rate bus')

    # TODO: sigue...




#
