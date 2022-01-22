
from abc import ABC, abstractmethod
import logging


__all__ = ['MidiRtInterface', 'MidiNrtInterface']


_logger = logging.getLogger(__name__)


class MidiInterface(ABC):
    ...

    @abstractmethod
    def _send(self, msg, target):
        pass


class MidiRtInterface(MidiInterface):
    ...


class MidiNrtInterface(MidiInterface):
    ...


class MidiScore():
    ...
