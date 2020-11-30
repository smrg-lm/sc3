
import unittest

import sc3
from sc3.synth.bus import Bus, AudioBus, ControlBus
from sc3.synth.server import s

sc3.init()


# TODO: Needs a server in travis.

class BusTestCase(unittest.TestCase):
    def test_common_interface(self):
        b1 = ControlBus(5)
        b2 = ControlBus.new_from(b1, 3)
        self.assertEqual(b1.rate, b2.rate)
        self.assertEqual(b1.index + 3, b2.index)
        self.assertEqual(b2.channels, 1)
        ...

    def test_audiobus_interface(self):
        b = AudioBus()
        self.assertEqual(b.channels, 1)
        self.assertEqual(b.rate, 'audio')
        b = AudioBus(8)
        self.assertEqual(b.channels, 8)
        ...

    def test_controlbus_interface(self):
        b = ControlBus()
        self.assertEqual(b.channels, 1)
        self.assertEqual(b.rate, 'control')
        b = ControlBus(8)
        self.assertEqual(b.channels, 8)
        ...
