
import unittest
import math

import sc3
sc3.init('nrt')

from sc3.base.main import main
from sc3.base.clock import TempoClock
from sc3.base.stream import routine


# NOTE: These tests are duplicated for test_clock_rt.py and need sync.

class ClockTestCase(unittest.TestCase):
    def test_logical_time_delta(self):
        tempo = 1000  # Float point resolution may affect tests if big.
        delta = 1

        @routine
        def test():
            # Clock is created inside a main routine to avoid
            # timing offset relative to elapsed time updates.
            clock = TempoClock(tempo)

            @routine
            def r():
                nonlocal clock
                beats = clock.beats
                elapsed_delta = 0
                t1 = main.current_tt._seconds
                self.assertTrue(math.isclose(beats, elapsed_delta))
                yield delta

                beats = clock.beats
                elapsed_delta += delta
                t2 = main.current_tt._seconds
                self.assertTrue(math.isclose(beats, elapsed_delta))
                yield delta

                beats = clock.beats
                elapsed_delta += delta
                t3 = main.current_tt._seconds
                self.assertTrue(math.isclose(beats, elapsed_delta))
                self.assertTrue(math.isclose(t2 - t1, t3 - t2))

            r.play(clock)

        test.play()
        main.process()

    def test_initial_values(self):

        @routine
        def example():
            offset = 5
            # Starts from zero by default.
            t = TempoClock(1)
            self.assertTrue(math.isclose(t.beats, 0))
            # Starts counting beats from 'offset'.
            t = TempoClock(1, offset)
            self.assertTrue(math.isclose(t.beats, offset))
            # Counting beats as if it started 'offset' seconds ago from 0.
            t = TempoClock(1, 0, main.current_tt._seconds - offset)
            self.assertTrue(math.isclose(t.beats, offset))

        example.play()
        main.process()

    # TODO...


if __name__ == '__main__':
    unittest.main()
