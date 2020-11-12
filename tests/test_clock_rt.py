
import unittest
from threading import Thread, Barrier

import sc3
sc3.init('rt')

from sc3.base.main import main
from sc3.base.clock import TempoClock
from sc3.base.stream import routine


class ClockTestCase(unittest.TestCase):
    def test_logical_time_delta(self):
        barrier = Barrier(3, timeout=1)  # The test has to wait.
        tempo = 1000  # Float point resolution may affect tests if big.
        delta = 1

        @routine.run()
        def test():
            # Clock is created inside a main routine to avoid
            # timing offset relative to elapsed time updates.
            clock = TempoClock(tempo)

            @routine.run(clock)
            def r():
                nonlocal clock
                beats = clock.beats
                elapsed_delta = 0
                t1 = main.current_tt.seconds
                self.assertEqual(beats, elapsed_delta)
                yield delta

                beats = clock.beats
                elapsed_delta += delta
                t2 = main.current_tt.seconds
                self.assertEqual(beats, elapsed_delta)
                yield delta

                beats = clock.beats
                elapsed_delta += delta
                t3 = main.current_tt.seconds
                self.assertEqual(beats, elapsed_delta)
                self.assertEqual(t2 - t1, t3 - t2)

                # Clock threads can't be blocked.
                Thread(target=lambda: barrier.wait(), daemon=True).start()

            # Clock threads can't be blocked.
            Thread(target=lambda: barrier.wait(), daemon=True).start()

        barrier.wait()

    def test_initial_values(self):
        barrier = Barrier(2, timeout=1)  # The test has to wait.

        @routine.run()
        def example():
            offset = 5
            # Starts from zero by default.
            t = TempoClock(1)
            self.assertEqual(t.beats, 0)
            # Starts counting beats from 'offset'.
            t = TempoClock(1, offset)
            self.assertEqual(t.beats, offset)
            # Counting beats as if it started 'offset' seconds ago from 0.
            t = TempoClock(1, 0, main.current_tt.seconds - offset)
            self.assertEqual(t.beats, offset)
            Thread(target=lambda: barrier.wait(), daemon=True).start()

        barrier.wait()

    # TODO...


if __name__ == '__main__':
    unittest.main()
