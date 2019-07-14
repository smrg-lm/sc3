"""Bus.sc"""

import logging

from . import graphparam as gpp
from . import server as srv
from . import utils as utl
from . import responsedefs as rdf


_logger = logging.getLogger(__name__)


class Bus(gpp.UGenParameter, gpp.NodeParameter):
    def __init__(self, rate='audio', index=0, num_channels=2, server=None): # NOTE: es *new
        self._rate = rate # todos tienen solo getter salvo _map_symbol que es privado.
        self._index = index
        self._num_channels = num_channels
        self._server = server or srv.Server.default
        # self._map_symbol = None

    @property
    def rate(self):
        return self._rate

    @property
    def index(self):
        return self._index

    @property
    def num_channels(self):
        return self._num_channels

    @property
    def server(self):
        return self._server

    @classmethod
    def new_from(cls, bus, offset, num_channels=1):
        if offset > bus.num_channels\
        or num_channels + offset > bus.num_channels:
            raise Exception(
                'Bus:new_from tried to reach outside '
                f'the channel range of {bus}')
        return cls(bus.rate, bus.index + offset, num_channels)

    @classmethod
    def control(cls, server=None, num_channels=1):
        server = server or srv.Server.default
        alloc = server.control_bus_allocator.alloc(num_channels)
        if alloc is None:
            raise Exception(
                'Bus:control failed to get a control bus allocated, '
                f'num_channels = {num_channels}, server = {server.name}')
        return cls('control', alloc, num_channels, server)

    @classmethod
    def audio(cls, server=None, num_channels=1):
        server = server or srv.Server.default
        alloc = server.audio_bus_allocator.alloc(num_channels)
        if alloc is None:
            raise Exception(
                'Bus:audio failed to get a audio bus allocated, '
                f'num_channels = {num_channels}, server = {server.name}')
        return cls('audio', alloc, num_channels, server)

    @classmethod
    def alloc(cls, rate, server=None, num_channels=1):
        if rate == 'control':
            return cls.control(server, num_channels)
        elif rate == 'audio':
            return cls.audio(server, num_channels)
        raise Exception(f"Bus:alloc invalid rate '{rate}'")

    def settable(self): # NOTE: está pitonizado, era isSettable
        return self._rate != 'audio'

    def set(self, *values):  # // shouldn't be larger than self._num_channels
        if self._index is None:
            raise Exception("cannot call 'set' on a Bus that has been freed")
        elif self.settable():
            values = [[self._index + i, val] for i, val in enumerate(values)]
            self._server.send_bundle(0, ['/c_set'].extend(utl.flat(values)))
        else:
            _logger.warning('cannot set an audio rate bus')

    def set_msg(self, *values):
        if self._index is None:
            raise Exception(
                "cannot construct a '/c_set' on a Bus that has been freed")
        elif self.settable():
            values = [[self._index + i, val] for i, val in enumerate(values)]
            return ['/c_set'].extend(utl.flat(values))
        raise Exception('cannot set an audio rate bus')

    def setn(self, values):
        if self._index is None:
            raise Exception("cannot call 'setn' on a Bus that has been freed")
        elif self.settable():
            self._server.send_bundle(0, ['/c_setn', len(values)].extend(values))
        else:
            _logger.warning('cannot set an audio rate bus')

    def setn_msg(self, values):
        if self._index is None:
            raise Exception(
                "cannot construct a '/c_setn' for a Bus that has been freed")
        elif self.settable():
            return ['/c_setn', len(values)].extend(values)
        raise Exception('cannot set an audio rate bus')

    def set_at(self, offset, *values):
        if self._index is None:
            raise Exception('cannot call set_at on a Bus that has been freed')
        elif self.settable():
            values = [[self._index + offset + i, val]\
                      for i, val in enumerate(values)]
            self._server.send_bundle(0, ['/c_set'].extend(utl.flat(values)))
        else:
            _logger.warning('cannot set an audio rate bus')

    def setn_at(self, offset, values):
        if self._index is None:
            raise Exception('cannot call setn_at on a Bus that has been freed')
        # // could throw an error if values.size > numChannels
        elif self.settable():
            self._server.send_bundle(0,
                ['/c_setn', self._index + offset, len(values)].extend(values))
        else:
            _logger.warning('cannot set an audio rate bus')

    def set_pairs(self, *pairs):
        if self._index is None:
            raise Exception(
                'cannot call set_pairs on a Bus that has been freed')
        elif self.settable():
            pairs = [[self._index + pair[0], pair[1]]\
                     for pair in utl.gen_cclumps(pairs, 2)]
            self._server.send_bundle(0, ['/c_set'].extend(utl.flat(paris)))
        else:
            _logger.warning('cannot set an audio rate bus')

    def get(self, action=None):
        if self._index is None:
            raise Exception('cannot call get on a Bus that has been freed')

        if self._num_channels == 1:
            if action is None:
                def func(val):
                    print(f'Bus {self._rate} index: {self._index} value: {val}')
                action = func

            def osc_func(msg, *args):
                # // The response is of the form [/c_set, index, value].
                # // We want "value," which is at index 2.
                action(msg[2])

            rdf.OSCFunc(
                osc_func, '/c_set', self._server.addr, # BUG: es c_set? está el comentario de arriba pero se ve raro, tal vez por eso lo comenta.
                arg_template=[self._index]
            ).one_shot()
            self._server.send_msg('/c_get', self._index)
        else:
            self.getn(self._num_channels, action)

    def get_msg(self):
        if self._index is None:
            raise Exception(
                "cannot construct a '/c_get' for a Bus that has been freed")
        return ['/c_get', self._index]

    def getn(self, count=None, action=None):
        if self._index is None:
            raise Exception('cannot call getn on a Bus that has been freed')

        if action is None:
            def func(vals):
                print(f'Bus {self._rate} index: {self._index} values: {vals}')
            action = func

        def osc_func(msg, *args):
            # // The response is of the form [/c_set, index, count, ...values].
            # // We want the values, which are at indexes 3 and above.
            action(msg[3:])

        rdf.OSCFunc(
            osc_func, '/c_setn', self._server.addr,
            arg_template=[self._index]
        ).one_shot() # NOTE: ver si one_shot se puede usar en las funcinoes de server que se liberan a sí mismas
        self._server.send_msg('/c_getn', self._index,
                              count or self._num_channels) # BUG: revisar los 'or'

    def getn_msg(self, count=None):
        if self._index is None:
            raise Exception(
                "cannot construct a '/c_getn' for a Bus that has been freed")
        return ['/c_getn', self._index, count or self._num_channels] # BUG: or no es lo mismo con número, e.g. si count es 0 pasa num_channels, aunque creo que no tiene sentido que sea cero.
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

    def alloc_bus(self):  # NOTE: Naming convention as Buffer for instance methods.
        pass

    def realloc_bus(self):
        pass

    # // alternate syntaxes
    # TODO: hay métodos que son importantes (e.g. asMap), VER.

    # UGen graph parameter interface #

    def as_ugen_input(self, *_):
        return self._index

    def as_control_input(self):
        return self._index

    def as_ugen_rate(self):
        return self._rate

    # Node parameter interface #
    # NOTE: Usa todos los valores por defecto de Object
