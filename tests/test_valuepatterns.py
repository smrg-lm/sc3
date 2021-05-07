
import unittest
import math

import sc3
sc3.init('nrt')

from sc3.base.main import main
from sc3.base.stream import routine, embed
from sc3.base.clock import TempoClock
from sc3.seq.patterns.eventpatterns import Pbind
from sc3.seq.patterns.listpatterns import Pseq
from sc3.seq.patterns.valuepatterns import Ptime


class ValuePatternsTestCase(unittest.TestCase):
    def test_ptime(self):
        # Test not embedded.
        p = Pbind({
            'dur': Pseq([0.5, 0.5, 1], 2),
            'time': Pseq([Ptime(3), Ptime(3)])
        })
        for e in list(p):
            self.assertEqual(e['time'], 0.0)

        # Test embedded.
        result = []

        @routine.run(TempoClock(90/60))
        def test_routine():
            t = embed(Pseq([Ptime(3), Ptime(3)]))
            for i in range(6):
                result.append(next(t))
                yield 0.5

        main.process()
        for r, t in zip(result, [0.0, 0.5, 1] * 2):
            self.assertTrue(math.isclose(r, t))
