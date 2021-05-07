
import unittest

import sc3
sc3.init('nrt')

from sc3.base.stream import stream
from sc3.seq.patterns.listpatterns import Pseq
from sc3.seq.patterns.funcpatterns import *


class FuncPatternsTestCase(unittest.TestCase):
    def test_pif(self):
        # condition ends first.
        p = Pif(Pseq([True]), Pseq([1, 1]), Pseq([2, 2]))
        self.assertEqual(list(p), [1])

        # iftrue ends first.
        p = Pif(Pseq([True, False, True]), Pseq([1]), Pseq([2, 2]))
        self.assertEqual(list(p), [1, 2])

        # iffalse ends first.
        p = Pif(Pseq([True, False, False]), Pseq([1, 1]), Pseq([2]))
        self.assertEqual(list(p), [1, 2])

        # Constant values.
        p = Pif(None, Pseq([1, 1]), Pseq([2, 2]))
        self.assertEqual(list(p), [2, 2])

        p = Pif(Pseq([True, False]), None, None)
        self.assertEqual(list(p), [None, None])

        # Reset stream.
        p = Pif(Pseq([True, False]), 1, 2)
        q = stream(p)
        self.assertEqual(list(q), [1, 2])
        q.reset()
        self.assertEqual(list(q), [1, 2])


if __name__ == '__main__':
    unittest.main()
