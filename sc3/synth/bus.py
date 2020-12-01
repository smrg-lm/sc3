"""Bus.sc"""

import logging

from . import _graphparam as gpp
from . import server as srv
from ..base import utils as utl
from ..base import responsedefs as rdf


__all__ = ['AudioBus', 'ControlBus']


_logger = logging.getLogger(__name__)


class BusException(Exception):
    pass


class BusAlreadyFreed(BusException):
    def __init__(self, method=None):
        if method is not None:
            self.args = (f"'{method}' method called",)


class Bus(gpp.UGenParameter, gpp.NodeParameter):
    '''Client side representation of server buses.

    Bus objects are used to keep track and manage the buses being
    used in the server, they can be passed as arguments instead
    of using the bus number directly.

    From ControlBus objects bus values can be obtained or assigned
    via OSC commands.

    Parameters
    ----------
    num_channels : int
        Number of channels, default is 1.
    server : Server
        Target server.
    index : int
        Sets the bus index. If ``index`` is None bus number
        is automatically allocated (client side) by the bus
        allocator class.
    '''

    # @classmethod
    # def audio(cls, channels=1, server=None, index=None):
    #     return AudioBus(channels, server, index)
    #
    # @classmethod
    # def control(cls, channels=1, server=None, index=None):
    #     return ControlBus(channels, server, index)

    @property
    def rate(self):
        return self._rate

    @property
    def index(self):
        return self._index

    @property
    def channels(self):
        return self._channels

    @property
    def server(self):
        return self._server

    @classmethod
    def new_from(cls, bus, offset, channels=1):
        if offset > bus._channels\
        or channels + offset > bus._channels:
            raise BusException(
                'new_from tried to reach outside '
                f'the channel range of {bus}')
        return cls(channels, bus.server, bus.index + offset)

    def free(self, clear=False):
        if self._index is None:
            _logger.warning('bus has already been freed')
            return
        if self._rate == 'audio':
            self._server._audio_bus_allocator.free(self._index)
        else:
            self._server._control_bus_allocator.free(self._index)
            if clear:
                self.fill(0, self._channels)
        self._index = None
        self._channels = None
        self._map_symbol = None

    # # Allow reallocation. Don't allow, use instances.
    #
    # def alloc(self):
    #     if self._rate == 'audio':
    #         self._index = self._server._audio_bus_allocator.alloc(
    #             self._channels)
    #     else:
    #         self._index = self._server._control_bus_allocator.alloc(
    #             self._channels)
    #     self._map_symbol = None
    #
    # def realloc(self):
    #     if self._index is None:
    #         raise BusAlreadyFreed('realloc')
    #     rate = self._rate
    #     num_channels = self._channels
    #     self.free()
    #     self._rate = rate
    #     self._channels = num_channels
    #     self.alloc()

    # setAll is fill(value, self._channels)
    # value_ is fill(value, self._channels)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented

        if self._index == other._index\
        and self._channels == other._channels\
        and self._rate == other._rate\
        and self._server == other._server:
            return True
        else:
            return False

    def __hash__(self):
        return hash(
            (type(self), self._index, self._channels,
            self._rate, self._server))

    def __repr__(self):
        return (
            f'{type(self).__name__}({self._channels}, '
            f'{self._index}, {self._server.name})')

    def as_map(self):
        if self._map_symbol is None:
            if self._index is None:
                raise BusException('bus not allocated')
            self._map_symbol = 'a' if self._rate == 'audio' else 'c'
            self._map_symbol += str(self._index)
        return self._map_symbol

    def sub_bus(self, offset, num_channels=1):
        return type(self).new_from(self, offset, num_channels)

    # ar
    # kr
    # play


    ### UGen graph parameter interface ###

    def _as_ugen_input(self, *_):
        return self._index

    def _as_ugen_rate(self):
        return self._rate


    ### Node parameter interface ###

    def _as_control_input(self):
        return self._index


class AudioBus(Bus):
    def __init__(self, channels=1, server=None, index=None):
        super(gpp.UGenParameter, self).__init__(self)
        self._channels = channels
        self._server = server or srv.Server.default
        self._rate = 'audio'
        if index is None:
            self._index = self._server._audio_bus_allocator.alloc(
                self._channels)
            if self._index is None:
                raise BusException(
                    'failed to get AudioBus bus allocated, channels '
                    f"= {self._channels}, server = {self._server.name}")
        else:
            self._index = index
        self._map_symbol = None

    # @property
    # def is_audio_io(self):
    #     return self._index < self._server.options.first_private_bus()


    ### Shared memory interface ###

    # def get_synchronous(self):
    #     ...

    # def getn_synchronous(self, count):
    #     ...

    # def set_synchronous(self, *values):
    #     ...

    # def setn_synchronous(self, values):
    #     ...


class ControlBus(Bus):
    def __init__(self, channels=1, server=None, index=None):
        super(gpp.UGenParameter, self).__init__(self)
        self._channels = channels
        self._server = server or srv.Server.default
        self._rate = 'control'
        if index is None:
            self._index = self._server._control_bus_allocator.alloc(
                self._channels)
            if self._index is None:
                raise BusException(
                    'failed to get ControlBus bus allocated, channels '
                    f'= {self._channels}, server = {self._server.name}')
        else:
            self._index = index
        self._map_symbol = None

    def set(self, *values):  # // shouldn't be larger than self._channels
        if self._index is None:
            raise BusAlreadyFreed('set')
        msg = ['/c_set']
        values = [[self._index + i, val] for i, val in enumerate(values)]
        msg.extend(utl.flat(values))
        self._server.send_bundle(0, msg)

    def set_msg(self, *values):
        if self._index is None:
            raise BusAlreadyFreed('set_msg')
        msg = ['/c_set']
        values = [[self._index + i, val] for i, val in enumerate(values)]
        msg.extend(utl.flat(values))
        return msg

    def setn(self, values):
        if self._index is None:
            raise BusAlreadyFreed('setn')
        msg = ['/c_setn', self._index, len(values)]
        msg.extend(values)
        self._server.send_bundle(0, msg)

    def setn_msg(self, values):
        if self._index is None:
            raise BusAlreadyFreed('setn_msg')
        msg = ['/c_setn', self._index, len(values)]
        msg.extend(values)
        return msg

    def set_at(self, offset, *values):
        if self._index is None:
            raise BusAlreadyFreed('set_at')
        msg = ['/c_set']
        values = [
            [self._index + offset + i, val] for i, val in enumerate(values)]
        msg.extend(utl.flat(values))
        self._server.send_bundle(0, msg)

    def setn_at(self, offset, values):
        if self._index is None:
            raise BusAlreadyFreed('setn_at')
        # // could throw an error if values.size > numChannels
        msg = ['/c_setn', self._index + offset, len(values)]
        msg.extend(values)
        self._server.send_bundle(0, msg)

    def set_pairs(self, *pairs):
        if self._index is None:
            raise BusAlreadyFreed('set_pairs')
        msg = ['/c_set']
        pairs = [[self._index + pair[0], pair[1]]\
                 for pair in utl.gen_cclumps(pairs, 2)]
        msg.extend(utl.flat(pairs))
        self._server.send_bundle(0, msg)

    def get(self, action=None):
        if self._index is None:
            raise BusAlreadyFreed('get')

        if self._channels == 1:
            if action is None:
                def default_action_func(val):
                    print(
                        f'{type(self).__name__} index: '
                        f'{self._index} value: {val}')
                action = default_action_func

            def get_func(msg, *_):
                # // The response is of the form [/c_set, index, value].
                # // We want "value," which is at index 2.
                action(msg[2])

            rdf.OscFunc(
                get_func, '/c_set', self._server.addr,
                arg_template=[self._index]).one_shot()
            self._server.send_msg('/c_get', self._index)
        else:
            self.getn(self._channels, action)

    def get_msg(self):
        if self._index is None:
            raise BusAlreadyFreed('get_msg')
        return ['/c_get', self._index]

    def getn(self, count=None, action=None):
        if self._index is None:
            raise BusAlreadyFreed('getn')

        if action is None:
            def default_action_func(vals):
                print(
                    f'{type(self).__name__} index: '
                    f'{self._index} values: {vals}')
            action = default_action_func

        def getn_func(msg, *_):
            # // The response is of the form [/c_set, index, count, ...values].
            # // We want the values, which are at indexes 3 and above.
            action(msg[3:])

        rdf.OscFunc(
            getn_func, '/c_setn', self._server.addr,
            arg_template=[self._index]).one_shot()
        if count is None:
            count = self._channels
        self._server.send_msg('/c_getn', self._index, count)

    def getn_msg(self, count=None):
        if self._index is None:
            raise BusAlreadyFreed('getn_msg')
        if count is None:
            count = self._channels
        return ['/c_getn', self._index, count]

    def fill(self, value, num_channels):
        if self._index is None:
            raise BusAlreadyFreed('fill')
        # // Could throw an error if numChans > numChannels.
        self._server.send_bundle(
            None, ['/c_fill', self._index, num_channels, value])

    def fill_msg(self, value):
        if self._index is None:
            raise BusAlreadyFreed('fill_msg')
        return ['/c_fill', self._index, self._channels, value]
