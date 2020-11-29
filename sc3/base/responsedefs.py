"""ResponseDefs.sc"""

from abc import ABC, abstractmethod
import inspect
import logging

from ..synth import server as srv
from . import functions as fn
from . import systemactions as sac
from . import model as mdl
from . import main as _libsc3
from . import utils as utl
from ._oscmatch import osc_rematch_pattern as _match_osc_address_pattern


__all__ = ['OscFunc']


_logger = logging.getLogger(__name__)


class AbstractMessageMatcher(ABC):
    @abstractmethod
    def __call__(self):
        pass


class AbstractDispatcher(ABC):
    all = set()  # TODO: Not really used, needs a metaclass.

    def __init__(self):
        self.registered = False

    @abstractmethod
    def add(self, func_proxy):
        '''Proxies call this to add themselves to this dispatcher;
        should register this if needed.'''
        pass

    @abstractmethod
    def remove(self, func_proxy):
        '''Proxies call this to remove themselves from this dispatcher;
        should unregister if needed.'''
        pass

    @abstractmethod
    def __call__(self):
        pass

    @abstractmethod
    def register(self):
        '''Register this dispatcher to listen for its message type.'''
        pass

    @abstractmethod
    def unregister(self):
        '''Unregister this dispatcher so it no longer listens.'''
        pass

    def free(self):
        self.unregister()
        type(self).all.remove(self)

    @abstractmethod
    def type_key(self):
        '''This method must return an str.'''
        pass


class AbstractWrappingDispatcher(AbstractDispatcher):
    # // basis for the default dispatchers
    # // uses function wrappers for matching

    def __init__(self):
        super().__init__()
        self.active = dict()
        self.wrapped_funcs = dict()

    def add(self, func_proxy):
        mdl.NotificationCenter.register(
            func_proxy, 'function', self, self.update_func_for_func_proxy)
        func = self.wrap_func(func_proxy)
        self.wrapped_funcs[func_proxy] = func
        keys = self.get_keys_for_func_proxy(func_proxy)
        for key in keys:
            try:
                self.active[key].append(func)
            except KeyError:
                self.active[key] = [func]
        if not self.registered:
            self.register()

    def remove(self, func_proxy):
        mdl.NotificationCenter.unregister(func_proxy, 'function', self)
        keys = self.get_keys_for_func_proxy(func_proxy)
        func = self.wrapped_funcs[func_proxy]
        for key in keys:
            self.active[key].remove(func)
        del self.wrapped_funcs[func_proxy]
        if len(self.active) == 0:
            self.unregister()

    def update_func_for_func_proxy(self, func_proxy):
        func = self.wrap_func(func_proxy)
        old_func = self.wrapped_funcs[func_proxy]
        self.wrapped_funcs[func_proxy] = func
        keys = self.get_keys_for_func_proxy(func_proxy)
        for key in keys:
            i = self.active[key].index(old_func)
            self.active[key][i] = func

    @abstractmethod
    def wrap_func(self, func_proxy):
        pass

    @abstractmethod
    def get_keys_for_func_proxy(self, func_proxy):
        pass

    def free(self):
        for func_proxy in self.wrapped_funcs:
            mdl.NotificationCenter.unregister(func_proxy, 'function', self)
        super().free()


class AbstractResponderFunc(ABC):
    # _all_func_proxies is set()

    def __init__(self):
        self._func = None
        self._permanent = False
        self.src_id = None
        self.enabled = False
        self.dispatcher = None

    @property
    def func(self):
        return self._func

    @func.setter
    def func(self, value):  # prFunc_
        self._func = value
        mdl.NotificationCenter.notify(self, 'function')

    @property
    def permanent(self):
        return self._permanent

    @permanent.setter
    def permanent(self, value):
        self._permanent = value
        if value and self.enabled:
            sac.CmdPeriod.remove(self.__on_cmd_period)
        else:
            sac.CmdPeriod.add(self.__on_cmd_period)

    def enable(self):
        if not self.enabled:
            if not self.permanent:
                sac.CmdPeriod.add(self.__on_cmd_period)
            self.dispatcher.add(self)
            self.enabled = True
            type(self)._all_func_proxies.add(self)

    def disable(self):
        if not self.permanent:
            sac.CmdPeriod.remove(self.__on_cmd_period)
        self.dispatcher.remove(self)
        self.enabled = False

    def __on_cmd_period(self):  # Avoid clash.
        self.free()

    def one_shot(self):
        wrapped_func = self._func

        def one_shot_func(*args):
            self.free()
            wrapped_func(*args)

        self.func = one_shot_func

    # def fix(self):  # Use oscfunc.permanent = True.
    #     self.permanent = True

    def free(self):
        cls = type(self)
        if self in cls._all_func_proxies:
            cls._all_func_proxies.remove(self)
        if self.enabled:
            self.disable()

    def clear(self):
        self.func = None

    @classmethod
    def _all_func_proxies(cls):
        result = dict()
        for func_proxy in cls._all_func_proxies:
            key = func_proxy.dispatcher.type_key()
            try:
                result[key].append(func_proxy)
            except KeyError:
                result[key] = [func_proxy]
        return result

    @classmethod
    def all_enabled(cls):
        result = dict()
        enabled_proxies = [x for x in cls._all_func_proxies if x.enabled]
        for func_proxy in enabled_proxies:
            key = func_proxy.dispatcher.type_key()
            try:
                result[key].append(func_proxy)
            except KeyError:
                result[key] = [func_proxy]
        return result

    @classmethod
    def all_disabled(cls):
        result = dict()
        disabled_proxies = [x for x in cls._all_func_proxies if not x.enabled]
        for func_proxy in disabled_proxies:
            key = func_proxy.dispatcher.type_key()
            try:
                result[key].append(func_proxy)
            except KeyError:
                result[key] = [func_proxy]
        return result


### OSC ###


class OscFuncAddrMessageMatcher(AbstractMessageMatcher):
    # // If you need to test for address func gets wrapped in this.
    def __init__(self, addr, func):
        self.addr = addr
        self.func = func

    def __call__(self, msg, time, addr, recv_port):
        if self.addr.addr == addr.addr\
        and (self.addr.port is None or self.addr.port == addr.port):  # was matchItem
            fn.value(self.func, msg, time, addr, recv_port)


class OscFuncRecvPortMessageMatcher(AbstractMessageMatcher):
    # // If you need to test for recvPort func gets wrapped in this.
    def __init__(self, recv_port, func):
        self.recv_port = recv_port
        self.func = func

    def __call__(self, msg, time, addr, recv_port):
        if self.recv_port == recv_port:
            fn.value(self.func, msg, time, addr, recv_port)


class OscFuncBothMessageMatcher(AbstractMessageMatcher):
    def __init__(self, addr, recv_port, func):
        self.addr = addr
        self.recv_port = recv_port
        self.func = func

    def __call__(self, msg, time, addr, recv_port):
        if  self.addr.addr == addr.addr\
        and (self.addr.port is None or self.addr.port == addr.port)\
        and self.recv_port == recv_port:
            fn.value(self.func, msg, time, addr, recv_port)


class OSCArgsMatcher(AbstractMessageMatcher):
    def __init__(self, arg_template, func):
        self.arg_template = utl.as_list(arg_template)
        self.func = func

    def __call__(self, msg, time, addr, recv_port):
        args = msg[1:]
        for i, item in enumerate(self.arg_template):
            if item is not None and item != args[i]:  # was matchItem.not
                return
        fn.value(self.func, msg, time, addr, recv_port)


# // The default dispatchers below store by the 'most significant'
# // message argument for fast lookup. These are for use when more
# // than just the 'most significant' argument needs to be matched.

class OSCMessageDispatcher(AbstractWrappingDispatcher):
    def wrap_func(self, func_proxy):
        func = func_proxy.func
        src_id = func_proxy.src_id
        recv_port = getattr(func_proxy, 'recv_port', None)
        arg_template = getattr(func_proxy, 'arg_template', None)
        if arg_template is not None:
            func = OSCArgsMatcher(arg_template, func)
        if src_id is not None and recv_port is not None:
            return OscFuncBothMessageMatcher(src_id, recv_port, func)
        elif src_id is not None:
            return OscFuncAddrMessageMatcher(src_id, func)
        elif recv_port is not None:
            return OscFuncRecvPortMessageMatcher(recv_port, func)
        else:
            return func

    def get_keys_for_func_proxy(self, func_proxy):
        return [func_proxy.path]

    def __call__(self, msg, time, addr, recv_port):
        if msg[0] in self.active:
            for func in self.active[msg[0]]:
                fn.value(func, msg, time, addr, recv_port)

    def register(self):
        _libsc3.main.add_osc_recv_func(self) # thisProcess.addOSCRecvFunc(this)
        self.registered = True

    def unregister(self):
        _libsc3.main.remove_osc_recv_func(self) # thisProcess.removeOSCRecvFunc(this)
        self.registered = False

    def type_key(self):
        return 'OSC unmatched'


class OSCMessagePatternDispatcher(OSCMessageDispatcher):
    def __call__(self, msg, time, addr, recv_port):
        pattern = msg[0]
        for key, funcs in self.active.items():
            if _match_osc_address_pattern(pattern, key):
                for func in funcs:
                    fn.value(func, msg, time, addr, recv_port)

    def type_key(self):
        return 'OSC matched'


class OscFunc(AbstractResponderFunc):
    _all_func_proxies = set()
    default_dispatcher = OSCMessageDispatcher()
    default_matching_dispatcher = OSCMessagePatternDispatcher()

    @classmethod
    def _trace_func_show_status(cls, msg, time, addr, recv_port):
        log = ('OSC Message Received:\n'
               f'    time: {time}\n'
               f'    address: {addr}\n'
               f'    recv_port: {recv_port}\n'
               f'    msg: {msg}')
        _logger.info(log)

    @classmethod
    def _trace_func_hide_status(cls, msg, time, addr, recv_port):
        if msg[0] == '/status.reply'\
        and any(server.addr == addr for server in srv.Server.all):
            return
        cls._trace_func_show_status(msg, time, addr, recv_port)

    _trace_func = _trace_func_show_status
    _trace_running = False

    def __init__(self, func, path, src_id=None, *, recv_port=None,
                 arg_template=None, dispatcher=None):
        super().__init__()
        if path[0] != '/':
            path = '/' + path
        self.path = path
        self.src_id = src_id
        self.recv_port = recv_port
        if recv_port is not None:
            # This whould require to create another OscUdpInterface or
            # OSCUDPServer which is something I don't want because I don't
            # know why this is important of if it works for TCP in sclang.
            # OscFuncRecvPortMessageMatcher and OscFuncBothMessageMatcher
            # are needed only by this feature.
            _libsc3.main.open_udp_port(recv_port)  # Not implemented.
        self.arg_template = arg_template
        self._func = func
        self.dispatcher = dispatcher or type(self).default_dispatcher
        self.enable()
        # type(self)._all_func_proxies.add(self)  # Called by enable() already.

    @classmethod
    def matching(cls, func, path, src_id=None,
                 recv_port=None, arg_template=None):
        return cls(
            func, path, src_id, recv_port, arg_template,
            cls.default_matching_dispatcher)

    @classmethod
    def __on_cmd_period(cls):  # Avoid clash.
        cls.trace(False)

    @classmethod
    def trace(cls, flag=True, hide_status_msg=False):
        if flag and not cls._trace_running:
            if hide_status_msg:
                cls._trace_func = cls._trace_func_hide_status
            else:
                cls._trace_func = cls._trace_func_show_status
            _libsc3.main.add_osc_recv_func(cls._trace_func)
            sac.CmdPeriod.add(cls.__on_cmd_period)
            cls._trace_running = True
        elif cls._trace_running:
            _libsc3.main.remove_osc_recv_func(cls._trace_func)
            sac.CmdPeriod.remove(cls.__on_cmd_period)
            cls._trace_running = False

    def __repr__(self):
        return (
            f'{type(self).__name__}({self.path}, {self.src_id}, '
            f'{self.recv_port}, {self.arg_template})')


# class OscDef(OscFunc):


### MIDI ###

# MIDI implementation needs some thought, mostly because there
# are many libraries and so far sc3 is dependencies free.

class MidiFuncSrcMessageMatcher(AbstractMessageMatcher):
    # // If you need to test for srcID func gets wrapped in this.
    ...


class MidiFuncChanMessageMatcher(AbstractMessageMatcher):
    # // If you need to test for chan func gets wrapped in this.
    ...


class MidiFuncChanArrayMessageMatcher(AbstractMessageMatcher):
    # // If you need to test for chanArray func gets wrapped in this.
    ...


class MidiFuncSrcMessageMatcherNV(MidiFuncSrcMessageMatcher):
    # // Version for message types which don't pass a val.
    ...


class MidiFuncSrcSysMessageMatcher(MidiFuncSrcMessageMatcher):
    # // Version for message types which don't pass a val.
    ...


class MidiFuncSrcSysMessageMatcherND(MidiFuncSrcMessageMatcher):
    ...


class MidiFuncBothMessageMatcher(AbstractMessageMatcher):
    # // If you need to test for chan and srcID func gets wrapped in this.
    ...


class MidiFuncBothCAMessageMatcher(AbstractMessageMatcher):
    # // If you need to test for chanArray and srcID func gets wrapped in this.
    ...


class MIDIValueMatcher(AbstractMessageMatcher):
    # // If you want to test for the actual message value,
    # // the func gets wrapped in this.
    ...


class MIDIMessageDispatcher(AbstractWrappingDispatcher):
    # // For 'note_on', 'note_off', 'control', 'polytouch'.
    ...


class MIDIMessageDispatcherNV(MIDIMessageDispatcher):
    # // For 'touch', 'program', 'bend'.
    ...


class MIDISysexDispatcher(MIDIMessageDispatcher):
    # // For 'sysex'.
    ...


class MIDISysDataDispatcher(MIDIMessageDispatcher):
    # // sysrt with data.
    ...

class MIDISysDataDropIndDispatcher(MIDISysDataDispatcher):
    ...


class MIDISysNoDataDispatcher(MIDISysDataDispatcher):
    ...


class MIDIMTCtoSMPTEDispatcher(MIDISysexDispatcher):
    ...


class MIDISMPTEAssembler(AbstractMessageMatcher):
    # // Thanks to nescivi for code from MTC class!!
    ...


class MidiFunc(AbstractResponderFunc):
    ...

# class MidiDef(MidiFunc):
