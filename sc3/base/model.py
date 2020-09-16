"""Model.sc"""

import weakref

from . import functions as fn


__all__ = ['NotificationCenter']


class NotificationCenter():
    _registrations = weakref.WeakKeyDictionary()

    def __new__(cls):
        return cls

    @classmethod
    def notify(cls, obj, msg, *args, **kwargs):
        if obj in cls._registrations and msg in cls._registrations[obj]:
            for listener, action in cls._registrations[obj][msg].copy().items():
                fn.value(action, obj, msg, listener, *args, **kwargs)

    @classmethod
    def register(cls, obj, msg, listener, action):
        if obj not in cls._registrations:
            cls._registrations[obj] = dict()
        if msg not in cls._registrations[obj]:
            cls._registrations[obj][msg] = weakref.WeakKeyDictionary()
        cls._registrations[obj][msg][listener] = action

    @classmethod
    def unregister(cls, obj, msg=None, listener=None):
        err = False
        try:
            if msg is None:
                del cls._registrations[obj]
            elif listener is None:
                del cls._registrations[obj][msg]
            else:
                del cls._registrations[obj][msg][listener]
        except KeyError as e:
            err = True
        if err:
            raise KeyError(
                f'no registration found for ({obj}, {msg}, {listener})')

    @classmethod
    def register_one_shot(cls, obj, msg, listener, action):
        def one_shot_action(*args):
            action(*args)
            cls.unregister(obj, msg, listener)
        cls.register(obj, msg, listener, one_shot_action)

    @classmethod
    def registration_exists(cls, obj, msg, listener):
        if obj in cls._registrations\
        and msg in cls._registrations[obj]\
        and listener in cls._registrations[obj][msg]:
            return True
        else:
            return False

    @classmethod
    def clear(cls):
        cls._registrations = weakref.WeakKeyDictionary()
