
import unittest

import sc3
from sc3.base.play import play
from sc3.synth.systemdefs import SystemDefs
from sc3.synth.node import Synth
from sc3.synth.ugens import Silent, SinOsc

sc3.init('nrt')

from sc3.base.main import main


class PlayTestCase(unittest.TestCase):
    def test_events(self):
        SystemDefs.add_synthdef('default')
        x = play({'freq': 440})
        self.assertIsNone(x)
        x = play(freq=550)
        self.assertIsNone(x)
        x = play({'freq': 660}, freq=770)  # Overrides.
        self.assertIsNone(x)

        score = main.process()
        main.reset()
        # print(score)

    def test_lambdas(self):
        x = play(lambda: Silent())
        self.assertIsInstance(x, Synth)
        x = play(lambda: 0)
        self.assertIsInstance(x, Synth)
        x = play(lambda: [0])
        self.assertIsInstance(x, Synth)
        x = play(lambda: [0.1, 0.2])  # Ignores.
        self.assertIsInstance(x, Synth)
        x = play(lambda: [SinOsc.kr(), 0.0])  # Out.kr, Silent.ar
        self.assertIsInstance(x, Synth)
        try:
            success = False
            x = play(lambda: [0, Silent(), 'error'])
        except Exception as e:
            self.assertIsInstance(e, ValueError)
            success = True
        finally:
            self.assertTrue(success)

        score = main.process()
        main.reset()
        # print(score)

    # def test_buffers(self):
    #     ...
