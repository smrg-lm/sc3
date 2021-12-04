"""Bus.sc"""

import logging

from . import _graphparam as gpp
from . import server as srv
from ..base import utils as utl
from ..base import responders as rpd


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
    channels : int
        Number of channels, default is 1.
    server : Server
        Target server.
    index : int
        Sets the bus index. If ``index`` is None bus number
        is automatically allocated (client side) by the bus
        allocator class.

    '''

    @property
    def index(self):
        '''Bus index in the server.

        '''

        return self._index

    @property
    def channels(self):
        '''Number of channels.

        '''

        return self._channels

    @property
    def server(self):
        '''Target server of the bus object.

        '''

        return self._server

    @classmethod
    def new_from(cls, bus, offset, channels=1):
        '''Create a new object from ``bus``.

        Parameters
        ----------
        bus: Bus
            The bus from wich to create the new object.
        offset: int
            Channel offset from wich to create the new bus object.
        channels: int
            Number of channels from to count from ``offset``.

        '''

        if offset > bus._channels\
        or channels + offset > bus._channels:
            raise BusException(
                'new_from tried to reach outside '
                f'the channel range of {bus}')
        return cls(channels, bus.server, bus.index + offset)

    def sub_bus(self, offset, channels=1):
        '''Return a sub-range of channels from this bus.

        '''

        return type(self).new_from(self, offset, channels)

    def free(self):
        raise NotImplementedError

    # Don't allow reallocation, better to use instances.
    # alloc
    # reralloc

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented

        if self._index == other._index\
        and self._channels == other._channels\
        and self._server == other._server:
            return True
        else:
            return False

    def __hash__(self):
        return hash(
            (type(self), self._index, self._channels, self._server))

    def __repr__(self):
        return (
            f'{type(self).__name__}({self._channels}, '
            f'{self._server.name}, {self._index})')


    ### UGen graph parameter interface ###

    def _as_ugen_input(self, *_):
        return self._index


    ### Node parameter interface ###

    def _as_control_input(self):
        return self._index


class AudioBus(Bus):
    def __init__(self, channels=1, server=None, index=None):
        super(gpp.UGenParameter, self).__init__(self)
        self._channels = channels
        self._server = server or srv.Server.default
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

    def free(self):
        '''Free the bus object index.

        '''

        if self._index is None:
            _logger.warning('AudioBus has already been freed')
            return
        self._server._audio_bus_allocator.free(self._index)
        self._index = None
        self._channels = None
        self._map_symbol = None

    def as_map(self):
        '''Return the map string of this bus.

        '''

        if self._map_symbol is None:
            if self._index is None:
                raise BusException('bus not allocated')
            self._map_symbol = 'a' + str(self._index)
        return self._map_symbol

    ### Shared memory interface ###

    # def get_synchronous(self):
    #     ...

    # def getn_synchronous(self, count):
    #     ...

    # def set_synchronous(self, *values):
    #     ...

    # def setn_synchronous(self, values):
    #     ...


    ### UGen graph parameter interface ###

    def _as_ugen_rate(self):
        return 'audio'


class ControlBus(Bus):
    def __init__(self, channels=1, server=None, index=None):
        super(gpp.UGenParameter, self).__init__(self)
        self._channels = channels
        self._server = server or srv.Server.default
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

    def clear(self):
        '''Set bus value to zero for all channels.

        '''

        self.fill(0, self._channels)

    def free(self):
        '''Free the bus object index.

        '''

        if self._index is None:
            _logger.warning('ControlBus has already been freed')
            return
        self._server._control_bus_allocator.free(self._index)
        self._index = None
        self._channels = None
        self._map_symbol = None

    def as_map(self):
        '''Return the map string of this bus.

        '''

        if self._map_symbol is None:
            if self._index is None:
                raise BusException('bus not allocated')
            self._map_symbol = 'c' + str(self._index)
        return self._map_symbol

    def set(self, *values):
        '''Set bus value or values for consecutive channels.

        This method uses '/c_set' command. The length of ``*values``
        shouldn't be larger than the number of channels or it will
        override values set by other bus objects.

        '''

        if self._index is None:
            raise BusAlreadyFreed('set')
        msg = [
            '/c_set',
            *[[self._index + i, v] for i, v in enumerate(values)]]
        self._server.addr.send_msg(*utl.flat(msg))

    def setn(self, values):
        '''Set the list of ``values`` to consecutive channels.

        This method uses '/c_setn' command that sets a list of values to a
        contiguous range of buses. The length of ``*values`` shouldn't be
        larger than the number of channels or it will override values set by
        other bus objects.

        '''

        if self._index is None:
            raise BusAlreadyFreed('setn')
        self._server.addr.send_msg(
            '/c_setn', self._index, len(values), *values)

    def set_at(self, offset, *values):
        '''Set the value of consecutive buses using '/c_set' command.

        Parameters
        ----------
        offset : int
            Start index relative to this bus index.
        *values : float
            A scalar value for each consecutive bus.

        Notes
        -----
        Booth ``set_at`` and ``set_pairs`` are different parameter
        organizations for the '/c_set' command.

        '''

        if self._index is None:
            raise BusAlreadyFreed('set_at')
        msg = [
            '/c_set',
            *[[self._index + offset + i, v] for i, v in enumerate(values)]]
        self._server.addr.send_msg(*utl.flat(msg))

    def setn_at(self, offset, values):
        '''Set the value of consecutive buses using '/c_setn' command.

        Parameters
        ----------
        offset : int
            Start index relative to this bus index.
        values : list[float]
            A list of values for each consecutive bus.

        '''

        if self._index is None:
            raise BusAlreadyFreed('setn_at')
        # // could throw an error if values.size > numChannels
        self._server.addr.send_msg(
            '/c_setn', self._index + offset, len(values), *values)

    def set_pairs(self, *pairs):
        '''Set the value of buses by index relative to this bus.

        Parameters
        ----------
        *paris : tuple(int, float)
            Tuples or lists indicating the index and value of each bus.

        Notes
        -----
        Booth ``set_at`` and ``set_pairs`` are different parameter
        organizations for the '/c_set' command.

        '''

        if self._index is None:
            raise BusAlreadyFreed('set_pairs')
        msg = [
            '/c_set',
            *[[self._index + pair[0], pair[1]]
            for pair in utl.gen_cclumps(pairs, 2)]]
        self._server.addr.send_msg(*utl.flat(msg))

    def get(self, action=None):
        '''Get the bus current value.

        Parameters
        ----------
        action: function
            A function to be evaluated with the bus' value as argument.

        '''

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

            rpd.OscFunc(
                get_func, '/c_set', self._server.addr,
                arg_template=[self._index]).one_shot()
            self._server.addr.send_msg('/c_get', self._index)
        else:
            self.getn(self._channels, action)

    def getn(self, count=None, action=None):
        '''Get consecutive channels' values from this bus index.

        Parameters
        ----------
        count: int
            Number of channels to get the values from.
        action: function
            A function to be evaluated with a list of buses' values
            as argument.

        '''

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

        rpd.OscFunc(
            getn_func, '/c_setn', self._server.addr,
            arg_template=[self._index]).one_shot()
        if count is None:
            count = self._channels
        self._server.addr.send_msg('/c_getn', self._index, count)

    def fill(self, value, channels):
        '''Set contiguous buses from this bus index to a single value.

        This method uses '/c_fill' command.

        Parameters
        ----------
        value: int | float
            Value to assign in the buses.
        channels: int
            Number of contiguous buses to set.

        '''

        if self._index is None:
            raise BusAlreadyFreed('fill')
        # // Could throw an error if numChans > numChannels.
        self._server.addr.send_msg('/c_fill', self._index, channels, value)

    # setAll is fill(value, self._channels)
    # value_ is fill(value, self._channels)


    ### UGen graph parameter interface ###

    def _as_ugen_rate(self):
        return 'control'
