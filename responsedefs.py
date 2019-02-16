"""ResponseDefs.sc"""

from abc import ABC, abstractmethod

import supercollie.systemactions as sac
import supercollie.model as mdl


class AbstractResponderFunc(ABC):
    _all_func_proxies = set()

    def __init__(self):
        # tienen solo getter
        self._func_list = [] # no inicializa, func es/se convierte en FunctionList
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
    def func_list(self):
        return self._func_list

    @func_list.setter
    def func_list(self, value):  # prFunc_
        self._func_list = list(value)  # se asegura que sea un iterable compatible y hace una copia si es una lista
        mdl.NotificationCenter.notify(self, 'function', self)

    def add(self, func):
        self._func_list.append(func)
        mdl.NotificationCenter.notify(self, 'function', self)

    def remove(self, func):
        self._func_list.remove(func)
        mdl.NotificationCenter.notify(self, 'function', self)

    def cmd_period(self):
        self.free()

    def one_shot(self):
        wrapped_func_list = self._func_list

        def one_shot_func(*args):
            self.free()
            for func in self._func_list:
                func(*args)
        self.func_list = [one_shot_func]

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
        self.func_list = []

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
        self.func = None # BUG: no se si será func_list

    @abstractmethod
    def value(self):
        pass


# OSC #


class OSCMessageDispatcher(AbstractWrappingDispatcher):
    def __init__(self):
        super().__init__()

    def wrap_func(self, func_proxy):
        func_list = func_proxy.func_list
        src_id = func_proxy.src_id
        recv_port = getattr(func_proxy, 'recv_port', None)
        arg_template = getattr(func_proxy, 'arg_template', None)
        if arg_template is not None:
            # BUG: NOTE: TODO: FIXME: STOP:
            # func'_list' REALMENTE ES NECESARIO QUE FUNCIONE PARA FUNCTIONLIST?
            # Creo que se pueden declarar OSCFunc distintas para el mismo
            # mensaje OSC, funclist tal vez sea una extravagancia de sclang.
            # VER PRUEBAS EN SCLANG PREFIERO NO PONERLA SI ES ASÍ.

            # HACER PARA FUNCIÓN SIMPLE, NO HAY FUNCTIONLIST AQUÍ


class OSCMessagePatternDispatcher(OSCMessageDispatcher):
    pass


class OSCFunc(AbstractResponderFunc):
    pass


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
