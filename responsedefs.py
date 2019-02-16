"""ResponseDefs.sc"""

from abc import ABC, abstractmethod

import supercollie.systemactions as sac
import supercollie.model as mdl
import supercollie.main as main


class AbstractResponderFunc(ABC):
    _all_func_proxies = set()

    def __init__(self):
        # tienen solo getter
        self._func = None # @property, no inicializa
        self.src_id = None # no inicializa
        self.enabled = False
        self.dispatcher = None # no inicializa
        self._permanent = False # @property

    def enable(self):
        if not self.enabled:
            if not self.permanent:
                sac.CmdPeriod.add(self)
            self.dispatcher.add(self)
            self.enabled = True
            type(self)._all_func_proxies.add(self)

    def disable(self):
        if not self.permanent:
            sac.CmdPeriod.remove(self)
        self.dispatcher.remove(self)
        self.enabled = False

    @property
    def func(self):
        return self._func

    @func.setter
    def func(self, value):  # prFunc_
        self._func = value
        mdl.NotificationCenter.notify(self, 'function', self)

    def cmd_period(self):
        self.free()

    def one_shot(self):
        wrapped_func = self._func

        def one_shot_func(*args):
            self.free()
            wrapped_func(*args)
        self.func = one_shot_func

    @property
    def permanent(self):
        return self._permament

    @permanent.setter
    def permanent(self, value):
        self._permament = value
        if value and self.enabled:
            sac.CmdPeriod.remove(self)
        else:
            sac.CmdPeriod.add(self)

    def free(self):
        type(self)._all_func_proxies.remove(self)
        self.disable()

    def clear(self):
        self.func = None

    @classmethod
    def all_func_proxies(cls):
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


class AbstractDispatcher(ABC):
    '''Defines the required interface.'''
    all = set()

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
    def value(self):
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

    def update(self):
        '''Code here to update any changed state in this dispatcher's
        proxies, e.g. a new function; default does nothing.'''
        pass


# // basis for the default dispatchers
# // uses function wrappers for matching
class AbstractWrappingDispatcher(AbstractDispatcher):
    def __init__(self):
        super().__init__()
        self.active = dict() # NOTE: tal vez sea mejor hacerlas privadas
        self.wrapped_funcs = dict()

    def add(self, func_proxy):
        mdl.NotificationCenter.register(
            func_proxy, 'function', # NOTE: es addDependant, el msj es function en update de esta clase, el center debería poder reponder a cualquier mensaje en un caso así
            self, self.update
        )
        func = self.wrap_func(func_proxy)
        self.wrapped_funcs[func_proxy] = func
        keys = self.get_keys_for_func_proxy(func_proxy)
        for key in keys:
            try:
                self.active[key].append(func)
            except KeyError:
                self.active[key] = [func]
        if not self.registered:
            self.register

    def remove(self, func_proxy):
        mdl.NotificationCenter.unregister(func_proxy, 'function', self) # NOTE: es addDependant, el msj es function en update de esta clase
        keys = self.get_keys_for_func_proxy(func_proxy)
        func = self.wrapped_funcs[func_proxy]
        for key in keys:
            self.active[key].remove(func)
        del self.wrapped_funcs[func_proxy]
        if len(self.active) == 0:
            self.unregiter()

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

    def update(self, *args):
        self.update_func_for_func_proxy(args[0])

    def free(self):
        for func_proxy in self.wrapped_funcs:
            mdl.NotificationCenter.unregister(func_proxy, 'function', self)
        super().free()


# // The default dispatchers below store by the 'most significant' message argument for fast lookup
# // These are for use when more than just the 'most significant' argument needs to be matched
class AbstractMessageMatcher(ABC):
    def __init__(self):
        self.func = None

    @abstractmethod
    def value(self):
        pass


# OSC #


class OSCMessageDispatcher(AbstractWrappingDispatcher):
    def __init__(self):
        super().__init__()

    def wrap_func(self, func_proxy):
        func = func_proxy.func
        src_id = func_proxy.src_id
        recv_port = getattr(func_proxy, 'recv_port', None)
        arg_template = getattr(func_proxy, 'arg_template', None)
        if arg_template is not None:
            func = OSCArgsMatcher(arg_template, func)
        if src_id is not None and recv_port is not None:
            return OSCFuncBothMessageMatcher(src_id, recv_port, func)
        elif src_id is not None:
            return OSCFuncAddrMessageMatcher(src_id, func)
        elif recv_port is not None:
            return OSCFuncRecvPortMessageMatcher(recv_port, func)
        else:
            return func

    def get_keys_for_func_proxy(self, func_proxy):
        return [func_proxy.path]

    def value(self, msg, time, addr, recv_port):
        for func in self.active[msg[0]]:
            func(msg, time, addr, recv_port)

    def register(self):
        # thisProcess.addOSCRecvFunc(this) # BUG: TODO liblo, Main, y ver por qué llama desde thisProcess porque Main no se relaciona con Thread
        self.registered = True

    def unregister(self):
        # thisProcess.removeOSCRecvFunc(this) # BUG: TODO liblo, Main
        self.registered = False

    def type_key(self):
        return 'OSC unmatched'


class OSCMessagePatternDispatcher(OSCMessageDispatcher):
    def __init__(self):
        super().__init__()

    def value(self, msg, time, addr, recv_port):
        pattern = msg[0]
        for key, funcs in self.active.items():
            if match_osc_address_pattern(key, patter): # BUG: implementar
                for func in funcs:
                    func(msg, time, addr, recv_port)

    def type_key(self):
        return 'OSC matched'


class OSCFunc(AbstractResponderFunc):
    default_dispatcher = OSCMessageDispatcher()
    default_matching_dispatcher = OSCMessagePatternDispatcher()

    @staticmethod
    def _trace_func_show_status(msg, time, addr, recv_port):
        msg = 'OSC Message Received:\n'
        msg += '    time: {}\n'
        msg += '    address: {}\n'
        msg += '    recv_port: {}\n'
        msg += '    msg: {}'
        print(msg.format(time, addr, recv_port, msg)) # BUG: log

    @staticmethod
    def _trace_func_hide_status(msg, time, addr, recv_port):
        if msg[0] == '/status.reply'\
        and any(x.addr == self.addr for x in srv.Server.all):
            return
        OSCFunc._trace_func_show_status(msg, time, addr, recv_port)

    _trace_func = _trace_func_show_status
    _trace_running = False

    def __init__(self, func, path, src_id=None, recv_port=None,
                 arg_template=None, dispatcher=None):
        super().__init__()
        if path[0] != '/':
            path = '/' + path
        self.path = path
        self.src_id = src_id
        self.recv_port = recv_port
        if recv_port is not None\
        and main.Main.current_TimeThread.open_udp_port(recv_port): # BUG: implementar, ver por qué: thisProcess openUDPPort(recvPort).not
            raise Exception('could not open UDP port {}'.format(recv_port))
        self.arg_template = arg_template
        self._func = func
        self.dispatcher = dispatcher or type(self).default_dispatcher
        self.enable()
        type(self)._all_func_proxies.add(self)

    @classmethod
    def matching(cls, func, path, src_id=None,
                 recv_port=None, arg_template=None):
        obj = cls.__new__()
        obj.__init__(func, path, src_id, recv_port, arg_template,
                     cls.default_matching_dispatcher)
        return obj

    @classmethod
    def cmd_period(cls):
        cls.trace(False)

    @classmethod
    def trace(cls, flag=True, hide_status_msg=False):
        if flag:
            if not cls._trace_running:
                if hide_status_msg:
                    cls._trace_func = cls._trace_func_hide_status
                else:
                    cls._trace_func = cls._trace_func_show_status
                # thisProcess.addOSCRecvFunc(traceFunc) # BUG: implementar
                sac.CmdPeriod.add(cls)
                cls._trace_running = True
        else:
            # thisProcess.removeOSCRecvFunc(traceFunc) # BUG: implementar
            sac.CmdPeriod.remove(cls)
            cls._trace_running = False

    def __repr__(self):
        string = '{}({}, {}, {}, {})'
        return string.format(type(self).__name__, self.path, self.src_id,
                             self.recv_port, self.arg_template)


class OSCDef(OSCFunc):
    pass


# // if you need to test for address func gets wrapped in this
class OSCFuncAddrMessageMatcher(AbstractMessageMatcher):
    pass


# // if you need to test for recvPort func gets wrapped in this
class OSCFuncRecvPortMessageMatcher(AbstractMessageMatcher):
    pass


class OSCFuncBothMessageMatcher(AbstractMessageMatcher):
    pass


class OSCArgsMatcher(AbstractMessageMatcher):
    pass


# MIDI #

# sigue...
