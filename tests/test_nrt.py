
import unittest
import logging
import math
import pathlib
import shutil

import sc3
sc3.init('nrt')

from sc3.base.main import main
from sc3.base.stream import routine
from sc3.base.play import play
from sc3.base.clock import TempoClock
from sc3.synth.systemdefs import SystemDefs
from sc3.synth.server import Server


logger = logging.getLogger(__name__)


class NrtTestCase(unittest.TestCase):
    def test_process(self):
        SystemDefs.add_synthdef('default')

        @routine
        def r1():
            for i in range(5):
                play(freq=i)  #, sustain=2)
                yield 1

        r1.play()

        score = main.process()
        self.assertEqual(main.elapsed_time(), 5.0)

        expected = [
            [0.0, ['/g_new', 1, 0, 0]],
            [0.0, ['/d_recv', bytearray(), None]],
            [0.0, ['/s_new', 'default', 1000, 0, 1, 'freq', 0]],
            [0.8, ['/n_set', 1000, 'gate', 0]],
            [1.0, ['/s_new', 'default', 1001, 0, 1, 'freq', 1]],
            [1.8, ['/n_set', 1001, 'gate', 0]],
            [2.0, ['/s_new', 'default', 1002, 0, 1, 'freq', 2]],
            [2.8, ['/n_set', 1002, 'gate', 0]],
            [3.0, ['/s_new', 'default', 1003, 0, 1, 'freq', 3]],
            [3.8, ['/n_set', 1003, 'gate', 0]],
            [4.0, ['/s_new', 'default', 1004, 0, 1, 'freq', 4]],
            [4.8, ['/n_set', 1004, 'gate', 0]],
            [5.0, ['/c_set', 0, 0]]
        ]

        self.assertEqual(len(score.list), len(expected))
        for i, (res, exp) in enumerate(zip(score.list, expected)):
            self.assertEqual(res[0], exp[0])
            if i != 1:
                self.assertEqual(res[1], exp[1])

        if shutil.which(Server.default.options.program):
            # Test file exist and stat.
            file = pathlib.Path('test.aiff')
            self.assertFalse(file.exists())
            score.render(file)
            self.assertTrue(file.exists())
            self.assertEqual(file.stat().st_size, 1764456)
            file.unlink()
        else:
            logger.warning(
                f'{Server.default.options.program} server not installed')

        # Test reset time/tempo.
        main.reset()

        @routine
        def r1():
            for i in range(6):
                play(freq=i)
                yield 1

        r1.play(TempoClock(3))
        score = main.process()
        self.assertTrue(math.isclose(main.elapsed_time(), 2.0))
